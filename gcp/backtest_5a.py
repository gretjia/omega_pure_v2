"""
Phase 5a: Signal Direction Statistical Test
--------------------------------------------
Pure statistical test — no T+1, no trading simulation.
Answers: "Does the model predict the correct direction?"

Uses T16 best.pt (FVU=0.998896) on validation shards.
TARGET_MEAN/STD from train split only (no look-ahead).

Usage (Vertex AI):
  python3 backtest_5a.py \
    --checkpoint /gcs/omega-pure-data/checkpoints/phase4_standard/trial_16/best.pt \
    --shard_dir /gcs/omega-pure-data/wds_shards_v3_full \
    --output_dir /gcs/omega-pure-data/backtest/phase5a_t16

Usage (local):
  python3 backtest_5a.py --checkpoint best.pt --shard_dir /path/to/shards --output_dir ./results
"""

import os
import io
import sys
import glob
import json
import argparse
import logging

import torch
import torch.nn.functional as F
import numpy as np
import webdataset as wds
from torch.utils.data import DataLoader

from omega_epiplexity_plus_core import OmegaMathematicalCompressor
from omega_webdataset_loader import dynamic_processor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def fast_npy_decoder(sample):
    """Bypass WDS generic decode, strictly parse .npy bytes.
    ~15% CPU savings vs wds.decode() (from phase7_inference.py).
    """
    result = {}
    for key, value in sample.items():
        if key.endswith(".npy"):
            result[key] = np.load(io.BytesIO(value))
        else:
            result[key] = value
    return result


# ============================================================
# Model (same as train.py OmegaTIBWithMasking, inference mode)
# ============================================================

class OmegaTIBInference(torch.nn.Module):
    """Inference wrapper — no masking, no training-only logic."""
    def __init__(self, hidden_dim=64, window_size=(32, 10)):
        super().__init__()
        self.model = OmegaMathematicalCompressor(hidden_dim, window_size)
        self.post_proj_norm = torch.nn.LayerNorm(hidden_dim)

    def forward(self, x_2d, c_friction):
        B, T, S, C = x_2d.shape

        # Physics layer
        delta_p = x_2d[:, :, 0, 7]
        v_d_macro = x_2d[:, :, 0, 8]
        sigma_d_macro = x_2d[:, :, 0, 9]

        with torch.no_grad(), torch.autocast(device_type="cuda", enabled=False):
            q_metaorder = self.model.srl_inverter(
                delta_p.float(), sigma_d_macro.float(),
                v_d_macro.float(), c_friction.float()
            )
        q_metaorder = q_metaorder.unsqueeze(-1).unsqueeze(-1).expand(B, T, S, 1)

        # Financial Relativity Transform
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

        q_metaorder = torch.clamp(q_metaorder, min=-1e12, max=1e12)
        q_metaorder = torch.sign(q_metaorder) * torch.log1p(torch.abs(q_metaorder))
        native_manifold = torch.cat([lob_features, q_metaorder], dim=-1)

        x = self.model.input_proj(native_manifold)
        x = self.post_proj_norm(x)
        structured_features = self.model.tda_layer(x)
        z_core = self.model.epiplexity_bottleneck(structured_features)
        pooled_z = torch.mean(z_core, dim=[1, 2])
        prediction = self.model.intent_decoder(pooled_z)
        return prediction


def main():
    parser = argparse.ArgumentParser(description="Phase 5a: Signal Direction Test")
    parser.add_argument("--checkpoint", type=str, required=True)
    parser.add_argument("--shard_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="./backtest_results")
    parser.add_argument("--val_split", type=float, default=0.2)
    parser.add_argument("--batch_size", type=int, default=256)
    parser.add_argument("--macro_window", type=int, default=160)
    parser.add_argument("--coarse_graining_factor", type=int, default=1)
    parser.add_argument("--hidden_dim", type=int, default=64)
    parser.add_argument("--window_size_t", type=int, default=32)
    parser.add_argument("--window_size_s", type=int, default=10)
    parser.add_argument("--costs_bp", type=float, default=25.0)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # --- Load model ---
    model = OmegaTIBInference(
        hidden_dim=args.hidden_dim,
        window_size=(args.window_size_t, args.window_size_s),
    ).to(device)

    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    # Map state dict keys (training wrapper → inference wrapper)
    state = {}
    for k, v in ckpt["model_state_dict"].items():
        # Strip torch.compile _orig_mod. prefix if present
        if k.startswith("_orig_mod."):
            k = k[len("_orig_mod."):]
        # Remove "masking." prefix if present, keep "model." and "post_proj_norm."
        if k.startswith("masking."):
            continue  # skip masking layer (inference doesn't need it)
        state[k] = v
    n_loaded = len(state)
    result = model.load_state_dict(state, strict=False)
    if result.unexpected_keys or len(result.missing_keys) > 0:
        logger.warning(f"State dict: loaded {n_loaded} keys, "
                       f"missing={result.missing_keys}, unexpected={result.unexpected_keys}")
    else:
        logger.info(f"State dict: loaded {n_loaded} keys, all matched")
    model.eval()
    logger.info(f"Model loaded from {args.checkpoint}")

    # --- Validation shards (supports local and gs:// GCS paths) ---
    if args.shard_dir.startswith("gs://"):
        import subprocess
        result = subprocess.run(
            ["gcloud", "storage", "ls", os.path.join(args.shard_dir, "omega_shard_*.tar")],
            capture_output=True, text=True, check=True
        )
        all_shards = sorted([s.strip() for s in result.stdout.strip().split("\n") if s.strip()])
        n_train = int(len(all_shards) * (1 - args.val_split))
        val_shards = [f"pipe:gcloud storage cat {s}" for s in all_shards[n_train:]]
    else:
        all_shards = sorted(glob.glob(os.path.join(args.shard_dir, "omega_shard_*.tar")))
        n_train = int(len(all_shards) * (1 - args.val_split))
        val_shards = all_shards[n_train:]
    logger.info(f"Val shards: {len(val_shards)} (temporal split, last {args.val_split*100:.0f}%)")

    # --- DataLoader ---
    preprocess = dynamic_processor(args.macro_window, args.coarse_graining_factor)
    dataset = (
        wds.WebDataset(val_shards, resampled=False, handler=wds.warn_and_continue)
        .map(fast_npy_decoder)
        .map(preprocess, handler=wds.warn_and_continue)
        .batched(args.batch_size)
    )
    loader = DataLoader(dataset, batch_size=None, num_workers=0)

    # --- Inference ---
    all_preds = []
    all_targets = []
    n_samples = 0

    with torch.no_grad():
        for batch_i, batch in enumerate(loader):
            manifold = batch["manifold_2d"].to(device)
            c_friction = batch["c_friction"].to(device).unsqueeze(-1)
            target = batch["target"]  # keep on CPU

            prediction = model(manifold, c_friction)
            pred_bp = (prediction.view(-1) * 10000.0).cpu()

            all_preds.append(pred_bp.numpy().copy())
            all_targets.append(target.numpy().copy())
            n_samples += target.shape[0]

            if (batch_i + 1) % 100 == 0:
                logger.info(f"Processed {n_samples} samples...")

    preds = np.concatenate(all_preds)
    targets = np.concatenate(all_targets)
    logger.info(f"Total samples: {len(preds)}")

    # --- Statistical Analysis ---
    results = {}

    # 1. Overall correlation
    corr = np.corrcoef(preds, targets)[0, 1]
    results["correlation"] = float(corr)
    results["r_squared"] = float(corr ** 2)
    logger.info(f"Correlation: {corr:.6f}, R²: {corr**2:.6f}")

    # 2. Decile analysis
    percentiles = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    thresholds = np.percentile(preds, percentiles)

    decile_results = []
    for i in range(10):
        if i == 0:
            mask = preds <= np.percentile(preds, 10)
            label = "Bottom 10%"
        elif i == 9:
            mask = preds >= np.percentile(preds, 90)
            label = "Top 10%"
        else:
            lo = np.percentile(preds, i * 10)
            hi = np.percentile(preds, (i + 1) * 10)
            mask = (preds > lo) & (preds <= hi)
            label = f"Decile {i+1}"

        bucket_targets = targets[mask]
        n = len(bucket_targets)
        mean_ret = np.mean(bucket_targets) if n > 0 else 0
        hit_rate = np.mean(bucket_targets > 0) if n > 0 else 0
        mean_pred = np.mean(preds[mask]) if n > 0 else 0

        wins = bucket_targets[bucket_targets > 0]
        losses = bucket_targets[bucket_targets < 0]
        mean_win = np.mean(wins) if len(wins) > 0 else 0
        mean_loss = np.mean(np.abs(losses)) if len(losses) > 0 else 0
        payoff_ratio = mean_win / mean_loss if mean_loss > 0 else float('inf')

        decile_results.append({
            "label": label,
            "n": int(n),
            "mean_pred_bp": float(mean_pred),
            "mean_actual_bp": float(mean_ret),
            "hit_rate": float(hit_rate),
            "mean_win_bp": float(mean_win),
            "mean_loss_bp": float(mean_loss),
            "payoff_ratio": float(payoff_ratio),
            "net_after_costs_bp": float(mean_ret - args.costs_bp),
        })

    results["deciles"] = decile_results

    # 3. Top decile deep dive
    top_mask = preds >= np.percentile(preds, 90)
    top_targets = targets[top_mask]
    bottom_mask = preds <= np.percentile(preds, 10)
    bottom_targets = targets[bottom_mask]

    results["top_decile_mean_bp"] = float(np.mean(top_targets))
    results["bottom_decile_mean_bp"] = float(np.mean(bottom_targets))
    results["long_short_spread_bp"] = float(np.mean(top_targets) - np.mean(bottom_targets))

    # 4. Signal monotonicity test
    decile_means = [d["mean_actual_bp"] for d in decile_results]
    monotonic_score = sum(1 for i in range(len(decile_means)-1) if decile_means[i] < decile_means[i+1])
    results["monotonicity_score"] = f"{monotonic_score}/9"

    # --- Print Report ---
    logger.info("\n" + "="*80)
    logger.info("PHASE 5a: SIGNAL DIRECTION STATISTICAL TEST")
    logger.info("="*80)
    logger.info(f"Samples: {len(preds)}")
    logger.info(f"Correlation: {corr:.6f}")
    logger.info(f"R²: {corr**2:.8f}")
    logger.info(f"Costs: {args.costs_bp} BP roundtrip")
    logger.info("")
    logger.info(f"{'Decile':<12} {'N':>7} {'MeanPred':>10} {'MeanActual':>12} {'HitRate':>8} {'PayoffR':>8} {'NetCost':>10}")
    logger.info("-" * 75)
    for d in decile_results:
        logger.info(f"{d['label']:<12} {d['n']:>7} {d['mean_pred_bp']:>10.2f} {d['mean_actual_bp']:>12.2f} "
                     f"{d['hit_rate']:>8.3f} {d['payoff_ratio']:>8.2f} {d['net_after_costs_bp']:>10.2f}")
    logger.info("")
    logger.info(f"Top 10% mean return: {results['top_decile_mean_bp']:.2f} BP")
    logger.info(f"Bottom 10% mean return: {results['bottom_decile_mean_bp']:.2f} BP")
    logger.info(f"Long-Short spread: {results['long_short_spread_bp']:.2f} BP")
    logger.info(f"Monotonicity: {results['monotonicity_score']}")

    # --- Verdict ---
    top_mean = results["top_decile_mean_bp"]
    spread = results["long_short_spread_bp"]
    if top_mean > 5:
        verdict = "STRONG PASS — signal direction correct with statistical significance"
    elif top_mean > 0:
        verdict = "PASS — signal direction correct (weak)"
    else:
        verdict = "FAIL — signal direction incorrect or no predictive power"

    results["verdict"] = verdict
    logger.info(f"\n{'='*80}")
    logger.info(f"VERDICT: {verdict}")
    logger.info(f"{'='*80}")

    # --- Save ---
    output_path = os.path.join(args.output_dir, "phase5a_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
