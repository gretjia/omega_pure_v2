"""
Phase 14 Step 0 + Step 1: Data Baseline + Phase 6 Oracle Test
==============================================================
Step 0: Compute target distribution statistics (model-independent)
Step 1: Load Phase 6 checkpoint, run inference with Phase 6-era forward logic

Phase 6 architecture differences from Phase 13+:
  - window_size=(4,4) not (32,10) — RPB table shape [49,4] vs [1197,4]
  - tda_layer(x) directly, NO residual, NO Pre-LN
  - torch.mean(z_core, dim=[1,2]) global pooling, NO AttentionPooling
  - No overflow clamp before symlog
  - HAS FRT and post_proj_norm (same as current)
"""

import os
import sys
import json
import logging
import argparse
import glob
import subprocess

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from omega_epiplexity_plus_core import OmegaMathematicalCompressor
from omega_webdataset_loader import fast_npy_decoder, dynamic_processor

try:
    import webdataset as wds
    from torch.utils.data import DataLoader
    from scipy.stats import spearmanr, skew, kurtosis
except ImportError as e:
    print(f"Missing dependency: {e}. Install: pip install webdataset scipy")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


# ============================================================
# Phase 6-compatible inference wrapper
# ============================================================

class Phase6Inference(nn.Module):
    """Phase 6-era forward path (commit ca769ec).

    Key differences from Phase 13+ (backtest_5a.py):
      - tda_layer(x) directly (no residual, no Pre-LN)
      - torch.mean(z_core, dim=[1,2]) (no AttentionPooling)
      - No overflow clamp before symlog
    """

    def __init__(self, hidden_dim=64, window_size=(4, 4)):
        super().__init__()
        # OmegaMathematicalCompressor creates tda_pre_ln and attention_pool
        # even though Phase 6 doesn't use them. strict=False loading is safe.
        self.model = OmegaMathematicalCompressor(hidden_dim, window_size)
        self.post_proj_norm = nn.LayerNorm(hidden_dim)

    def forward(self, x_2d: torch.Tensor, c_friction: torch.Tensor):
        B, T, S, C = x_2d.shape

        # Physics layer (identical across all phases)
        delta_p = x_2d[:, :, 0, 7]
        v_d_macro = x_2d[:, :, 0, 8]
        sigma_d_macro = x_2d[:, :, 0, 9]

        device_type = x_2d.device.type
        with torch.no_grad(), torch.autocast(device_type=device_type, enabled=False):
            q_metaorder = self.model.srl_inverter(
                delta_p.float(), sigma_d_macro.float(),
                v_d_macro.float(), c_friction.float()
            )
        q_metaorder = q_metaorder.unsqueeze(-1).unsqueeze(-1).expand(B, T, S, 1)

        # Financial Relativity Transform (from ca769ec:train.py L:213-233)
        lob = x_2d[:, :, :, :5].float()
        bid_p, bid_v, ask_p, ask_v, close_p = (
            lob[..., 0], lob[..., 1], lob[..., 2], lob[..., 3], lob[..., 4]
        )
        mid_p = ((bid_p + ask_p) / 2.0).clamp(min=1e-6)
        lob[..., 0] = (bid_p - mid_p) / mid_p * 10000.0
        lob[..., 2] = (ask_p - mid_p) / mid_p * 10000.0
        anchor = close_p[:, 0:1, ...].clamp(min=1e-6)
        lob[..., 4] = torch.log(close_p.clamp(min=1e-6) / anchor) * 100.0
        lob[..., 1] = torch.log1p(bid_v.clamp(min=0.0))
        lob[..., 3] = torch.log1p(ask_v.clamp(min=0.0))
        lob_features = lob.to(x_2d.dtype)

        # Phase 6: NO overflow clamp before symlog (added post-Phase 6)
        q_metaorder = torch.sign(q_metaorder) * torch.log1p(torch.abs(q_metaorder))

        native_manifold = torch.cat([lob_features, q_metaorder], dim=-1)
        x = self.model.input_proj(native_manifold)
        x = self.post_proj_norm(x)

        # Phase 6: tda_layer directly (no residual, no Pre-LN)
        structured_features = self.model.tda_layer(x)
        z_core = self.model.epiplexity_bottleneck(structured_features)

        # Phase 6: global mean pooling (no AttentionPooling)
        pooled_z = torch.mean(z_core, dim=[1, 2])
        prediction = self.model.intent_decoder(pooled_z)
        return prediction


# ============================================================
# Shard discovery (reused from backtest_5a.py pattern)
# ============================================================

def get_val_shards(shard_dir: str, val_split: float = 0.2):
    if shard_dir.startswith("gs://"):
        result = subprocess.run(
            ["gcloud", "storage", "ls", os.path.join(shard_dir, "omega_shard_*.tar")],
            capture_output=True, text=True, check=True, timeout=120
        )
        all_shards = sorted([s.strip() for s in result.stdout.strip().split("\n") if s.strip()])
        n_train = int(len(all_shards) * (1 - val_split))
        val_shards = [f"pipe:gcloud storage cat {s}" for s in all_shards[n_train:]]
    else:
        all_shards = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
        n_train = int(len(all_shards) * (1 - val_split))
        val_shards = all_shards[n_train:]

    logger.info(f"Total shards: {len(all_shards)}, val shards: {len(val_shards)} "
                f"(last {val_split*100:.0f}%)")
    return val_shards


def create_val_loader(val_shards, macro_window, coarse_graining_factor, batch_size):
    preprocess = dynamic_processor(macro_window, coarse_graining_factor)
    dataset = (
        wds.WebDataset(val_shards, resampled=False, handler=wds.warn_and_continue)
        .map(fast_npy_decoder, handler=wds.warn_and_continue)
        .map(preprocess, handler=wds.warn_and_continue)
        .batched(batch_size)
    )
    return DataLoader(dataset, batch_size=None, num_workers=0)


# ============================================================
# Step 0: Target statistics (model-independent)
# ============================================================

def step0_target_statistics(val_shards, macro_window, coarse_graining_factor,
                            batch_size):
    logger.info("=" * 60)
    logger.info("STEP 0: TARGET DISTRIBUTION STATISTICS (model-independent)")
    logger.info("=" * 60)

    loader = create_val_loader(val_shards, macro_window, coarse_graining_factor,
                               batch_size)
    all_targets = []
    for batch_i, batch in enumerate(loader):
        all_targets.append(batch["target"].numpy().copy())
        if (batch_i + 1) % 200 == 0:
            n = sum(len(t) for t in all_targets)
            logger.info(f"  collected {n} targets...")

    targets = np.concatenate(all_targets)
    logger.info(f"  Total samples: {len(targets)}")

    stats = {
        "n_samples": int(len(targets)),
        "target_mean_bp": float(np.mean(targets)),
        "target_std_bp": float(np.std(targets)),
        "target_median_bp": float(np.median(targets)),
        "target_skew": float(skew(targets)),
        "target_kurtosis": float(kurtosis(targets)),  # Fisher (excess)
        "target_min_bp": float(np.min(targets)),
        "target_max_bp": float(np.max(targets)),
        "target_p1": float(np.percentile(targets, 1)),
        "target_p5": float(np.percentile(targets, 5)),
        "target_p25": float(np.percentile(targets, 25)),
        "target_p75": float(np.percentile(targets, 75)),
        "target_p95": float(np.percentile(targets, 95)),
        "target_p99": float(np.percentile(targets, 99)),
        "data_snr_mean_over_std": float(np.mean(targets) / np.std(targets)),
    }

    logger.info(f"  Mean:     {stats['target_mean_bp']:.4f} BP")
    logger.info(f"  Std:      {stats['target_std_bp']:.4f} BP")
    logger.info(f"  Skew:     {stats['target_skew']:.4f}")
    logger.info(f"  Kurtosis: {stats['target_kurtosis']:.4f} (excess)")
    logger.info(f"  Range:    [{stats['target_min_bp']:.1f}, {stats['target_max_bp']:.1f}] BP")
    logger.info(f"  P1/P99:   [{stats['target_p1']:.1f}, {stats['target_p99']:.1f}] BP")
    logger.info(f"  Data SNR (mean/std): {stats['data_snr_mean_over_std']:.6f} "
                f"({stats['data_snr_mean_over_std']*100:.3f}%)")
    return stats


# ============================================================
# Step 1: Phase 6 Oracle Test
# ============================================================

def step1_phase6_retest(checkpoint_path, val_shards, device,
                        macro_window, coarse_graining_factor, batch_size):
    logger.info("=" * 60)
    logger.info("STEP 1: PHASE 6 ORACLE TEST (window=(4,4), hd=64)")
    logger.info("=" * 60)

    # --- Download checkpoint if GCS ---
    if checkpoint_path.startswith("gs://"):
        local_path = "/tmp/phase6_best.pt"
        logger.info(f"  Downloading {checkpoint_path} ...")
        subprocess.run(
            ["gsutil", "cp", checkpoint_path, local_path],
            check=True, timeout=300
        )
        checkpoint_path = local_path

    # --- Build model ---
    model = Phase6Inference(hidden_dim=64, window_size=(4, 4)).to(device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"  Model params: {n_params}")

    # --- Load checkpoint ---
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=False)
    state = {}
    for k, v in ckpt["model_state_dict"].items():
        if k.startswith("_orig_mod."):
            k = k[len("_orig_mod."):]
        if k.startswith("masking."):
            continue
        state[k] = v

    result = model.load_state_dict(state, strict=False)

    # Phase 13 components will be missing — that's expected. Exact set check (Codex audit fix).
    expected_missing = {
        'model.tda_pre_ln.weight', 'model.tda_pre_ln.bias',
        'model.attention_pool.W_pool'
    }
    actual_missing = set(result.missing_keys)
    if actual_missing != expected_missing:
        extra = actual_missing - expected_missing
        absent = expected_missing - actual_missing
        logger.error(f"  Missing keys mismatch!")
        if extra:
            logger.error(f"  Unexpected missing: {extra}")
        if absent:
            logger.error(f"  Expected missing but found: {absent}")
        logger.error("  Checkpoint may be incompatible. Aborting.")
        return {"error": f"missing keys mismatch: extra={extra}, absent={absent}"}
    if result.unexpected_keys:
        logger.warning(f"  Unexpected keys in checkpoint: {result.unexpected_keys}")

    logger.info(f"  Loaded {len(state)} keys. Expected missing (Phase 13 components): "
                f"{sorted(actual_missing)}")
    model.eval()

    # --- Inference ---
    loader = create_val_loader(val_shards, macro_window, coarse_graining_factor,
                               batch_size)
    all_preds = []
    all_targets = []
    n_samples = 0

    with torch.no_grad():
        for batch_i, batch in enumerate(loader):
            manifold = batch["manifold_2d"].to(device)
            c_friction = batch["c_friction"].to(device).unsqueeze(-1)
            target = batch["target"]

            prediction = model(manifold, c_friction)
            pred_bp = (prediction.view(-1) * 10000.0).cpu()

            all_preds.append(pred_bp.numpy().copy())
            all_targets.append(target.numpy().copy())
            n_samples += target.shape[0]

            if (batch_i + 1) % 100 == 0:
                logger.info(f"  Processed {n_samples} samples...")

    preds = np.concatenate(all_preds)
    targets = np.concatenate(all_targets)
    logger.info(f"  Total samples: {len(preds)}")
    logger.info(f"  Pred range: [{preds.min():.2f}, {preds.max():.2f}] BP, "
                f"std={preds.std():.2f} BP")

    # --- Metrics ---
    pearson_ic = float(np.corrcoef(preds, targets)[0, 1])
    rank_ic, rank_ic_pval = spearmanr(preds, targets)
    rank_ic = float(rank_ic)
    rank_ic_pval = float(rank_ic_pval)

    # Decile analysis (from backtest_5a.py pattern)
    decile_results = []
    for i in range(10):
        if i == 0:
            mask = preds <= np.percentile(preds, 10)
        elif i == 9:
            mask = preds >= np.percentile(preds, 90)
        else:
            lo = np.percentile(preds, i * 10)
            hi = np.percentile(preds, (i + 1) * 10)
            mask = (preds > lo) & (preds <= hi)

        bt = targets[mask]
        n = len(bt)
        mean_ret = float(np.mean(bt)) if n > 0 else 0.0
        hit_rate = float(np.mean(bt > 0)) if n > 0 else 0.0
        wins = bt[bt > 0]
        losses = bt[bt < 0]
        mean_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
        mean_loss = float(np.mean(np.abs(losses))) if len(losses) > 0 else 0.0
        payoff_ratio = mean_win / mean_loss if mean_loss > 0 else float('inf')

        decile_results.append({
            "decile": f"D{i}",
            "n": int(n),
            "mean_actual_bp": mean_ret,
            "hit_rate": hit_rate,
            "payoff_ratio": payoff_ratio,
        })

    d9_mean = decile_results[9]["mean_actual_bp"]
    d0_mean = decile_results[0]["mean_actual_bp"]
    d9_d0_spread = d9_mean - d0_mean

    decile_means = [d["mean_actual_bp"] for d in decile_results]
    monotonic_score = sum(1 for i in range(9) if decile_means[i] < decile_means[i + 1])

    # --- Branch gate ---
    if rank_ic <= 0.01 or d9_d0_spread <= 2.0:
        branch = "A"
        branch_reason = (f"Phase 6 signal dead/negligible "
                         f"(RankIC={rank_ic:.4f}, D9-D0={d9_d0_spread:.2f} BP)")
    elif rank_ic > 0.05 and d9_d0_spread > 10.0:
        branch = "B"
        branch_reason = (f"Phase 6 signal STRONG — STOP THE WORLD "
                         f"(RankIC={rank_ic:.4f}, D9-D0={d9_d0_spread:.2f} BP)")
    else:
        branch = "C"
        branch_reason = (f"Gray zone — both paths remain viable "
                         f"(RankIC={rank_ic:.4f}, D9-D0={d9_d0_spread:.2f} BP)")

    results = {
        "n_samples": int(len(preds)),
        "pearson_ic": pearson_ic,
        "rank_ic": rank_ic,
        "rank_ic_pval": rank_ic_pval,
        "r_squared": float(pearson_ic ** 2),
        "d9_mean_bp": d9_mean,
        "d0_mean_bp": d0_mean,
        "d9_d0_spread_bp": d9_d0_spread,
        "monotonicity_score": f"{monotonic_score}/9",
        "pred_std_bp": float(preds.std()),
        "deciles": decile_results,
        "branch": branch,
        "branch_reason": branch_reason,
    }

    # --- Print report ---
    logger.info("")
    logger.info(f"  Pearson IC:  {pearson_ic:.6f}")
    logger.info(f"  Rank IC:     {rank_ic:.6f} (p={rank_ic_pval:.2e})")
    logger.info(f"  D9 mean:     {d9_mean:.2f} BP")
    logger.info(f"  D0 mean:     {d0_mean:.2f} BP")
    logger.info(f"  D9-D0:       {d9_d0_spread:.2f} BP")
    logger.info(f"  Monotonicity: {monotonic_score}/9")
    logger.info("")
    logger.info(f"  {'Decile':<8} {'N':>8} {'MeanBP':>10} {'HitRate':>8} {'PayoffR':>8}")
    logger.info("  " + "-" * 45)
    for d in decile_results:
        pr = f"{d['payoff_ratio']:.2f}" if d['payoff_ratio'] != float('inf') else "inf"
        logger.info(f"  {d['decile']:<8} {d['n']:>8} {d['mean_actual_bp']:>10.2f} "
                     f"{d['hit_rate']:>8.3f} {pr:>8}")
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"  BRANCH: {branch}")
    logger.info(f"  {branch_reason}")
    logger.info("=" * 60)

    return results


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Phase 14 Step 0+1: Data Baseline + Phase 6 Oracle Test"
    )
    parser.add_argument("--shard_dir",
                        default="gs://omega-pure-data/wds_shards_v3_full/")
    parser.add_argument("--checkpoint",
                        default="gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt")
    parser.add_argument("--output_dir", default="./reports/phase14")
    parser.add_argument("--val_split", type=float, default=0.2)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--macro_window", type=int, default=160)
    parser.add_argument("--coarse_graining_factor", type=int, default=1)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # --- Shard discovery ---
    val_shards = get_val_shards(args.shard_dir, args.val_split)
    if not val_shards:
        logger.error("No validation shards found!")
        sys.exit(1)

    # --- Step 0 ---
    step0_results = step0_target_statistics(
        val_shards, args.macro_window, args.coarse_graining_factor,
        args.batch_size
    )

    # --- Step 1 ---
    step1_results = step1_phase6_retest(
        args.checkpoint, val_shards, device,
        args.macro_window, args.coarse_graining_factor, args.batch_size
    )

    # --- Save combined results ---
    combined = {
        "step0_target_statistics": step0_results,
        "step1_phase6_retest": step1_results,
        "config": {
            "shard_dir": args.shard_dir,
            "checkpoint": args.checkpoint,
            "val_split": args.val_split,
            "batch_size": args.batch_size,
            "macro_window": args.macro_window,
            "phase6_window_size": [4, 4],
            "phase6_hidden_dim": 64,
        }
    }

    output_path = os.path.join(args.output_dir, "phase14_step0_step1.json")
    with open(output_path, "w") as f:
        json.dump(combined, f, indent=2)
    logger.info(f"\nResults saved to {output_path}")

    # --- Final verdict ---
    branch = step1_results.get("branch", "ERROR")
    logger.info(f"\n{'='*60}")
    logger.info(f"PHASE 14 ORACLE TEST COMPLETE")
    logger.info(f"BRANCH: {branch}")
    if branch == "A":
        logger.info("Next: Phase 13 confirmed as baseline → proceed to Step 2 (Macro Bypass A/B)")
    elif branch == "B":
        logger.info("Next: STOP THE WORLD — Phase 6 signal strong, investigate small-window topology")
    elif branch == "C":
        logger.info("Next: Gray zone — proceed to Step 2 + add multi-scale windowing to backlog")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
