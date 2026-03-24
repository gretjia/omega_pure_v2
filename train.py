"""
Omega-TIB Phase 3: Training Script
-----------------------------------
Single-file training loop for the Topological Information Bottleneck model.

Forward → MDL Loss → Backward → Step
Block-wise Input Masking (on-the-fly, train only)
Temporal validation split (last 20% shards, no look-ahead bias)
Mixed precision (fp16) + gradient clipping
Checkpoint save/load with resume

Usage:
  python3 train.py --shard_dir /omega_pool/wds_shards_v3_full --epochs 10
  python3 train.py --shard_dir /path/to/shards --resume --batch_size 128

Must run via: systemd-run --slice=heavy-workload.slice
"""

import os
import sys
import glob
import time
import random
import argparse
import logging
import fcntl

import torch
import torch.nn as nn
import torch.nn.functional as F
import webdataset as wds
from torch.utils.data import DataLoader

from omega_epiplexity_plus_core import (
    OmegaMathematicalCompressor,
    compute_epiplexity_mdl_loss,
    compute_fvu,
)
from omega_webdataset_loader import create_dataloader, dynamic_processor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============================================================
# VolumeBlockInputMasking (from architect/gdocs/id5)
# ============================================================

class VolumeBlockInputMasking(nn.Module):
    """
    Block-wise input masking: randomly zero out contiguous volume bars.
    Forces cross-temporal causal reasoning, prevents local interpolation.
    Applied after input_proj, before tda_layer. Train-only.
    """
    def __init__(self, min_mask_bars=10, max_mask_bars=30, mask_prob=0.5, keep_last=5):
        super().__init__()
        self.min_bars = min_mask_bars
        self.max_bars = max_mask_bars
        self.mask_prob = mask_prob
        self.keep_last = keep_last

    def forward(self, x_2d: torch.Tensor) -> torch.Tensor:
        if not self.training or random.random() > self.mask_prob:
            return x_2d

        B, T, S, F = x_2d.shape
        masked_x = x_2d.clone()

        for i in range(B):
            mask_len = random.randint(self.min_bars, self.max_bars)
            max_start = T - mask_len - self.keep_last
            if max_start > 0:
                start_idx = random.randint(0, max_start)
                masked_x[i, start_idx:start_idx + mask_len, :, :] = 0.0

        return masked_x


# ============================================================
# OmegaTIBWithMasking (wrapper — inserts masking between
# input_proj and tda_layer without modifying core file)
# ============================================================

class OmegaTIBWithMasking(nn.Module):
    """
    Wraps OmegaMathematicalCompressor to inject VolumeBlockInputMasking
    at the spec-mandated insertion point: after input_proj, before tda_layer.
    """
    def __init__(self, hidden_dim=64, window_size=(4, 4),
                 min_mask_bars=10, max_mask_bars=30, mask_prob=0.5, keep_last=5):
        super().__init__()
        self.model = OmegaMathematicalCompressor(hidden_dim, window_size)
        self.masking = VolumeBlockInputMasking(min_mask_bars, max_mask_bars,
                                               mask_prob, keep_last)
        # LayerNorm after input_proj to stabilize training with unnormalized raw features
        self.post_proj_norm = nn.LayerNorm(hidden_dim)

    def forward(self, x_2d: torch.Tensor, c_friction: torch.Tensor):
        B, T, S, C = x_2d.shape

        # Step 1: Physics layer (SRL inversion)
        delta_p = x_2d[:, :, 0, 7]
        v_d_macro = x_2d[:, :, 0, 8]
        sigma_d_macro = x_2d[:, :, 0, 9]

        with torch.no_grad(), torch.autocast(device_type="cuda", enabled=False):
            q_metaorder = self.model.srl_inverter(
                delta_p.float(), sigma_d_macro.float(),
                v_d_macro.float(), c_friction.float()
            )
        q_metaorder = q_metaorder.unsqueeze(-1).unsqueeze(-1).expand(B, T, S, 1)

        # Step 2: Build native manifold + project
        lob_features = x_2d[:, :, :, :5]
        # [Gemini Fix 2] log1p compression: 5M → ~15, safe for fp16 and gradient stability
        lob_features = torch.log1p(torch.clamp(lob_features, min=0))
        # [Gemini Fix 2] symlog for q_metaorder: handles negative values + sigma_d≈0 singularity
        q_metaorder = torch.sign(q_metaorder) * torch.log1p(torch.abs(q_metaorder))

        native_manifold = torch.cat([lob_features, q_metaorder], dim=-1)
        x = self.model.input_proj(native_manifold)
        x = self.post_proj_norm(x)

        # === MASKING INSERTION POINT (spec: after input_proj, before tda) ===
        x = self.masking(x)

        # Step 3-5: Topology → Bottleneck → Prediction
        structured_features = self.model.tda_layer(x)
        z_core = self.model.epiplexity_bottleneck(structured_features)
        pooled_z = torch.mean(z_core, dim=[1, 2])
        prediction = self.model.intent_decoder(pooled_z)

        return prediction, z_core


# ============================================================
# Validation DataLoader (finite, single-pass, no shuffle)
# ============================================================

def create_val_dataloader(wds_url, batch_size, macro_window,
                          coarse_graining_factor, num_workers):
    preprocess_fn = dynamic_processor(macro_window, coarse_graining_factor)
    dataset = (
        wds.WebDataset(wds_url, resampled=False, handler=wds.warn_and_continue)
        .decode(handler=wds.warn_and_continue)
        .map(preprocess_fn, handler=wds.warn_and_continue)
        .batched(batch_size)
    )
    loader_kwargs = dict(batch_size=None, num_workers=num_workers)
    if num_workers > 0:
        loader_kwargs["prefetch_factor"] = 2
    return DataLoader(dataset, **loader_kwargs)


# ============================================================
# Checkpoint save/load (atomic write)
# ============================================================

def save_checkpoint(path, model, optimizer, scaler, epoch, global_step, metrics):
    tmp_path = path + ".tmp"
    torch.save({
        "epoch": epoch,
        "global_step": global_step,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scaler_state_dict": scaler.state_dict() if scaler is not None else {},
        "metrics": metrics,
    }, tmp_path)
    os.replace(tmp_path, path)
    logger.info(f"Checkpoint saved: epoch={epoch}, step={global_step}")


def load_checkpoint(path, model, optimizer, scaler, device):
    if not os.path.exists(path):
        return 0, 0, {}
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    if scaler is not None and "scaler_state_dict" in ckpt:
        scaler.load_state_dict(ckpt["scaler_state_dict"])
    logger.info(f"Resumed from checkpoint: epoch={ckpt['epoch']}, step={ckpt['global_step']}")
    return ckpt["epoch"], ckpt["global_step"], ckpt.get("metrics", {})


# ============================================================
# Training loop (one epoch)
# ============================================================

def train_one_epoch(model, loader, optimizer, scaler, lambda_s,
                    grad_clip, device, epoch, steps_per_epoch, global_step,
                    use_amp):
    model.train()
    running = {"total": 0.0, "h_t": 0.0, "s_t": 0.0, "count": 0}
    loader_iter = iter(loader)
    skipped = 0

    for step_i in range(steps_per_epoch):
        try:
            batch = next(loader_iter)
        except StopIteration:
            loader_iter = iter(loader)
            batch = next(loader_iter)
        except Exception as e:
            skipped += 1
            if skipped % 10 == 1:
                logger.warning(f"Skipping corrupt batch (total skipped: {skipped}): {e}")
            loader_iter = iter(loader)
            continue

        manifold = batch["manifold_2d"].to(device)
        c_friction = batch["c_friction"].to(device).unsqueeze(-1)
        target = batch["target"].to(device)

        optimizer.zero_grad(set_to_none=True)

        if use_amp:
            with torch.autocast(device_type="cuda", dtype=torch.float16):
                prediction, z_core = model(manifold, c_friction)
                total_loss, h_t, s_t = compute_epiplexity_mdl_loss(
                    prediction, target, z_core, lambda_s
                )
            scaler.scale(total_loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            scaler.step(optimizer)
            scaler.update()
        else:
            prediction, z_core = model(manifold, c_friction)
            total_loss, h_t, s_t = compute_epiplexity_mdl_loss(
                prediction, target, z_core, lambda_s
            )
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            optimizer.step()

        running["total"] += total_loss.item()
        running["h_t"] += h_t.item()
        running["s_t"] += s_t.item()
        running["count"] += 1
        global_step += 1

        if step_i % max(1, steps_per_epoch // 10) == 0:
            n = max(running["count"], 1)
            logger.info(
                f"Epoch {epoch} Step {step_i}/{steps_per_epoch} | "
                f"Loss={running['total']/n:.6f} "
                f"H_T={running['h_t']/n:.6f} "
                f"S_T={running['s_t']/n:.4f}"
            )

    n = max(running["count"], 1)
    avg_metrics = {
        "total": running["total"] / n,
        "h_t": running["h_t"] / n,
        "s_t": running["s_t"] / n,
        "steps": running["count"],
    }
    return avg_metrics, global_step


# ============================================================
# Validation
# ============================================================

def validate(model, val_loader, lambda_s, device, max_steps=0):
    model.eval()
    all_preds, all_targets = [], []
    running = {"total": 0.0, "h_t": 0.0, "s_t": 0.0, "count": 0}

    with torch.no_grad():
        for step_i, batch in enumerate(val_loader):
            if max_steps > 0 and step_i >= max_steps:
                break
            manifold = batch["manifold_2d"].to(device)
            c_friction = batch["c_friction"].to(device).unsqueeze(-1)
            target = batch["target"].to(device)

            prediction, z_core = model(manifold, c_friction)
            total_loss, h_t, s_t = compute_epiplexity_mdl_loss(
                prediction, target, z_core, lambda_s
            )
            bs = target.size(0)
            running["total"] += total_loss.item() * bs
            running["h_t"] += h_t.item() * bs
            running["s_t"] += s_t.item() * bs
            running["count"] += bs
            all_preds.append(prediction.squeeze())
            all_targets.append(target)

    n = max(running["count"], 1)
    preds = torch.cat(all_preds)
    targets = torch.cat(all_targets)
    fvu = compute_fvu(preds, targets)

    return {
        "total": running["total"] / n,
        "h_t": running["h_t"] / n,
        "s_t": running["s_t"] / n,
        "fvu": fvu,
        "n_samples": running["count"],
    }


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Omega-TIB Phase 3 Training")
    # Data
    parser.add_argument("--shard_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="./checkpoints")
    # Training
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--steps_per_epoch", type=int, default=10000)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--lambda_s", type=float, default=0.001)
    parser.add_argument("--grad_clip", type=float, default=1.0)
    parser.add_argument("--val_split", type=float, default=0.2)
    # HPO-searchable
    parser.add_argument("--macro_window", type=int, default=160)
    parser.add_argument("--coarse_graining_factor", type=int, default=1)
    parser.add_argument("--window_size_t", type=int, default=4)
    parser.add_argument("--window_size_s", type=int, default=4)
    parser.add_argument("--hidden_dim", type=int, default=64)
    # Infra
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max_val_steps", type=int, default=0,
                        help="Max validation steps (0=all, useful for CPU smoke tests)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # --- Single instance lock (CLAUDE.md rule #25) ---
    lock_fd = os.open("/tmp/omega_train.lock", os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logger.error("Another train.py instance is running. Exiting.")
        sys.exit(1)

    # --- Setup ---
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda"  # Safe: log1p compresses features to [-30,30], within fp16 range
    logger.info(f"Device: {device}, AMP: {use_amp}")

    # Add file handler
    fh = logging.FileHandler(os.path.join(args.output_dir, "train.log"))
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

    # --- Temporal validation split ---
    all_shards = sorted(glob.glob(os.path.join(args.shard_dir, "omega_shard_*.tar")))
    if not all_shards:
        logger.error(f"No shards found in {args.shard_dir}")
        sys.exit(1)

    # [Gemini Fix 4] Skip slow gcsfuse getsize; handler auto-skips corrupt shards at read time
    valid_shards = all_shards
    logger.info(f"Using all {len(valid_shards)} shards (corrupt shards bypassed by handler)")
    n_train = int(len(valid_shards) * (1 - args.val_split))
    train_shards = valid_shards[:n_train]
    val_shards = valid_shards[n_train:]
    logger.info(f"Shards: {len(valid_shards)} valid, {len(train_shards)} train, "
                f"{len(val_shards)} val (temporal split, no look-ahead)")

    # --- DataLoaders (with error handler for corrupt shards) ---
    _train_preprocess = dynamic_processor(args.macro_window, args.coarse_graining_factor)
    _train_ds = (
        wds.WebDataset(train_shards, resampled=True, handler=wds.warn_and_continue)
        .shuffle(1000)
        .decode(handler=wds.warn_and_continue)
        .map(_train_preprocess, handler=wds.warn_and_continue)
        .batched(args.batch_size)
    )
    _train_kw = dict(batch_size=None, num_workers=args.num_workers)
    if args.num_workers > 0:
        _train_kw["prefetch_factor"] = 2
    train_loader = DataLoader(_train_ds, **_train_kw)
    val_loader = create_val_dataloader(
        val_shards, args.batch_size, args.macro_window,
        args.coarse_graining_factor, args.num_workers
    )

    # --- Model ---
    model = OmegaTIBWithMasking(
        hidden_dim=args.hidden_dim,
        window_size=(args.window_size_t, args.window_size_s),
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Model: OmegaTIBWithMasking, {n_params:,} parameters")
    logger.info(f"Config: hidden_dim={args.hidden_dim}, "
                f"window=({args.window_size_t},{args.window_size_s}), "
                f"macro_window={args.macro_window}, "
                f"coarse_graining={args.coarse_graining_factor}")

    # --- Optimizer + Scaler ---
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scaler = torch.cuda.amp.GradScaler() if use_amp else None

    # --- Resume ---
    ckpt_path = os.path.join(args.output_dir, "latest.pt")
    start_epoch, global_step = 0, 0
    if args.resume:
        start_epoch, global_step, _ = load_checkpoint(
            ckpt_path, model, optimizer, scaler, device
        )

    # --- Training ---
    logger.info(f"Starting training: epochs={args.epochs}, "
                f"steps/epoch={args.steps_per_epoch}, batch={args.batch_size}, "
                f"lr={args.lr}, lambda_s={args.lambda_s}")

    best_fvu = float("inf")

    for epoch in range(start_epoch, args.epochs):
        t0 = time.time()

        train_metrics, global_step = train_one_epoch(
            model, train_loader, optimizer, scaler, args.lambda_s,
            args.grad_clip, device, epoch, args.steps_per_epoch, global_step,
            use_amp
        )

        val_metrics = validate(model, val_loader, args.lambda_s, device,
                               max_steps=args.max_val_steps)
        elapsed = time.time() - t0

        logger.info(
            f"Epoch {epoch} DONE ({elapsed:.0f}s) | "
            f"Train: loss={train_metrics['total']:.6f} "
            f"H_T={train_metrics['h_t']:.6f} S_T={train_metrics['s_t']:.4f} | "
            f"Val: loss={val_metrics['total']:.6f} "
            f"FVU={val_metrics['fvu']:.4f} ({val_metrics['n_samples']} samples)"
        )

        # Save checkpoint every epoch
        save_checkpoint(ckpt_path, model, optimizer, scaler, epoch + 1,
                        global_step, {"train": train_metrics, "val": val_metrics})

        # Save best model by FVU
        if val_metrics["fvu"] < best_fvu:
            best_fvu = val_metrics["fvu"]
            best_path = os.path.join(args.output_dir, "best.pt")
            save_checkpoint(best_path, model, optimizer, scaler, epoch + 1,
                            global_step, {"train": train_metrics, "val": val_metrics})
            logger.info(f"New best FVU: {best_fvu:.4f}")

    logger.info(f"Training complete. Best FVU: {best_fvu:.4f}")


if __name__ == "__main__":
    main()
