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
import signal

import torch
import torch.nn as nn
import torch.nn.functional as F

# A100 TF32 optimization (INS-017 Vanguard, ~40% throughput boost on Ampere GPUs)
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
import webdataset as wds
from torch.utils.data import DataLoader

from omega_epiplexity_plus_core import OmegaMathematicalCompressor
from omega_webdataset_loader import create_dataloader, dynamic_processor, fast_npy_decoder

# Optional: Vertex AI HPO metric reporting
try:
    import hypertune
    _hpt = hypertune.HyperTune()
except ImportError:
    _hpt = None

# --- Spot VM preemption state (SIGTERM handler saves checkpoint) ---
_preemption_state = {
    "model": None, "optimizer": None, "scaler": None, "scheduler": None,
    "epoch": 0, "global_step": 0,
    "best_pf_ret": float("-inf"),        # Best val portfolio return (epoch-level)
    "best_batch_pf_ret": float("-inf"),   # Best train batch portfolio return (step-level)
    "ckpt_path": None,
}


def _sigterm_handler(signum, frame):
    """Handle SIGTERM from Spot VM preemption (30s grace period)."""
    logger = logging.getLogger(__name__)
    logger.warning("SIGTERM received — Spot VM preemption, saving emergency checkpoint")
    s = _preemption_state
    if s["model"] is not None and s["ckpt_path"] is not None:
        save_checkpoint(s["ckpt_path"], s["model"], s["optimizer"], s["scaler"],
                        s["epoch"], s["global_step"], {"emergency": True},
                        scheduler=s.get("scheduler"))
    if _hpt is not None:
        # Use best available portfolio return: val > batch > -999.0 (Vizier rejects inf)
        report_pf = s["best_pf_ret"]
        if report_pf == float("-inf"):
            report_pf = s.get("best_batch_pf_ret", float("-inf"))
        if report_pf == float("-inf"):
            report_pf = -999.0
        _hpt.report_hyperparameter_tuning_metric(
            hyperparameter_metric_tag="best_val_portfolio_return",
            metric_value=report_pf, global_step=s["global_step"])
    # C-047: Force FUSE flush before exit — prevent incomplete checkpoint on GCS
    os.sync()
    logger.warning(f"Emergency checkpoint saved (epoch={s['epoch']}, step={s['global_step']}, "
                   f"pf_ret={s['best_pf_ret']:.4f}, batch_pf_ret={s.get('best_batch_pf_ret', float('-inf')):.4f}). Exiting 143.")
    sys.exit(143)  # 128+SIGTERM(15) — signals abnormal termination for Spot VM restart


signal.signal(signal.SIGTERM, _sigterm_handler)


def compute_spear_loss(pred, target, z_core, lambda_s, epoch,
                       warmup_epochs=2, huber_delta=200.0, **kwargs):
    """Phase 11e: The Moment-Matched Spear (矩匹配建仓之矛)
    Wrapper that calls the new robust core loss logic from omega_epiplexity_plus_core
    and reconstructs pf_ret for monitoring.
    """
    from omega_epiplexity_plus_core import compute_spear_loss_moment_matched
    
    lambda_s_eff = lambda_s if epoch >= warmup_epochs else 0.0
    total, loss_err, s_t, pred_val = compute_spear_loss_moment_matched(
        raw_logits=pred, target=target, z_core=z_core,
        lambda_s=lambda_s_eff, huber_delta=huber_delta
    )

    eps = 1e-8
    # 4. Pointwise portfolio return proxy (监控指标，不参与梯度)
    #    Long-only 加权收益: clamp(pred,min=0) 归一化 → 加权 target
    with torch.no_grad():
        pred_pos = torch.clamp(pred_val, min=0.0)
        total_pos = pred_pos.sum()
        if total_pos > eps:
            weights = pred_pos / total_pos
            pf_ret = (weights * target.float().view(-1)).sum()
        else:
            pf_ret = torch.tensor(0.0, device=pred.device)

    return total, pf_ret, s_t


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

        # Vectorized masking (Gemini audit: Python for-loop is perf killer for small models)
        mask_lens = torch.randint(self.min_bars, self.max_bars + 1, (B,), device=x_2d.device)
        max_starts = T - mask_lens - self.keep_last
        valid = max_starts > 0

        starts = torch.zeros(B, device=x_2d.device, dtype=torch.long)
        if valid.any():
            starts[valid] = (torch.rand(valid.sum(), device=x_2d.device) * max_starts[valid].float()).long()

        idx = torch.arange(T, device=x_2d.device).unsqueeze(0).expand(B, T)
        in_mask = (idx >= starts.unsqueeze(1)) & (idx < (starts + mask_lens).unsqueeze(1)) & valid.unsqueeze(1)
        masked_x[in_mask.unsqueeze(-1).unsqueeze(-1).expand_as(masked_x)] = 0.0

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

        # Step 2: Build native manifold — Financial Relativity Transform
        # Architect directive: decompose LOB into 3 orthogonal physical representations
        # (1) Micro-structure: Bid/Ask → BP deviation from Mid-Price (preserves spread)
        # (2) Macro-trend: Close → cumulative log return from t=0 (preserves momentum)
        # (3) Volume: log1p (preserves power-law distribution)
        lob = x_2d[:, :, :, :5].float()  # fp32 for precision during division

        bid_p, bid_v, ask_p, ask_v, close_p = (
            lob[..., 0], lob[..., 1], lob[..., 2], lob[..., 3], lob[..., 4]
        )

        # (1) Micro: BP deviation from instantaneous Mid-Price
        mid_p = ((bid_p + ask_p) / 2.0).clamp(min=1e-6)
        lob[..., 0] = (bid_p - mid_p) / mid_p * 10000.0   # Bid spread ~[-10, -0.5] BP
        lob[..., 2] = (ask_p - mid_p) / mid_p * 10000.0   # Ask spread ~[+0.5, +10] BP

        # (2) Macro: cumulative log return from t=0 anchor (in %, 10% move → 10)
        anchor = close_p[:, 0:1, ...].clamp(min=1e-6)
        lob[..., 4] = torch.log(close_p.clamp(min=1e-6) / anchor) * 100.0

        # (3) Volume: log1p compression (power-law safe, range [0, 15])
        lob[..., 1] = torch.log1p(bid_v.clamp(min=0.0))
        lob[..., 3] = torch.log1p(ask_v.clamp(min=0.0))

        lob_features = lob.to(x_2d.dtype)  # back to model dtype (fp16 if AMP)

        # symlog for q_metaorder: handles negative values + sigma_d≈0 singularity
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
        .map(fast_npy_decoder, handler=wds.warn_and_continue)  # Gemini GCS audit
        .map(preprocess_fn, handler=wds.warn_and_continue)
        .batched(batch_size)
    )
    loader_kwargs = dict(batch_size=None, num_workers=num_workers, pin_memory=True)
    if num_workers > 0:
        loader_kwargs["prefetch_factor"] = 4
    return DataLoader(dataset, **loader_kwargs)


# ============================================================
# Checkpoint save/load (atomic write)
# ============================================================

def save_checkpoint(path, model, optimizer, scaler, epoch, global_step, metrics,
                    scheduler=None):
    import shutil
    # C-047: Write to local disk first, then copy to final path (GCS FUSE safe).
    # Risk: Spot SIGTERM during torch.save to /gcs/ FUSE → incomplete flush → corrupt checkpoint.
    # Fix: local staging guarantees atomic local write, then shutil.copy2 to FUSE is a single small I/O.
    local_staging = "/tmp/_omega_ckpt_staging.pt"
    torch.save({
        "epoch": epoch,
        "global_step": global_step,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scaler_state_dict": scaler.state_dict() if scaler is not None else {},
        "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else {},
        "metrics": metrics,
    }, local_staging)
    # Atomic copy: local → tmp on target → rename
    tmp_path = path + ".tmp"
    shutil.copy2(local_staging, tmp_path)
    os.replace(tmp_path, path)
    os.remove(local_staging)
    logger.info(f"Checkpoint saved: epoch={epoch}, step={global_step}")


def load_checkpoint(path, model, optimizer, scaler, device, scheduler=None):
    if not os.path.exists(path):
        return 0, 0, {}
    ckpt = torch.load(path, map_location=device, weights_only=False)
    try:
        model.load_state_dict(ckpt["model_state_dict"])
    except RuntimeError as e:
        # Architecture mismatch (e.g., different hidden_dim from prior HPO job)
        logger.warning(f"Checkpoint incompatible (different architecture), starting fresh: {e}")
        return 0, 0, {}
    optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    if scaler is not None and "scaler_state_dict" in ckpt:
        scaler.load_state_dict(ckpt["scaler_state_dict"])
    if scheduler is not None and "scheduler_state_dict" in ckpt and ckpt["scheduler_state_dict"]:
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
    logger.info(f"Resumed from checkpoint: epoch={ckpt['epoch']}, step={ckpt['global_step']}")
    return ckpt["epoch"], ckpt["global_step"], ckpt.get("metrics", {})


# ============================================================
# Training loop (one epoch)
# ============================================================

def train_one_epoch(model, loader, optimizer, scaler, lambda_s,
                    grad_clip, device, epoch, steps_per_epoch, global_step,
                    use_amp, warmup_epochs=2, overfit_batch=None, scheduler=None,
                    start_step=0, ckpt_path=None, ckpt_every=0,
                    temperature=0.1, huber_delta=200.0):
    model.train()
    running = {"total": 0.0, "pf_ret": 0.0, "s_t": 0.0, "count": 0}
    loader_iter = iter(loader) if overfit_batch is None else None
    skipped = 0

    if start_step > 0:
        logger.info(f"Epoch {epoch}: resuming from step {start_step}/{steps_per_epoch}")

    for step_i in range(start_step, steps_per_epoch):
        if overfit_batch is not None:
            batch = overfit_batch  # Same batch every step (overfit test)
        else:
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

        try:
            if use_amp:
                with torch.autocast(device_type="cuda", dtype=torch.float16):
                    prediction, z_core = model(manifold, c_friction)
                    total_loss, pf_ret, s_t = compute_spear_loss(
                        prediction, target, z_core, lambda_s, epoch, warmup_epochs,
                        huber_delta=huber_delta, temperature=temperature
                    )
                scaler.scale(total_loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                prediction, z_core = model(manifold, c_friction)
                total_loss, pf_ret, s_t = compute_spear_loss(
                    prediction, target, z_core, lambda_s, epoch, warmup_epochs,
                    huber_delta=huber_delta, temperature=temperature
                )
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            logger.error("CUDA OOM — parameter space INFEASIBLE for this trial")
            if _hpt is not None:
                _hpt.report_hyperparameter_tuning_metric(
                    hyperparameter_metric_tag="best_val_portfolio_return",
                    metric_value=-999.0, global_step=0)
            sys.exit(0)  # Clean exit — prevents infinite restart on Spot VM

        if scheduler is not None:
            scheduler.step()

        running["total"] += total_loss.item()
        running["pf_ret"] += pf_ret.item()
        running["s_t"] += s_t.item()
        running["count"] += 1
        # Track prediction std (cross-sectional variance monitoring, INS-017)
        with torch.no_grad():
            pred_std = prediction.view(-1).std().item()
            running["pred_std"] = running.get("pred_std", 0.0) + pred_std
        global_step += 1

        # Update preemption state with batch-level portfolio return (for SIGTERM reporting)
        pf_ret_val = pf_ret.item()
        _preemption_state["global_step"] = global_step
        if pf_ret_val > _preemption_state.get("best_batch_pf_ret", float("-inf")):
            _preemption_state["best_batch_pf_ret"] = pf_ret_val

        # Step-level checkpoint for Spot VM resilience (~every 3 min)
        if ckpt_path and ckpt_every > 0 and global_step % ckpt_every == 0:
            save_checkpoint(ckpt_path, model, optimizer, scaler,
                            epoch, global_step,
                            {"step_ckpt": True, "best_pf_ret": _preemption_state.get("best_pf_ret", float("-inf"))},
                            scheduler=scheduler)

        if step_i % max(1, steps_per_epoch // 10) == 0:
            n = max(running["count"], 1)
            logger.info(
                f"Epoch {epoch} Step {step_i}/{steps_per_epoch} | "
                f"Loss={running['total']/n:.6f} "
                f"PfRet={running['pf_ret']/n:.6f} "
                f"S_T={running['s_t']/n:.4f} "
                f"Std_yhat={running.get('pred_std',0)/n:.6f}"
            )

    n = max(running["count"], 1)
    avg_metrics = {
        "total": running["total"] / n,
        "pf_ret": running["pf_ret"] / n,
        "s_t": running["s_t"] / n,
        "steps": running["count"],
    }
    return avg_metrics, global_step


# ============================================================
# Validation
# ============================================================

def validate(model, val_loader, lambda_s, device, max_steps=0, epoch=0,
             warmup_epochs=2, temperature=0.1, huber_delta=200.0,
             sentinel_error=10.0, sentinel_warn=30.0):
    model.eval()
    all_preds, all_targets = [], []
    running = {"total": 0.0, "pf_ret": 0.0, "s_t": 0.0, "count": 0}

    with torch.no_grad():
        for step_i, batch in enumerate(val_loader):
            if max_steps > 0 and step_i >= max_steps:
                break
            manifold = batch["manifold_2d"].to(device)
            c_friction = batch["c_friction"].to(device).unsqueeze(-1)
            target = batch["target"].to(device)

            prediction, z_core = model(manifold, c_friction)
            total_loss, pf_ret, s_t = compute_spear_loss(
                prediction, target, z_core, lambda_s, epoch, warmup_epochs,
                huber_delta=huber_delta, temperature=temperature
            )
            bs = target.size(0)
            running["total"] += total_loss.item() * bs
            running["pf_ret"] += pf_ret.item() * bs
            running["s_t"] += s_t.item() * bs
            running["count"] += bs
            all_preds.append(prediction.view(-1))
            all_targets.append(target)

    n = max(running["count"], 1)
    preds = torch.cat(all_preds)

    # Cross-sectional prediction std (INS-017: Std Expansion monitoring)
    pred_std_bp = preds.std().item()

    # Variance Collapse Sentinel (INS-054, C-055: thresholds must be empirically calibrated)
    if pred_std_bp < sentinel_error and preds.numel() > 10:
        logger.error(f"VARIANCE COLLAPSE: pred_std={pred_std_bp:.2f} BP < {sentinel_error}. Brain death detected.")
    elif pred_std_bp < sentinel_warn:
        logger.warning(f"LOW VARIANCE: pred_std={pred_std_bp:.2f} BP < {sentinel_warn}. Nearing collapse.")

    return {
        "total": running["total"] / n,
        "pf_ret": running["pf_ret"] / n,
        "s_t": running["s_t"] / n,
        "pred_std_bp": pred_std_bp,
        "portfolio_return": running["pf_ret"] / n,
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
    parser.add_argument("--lambda_s", type=float, default=1e-4)
    parser.add_argument("--huber_delta", type=float, default=200.0,
                        help="Huber loss delta (BP). Phase 11c=50, Phase 11d=200 (INS-055)")
    parser.add_argument("--grad_clip", type=float, default=1.0)
    parser.add_argument("--val_split", type=float, default=0.2)
    # HPO-searchable (lambda x: int(float(x)) handles Vertex AI "128.0" format)
    _int = lambda x: int(float(x))
    parser.add_argument("--macro_window", type=_int, default=160)
    parser.add_argument("--coarse_graining_factor", type=_int, default=1)
    parser.add_argument("--window_size_t", type=_int, default=4)
    parser.add_argument("--window_size_s", type=_int, default=4)
    parser.add_argument("--hidden_dim", type=_int, default=64)
    # Infra
    parser.add_argument("--num_workers", type=int, default=6,
                        help="DataLoader workers (Gemini: 6 for 8-vCPU, reserve 2 for main+GPU)")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max_val_steps", type=int, default=0,
                        help="Max validation steps (0=all, useful for CPU smoke tests)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sentinel_error", type=float, default=10.0,
                        help="Variance collapse ERROR threshold (BP). C-055: calibrate with data")
    parser.add_argument("--sentinel_warn", type=float, default=30.0,
                        help="Low variance WARNING threshold (BP). C-055: calibrate with data")
    parser.add_argument("--mask_prob", type=float, default=0.5,
                        help="Block masking probability (0.0 to disable)")
    parser.add_argument("--overfit", action="store_true",
                        help="Overfit test: repeat first batch for all steps")
    parser.add_argument("--warmup_epochs", type=_int, default=2,
                        help="MDL lambda_s warmup: 0 for first N epochs")
    # Phase 4 HPO: early stopping
    parser.add_argument("--early_stop_fvu", type=float, default=0.0,
                        help="Early stop if best FVU > threshold after patience epochs (0=disabled)")
    parser.add_argument("--early_stop_patience", type=int, default=3,
                        help="Epochs to wait before checking early stop condition")
    # Spot VM resilience
    parser.add_argument("--ckpt_every_n_steps", type=int, default=0,
                        help="Save checkpoint every N steps (0=epoch-only, 500 recommended for Spot)")
    # Phase 11c: temperature kept for YAML backward-compat but no longer used (Pointwise Spear)
    parser.add_argument("--temperature", type=float, default=0.5,
                        help="DEPRECATED: Phase 11c Pointwise Spear removed Softmax. Kept for YAML compat.")
    parser.add_argument("--l2_weight", type=float, default=0.0,
                        help="DEPRECATED: replaced by Variance Straitjacket (INS-040). Kept for YAML compat.")
    parser.add_argument("--no_amp", action="store_true", default=False,
                        help="Disable AMP, use pure FP32/TF32 (Gemini: AMP negative-optimizes tiny models)")
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
    use_amp = device.type == "cuda" and not args.no_amp
    logger.info(f"Device: {device}, AMP: {use_amp}, TF32: {torch.backends.cuda.matmul.allow_tf32}")

    # Add file handler
    fh = logging.FileHandler(os.path.join(args.output_dir, "train.log"))
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

    # --- Temporal validation split ---
    if args.shard_dir.startswith("gs://"):
        # GCS pipe mode: generate pipe:gcloud storage cat URLs (no FUSE, no staging)
        # Gemini audit: glob on GCS FUSE triggers 1992 API calls; pipe avoids this entirely
        import subprocess
        ls_result = subprocess.run(
            ["gcloud", "storage", "ls", os.path.join(args.shard_dir, "omega_shard_*.tar")],
            capture_output=True, text=True, timeout=60
        )
        gcs_urls = sorted([u.strip() for u in ls_result.stdout.strip().split("\n") if u.strip()])
        if not gcs_urls:
            logger.error(f"No shards found in {args.shard_dir}")
            sys.exit(1)
        all_shards = [f"pipe:gcloud storage cat {url}" for url in gcs_urls]
        logger.info(f"GCS pipe mode: {len(all_shards)} shards via streaming")
    else:
        all_shards = sorted(glob.glob(os.path.join(args.shard_dir, "omega_shard_*.tar")))
        if not all_shards:
            logger.error(f"No shards found in {args.shard_dir}")
            sys.exit(1)

    valid_shards = all_shards
    logger.info(f"Using {len(valid_shards)} shards (corrupt shards bypassed by handler)")
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
        .map(fast_npy_decoder, handler=wds.warn_and_continue)  # Gemini GCS audit: -15% CPU
        .map(_train_preprocess, handler=wds.warn_and_continue)
        .batched(args.batch_size)
    )
    _train_kw = dict(batch_size=None, num_workers=args.num_workers, pin_memory=True)
    if args.num_workers > 0:
        _train_kw["prefetch_factor"] = 4  # Gemini: 4 > 2 for NVMe throughput
    train_loader = DataLoader(_train_ds, **_train_kw)
    val_loader = create_val_dataloader(
        val_shards, args.batch_size, args.macro_window,
        args.coarse_graining_factor, args.num_workers
    )

    # --- Model ---
    model = OmegaTIBWithMasking(
        hidden_dim=args.hidden_dim,
        window_size=(args.window_size_t, args.window_size_s),
        mask_prob=args.mask_prob,
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Model: OmegaTIBWithMasking, {n_params:,} parameters")
    logger.info(f"Config: hidden_dim={args.hidden_dim}, "
                f"window=({args.window_size_t},{args.window_size_s}), "
                f"macro_window={args.macro_window}, "
                f"coarse_graining={args.coarse_graining_factor}")

    # --- Optimizer + Scaler + LR Scheduler ---
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scaler = torch.cuda.amp.GradScaler() if use_amp else None
    total_steps = args.epochs * args.steps_per_epoch
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=args.lr, total_steps=total_steps,
        pct_start=0.05, anneal_strategy='cos', div_factor=100,  # start lr/100, warmup 5%
    ) if not args.overfit else None

    # --- Resume (auto-resume for Spot VM preemption recovery) ---
    ckpt_path = os.path.join(args.output_dir, "latest.pt")
    start_epoch, global_step = 0, 0
    _resumed_metrics = {}
    if os.path.exists(ckpt_path):
        start_epoch, global_step, _resumed_metrics = load_checkpoint(
            ckpt_path, model, optimizer, scaler, device, scheduler
        )
        # Compute mid-epoch resume position from global_step
        if global_step > 0 and global_step % args.steps_per_epoch != 0:
            start_epoch = global_step // args.steps_per_epoch
            logger.info(f"Mid-epoch resume: epoch={start_epoch}, "
                        f"step={global_step % args.steps_per_epoch}/{args.steps_per_epoch}")
    elif args.resume:
        logger.warning(f"Resume requested but no checkpoint at {ckpt_path}")

    # Register state for SIGTERM preemption handler
    _preemption_state.update({
        "model": model, "optimizer": optimizer, "scaler": scaler,
        "scheduler": scheduler, "epoch": start_epoch, "global_step": global_step,
        "ckpt_path": ckpt_path,
    })

    # --- Overfit mode: capture first batch ---
    overfit_batch = None
    if args.overfit:
        loader_iter = iter(train_loader)
        overfit_batch = next(loader_iter)
        logger.info(f"OVERFIT MODE: repeating single batch of {overfit_batch['target'].shape[0]} samples")

    # --- Training ---
    logger.info(f"Starting training [Phase 11c Pointwise Spear]: epochs={args.epochs}, "
                f"steps/epoch={args.steps_per_epoch}, batch={args.batch_size}, "
                f"lr={args.lr}, lambda_s={args.lambda_s}, "
                f"warmup={args.warmup_epochs}, mask_prob={args.mask_prob}")

    best_pf_ret = _resumed_metrics.get("best_pf_ret", float("-inf"))

    for epoch in range(start_epoch, args.epochs):
        t0 = time.time()

        # Compute start_step for mid-epoch resume (0 if starting fresh)
        start_step = global_step - (epoch * args.steps_per_epoch) if global_step > epoch * args.steps_per_epoch else 0

        train_metrics, global_step = train_one_epoch(
            model, train_loader, optimizer, scaler, args.lambda_s,
            args.grad_clip, device, epoch, args.steps_per_epoch, global_step,
            use_amp, warmup_epochs=args.warmup_epochs,
            overfit_batch=overfit_batch, scheduler=scheduler,
            start_step=start_step, ckpt_path=ckpt_path,
            ckpt_every=args.ckpt_every_n_steps,
            temperature=args.temperature,
            huber_delta=args.huber_delta,
        )

        val_metrics = validate(model, val_loader, args.lambda_s, device,
                               max_steps=args.max_val_steps, epoch=epoch,
                               warmup_epochs=args.warmup_epochs,
                               temperature=args.temperature,
                               huber_delta=args.huber_delta,
                               sentinel_error=args.sentinel_error,
                               sentinel_warn=args.sentinel_warn)
        elapsed = time.time() - t0

        logger.info(
            f"Epoch {epoch} DONE ({elapsed:.0f}s) | "
            f"Train: loss={train_metrics['total']:.6f} "
            f"PfRet={train_metrics['pf_ret']:.6f} S_T={train_metrics['s_t']:.4f} | "
            f"Val: loss={val_metrics['total']:.6f} "
            f"PfRet={val_metrics.get('portfolio_return',0):.6f} "
            f"Std_yhat={val_metrics.get('pred_std_bp',0):.2f}BP "
            f"({val_metrics['n_samples']} samples)"
        )

        # Save checkpoint every epoch (including scheduler for Spot VM resume)
        save_checkpoint(ckpt_path, model, optimizer, scaler, epoch + 1,
                        global_step, {"train": train_metrics, "val": val_metrics,
                                      "best_pf_ret": best_pf_ret},
                        scheduler=scheduler)

        # Save best model by portfolio return (higher = better)
        val_pf_ret = val_metrics["portfolio_return"]
        if val_pf_ret > best_pf_ret:
            best_pf_ret = val_pf_ret
            best_path = os.path.join(args.output_dir, "best.pt")
            save_checkpoint(best_path, model, optimizer, scaler, epoch + 1,
                            global_step, {"train": train_metrics, "val": val_metrics,
                                          "best_pf_ret": best_pf_ret},
                            scheduler=scheduler)
            logger.info(f"New best Portfolio Return: {best_pf_ret:.6f}")

        # Report metric for Vertex AI HPO (Vizier) — MAXIMIZE portfolio return
        if _hpt is not None:
            _hpt.report_hyperparameter_tuning_metric(
                hyperparameter_metric_tag="best_val_portfolio_return",
                metric_value=best_pf_ret,
                global_step=epoch,
            )

        # Update preemption state (for SIGTERM handler on Spot VMs)
        _preemption_state.update({
            "epoch": epoch + 1, "global_step": global_step,
            "best_pf_ret": best_pf_ret,
        })

        # Early stopping (MDL-shock aware: wait for warmup + 1 absorption epoch)
        # Direction reversed: portfolio return should increase, stop if below threshold
        safe_epoch = max(args.early_stop_patience, args.warmup_epochs + 1)
        if args.early_stop_fvu > 0 and epoch >= safe_epoch:
            if best_pf_ret < args.early_stop_fvu:
                logger.info(
                    f"Early stopping: best PfRet {best_pf_ret:.6f} < "
                    f"{args.early_stop_fvu} after {epoch + 1} epochs "
                    f"(safe_epoch={safe_epoch})"
                )
                break

    logger.info(f"Training complete. Best Portfolio Return: {best_pf_ret:.6f}")


if __name__ == "__main__":
    main()
