"""
Phase 7 Step 2: Full Inference (T29 Flagship, hd=64)
-----------------------------------------------------
Run T29 model on ALL 1992 shards. Output predictions.parquet with:
  symbol, date, shard_idx, pred_bp, target_bp, bid_p1, ask_p1, macro_v_d, z_sparsity

Includes z_core hook for M3 (MDL compression efficiency) metric.

Usage (linux1, CPU, via systemd-run):
  systemd-run --slice=heavy-workload.slice --scope \
    python3 phase7_inference.py \
      --checkpoint /omega_pool/phase7/best_t29.pt \
      --shard_dir /omega_pool/wds_shards_v3_full/ \
      --date_map /omega_pool/phase7/shard_date_map.json \
      --output /omega_pool/phase7/predictions.parquet \
      --hidden_dim 64 --window_size_t 32 --batch_size 512
"""

import os
import re
import sys
import glob
import json
import time
import pickle
import argparse
import logging

import torch
import torch.nn.functional as F
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# Target stats from TRAIN split (no look-ahead)
TARGET_MEAN = -5.08
TARGET_STD = 216.24

# ============================================================
# Model (same as backtest_5a.py, inference-only)
# ============================================================

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gcp'))

from omega_epiplexity_plus_core import OmegaMathematicalCompressor


class OmegaTIBInference(torch.nn.Module):
    def __init__(self, hidden_dim=64, window_size=(32, 10)):
        super().__init__()
        self.model = OmegaMathematicalCompressor(hidden_dim, window_size)
        self.post_proj_norm = torch.nn.LayerNorm(hidden_dim)
        self._z_core = None  # Hook storage

    def forward(self, x_2d, c_friction):
        B, T, S, C = x_2d.shape

        # Physics layer (non-learnable)
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

        q_metaorder = torch.sign(q_metaorder) * torch.log1p(torch.abs(q_metaorder))
        native_manifold = torch.cat([lob_features, q_metaorder], dim=-1)

        x = self.model.input_proj(native_manifold)
        x = self.post_proj_norm(x)
        structured_features = self.model.tda_layer(x)
        z_core = self.model.epiplexity_bottleneck(structured_features)

        # Store z_core for sparsity analysis (M3)
        self._z_core = z_core.detach()

        pooled_z = torch.mean(z_core, dim=[1, 2])
        prediction = self.model.intent_decoder(pooled_z)
        return prediction


def compute_z_sparsity(z_core, threshold=0.01):
    """L0-like sparsity: fraction of near-zero activations."""
    total = z_core.numel()
    near_zero = (z_core.abs() < threshold).sum().item()
    return near_zero / total


def parse_symbol_from_key(key):
    """Parse WebDataset __key__: '600519_SH_000000042' → ('600519.SH', 42)"""
    match = re.match(r'^(.+)_(\d{9})$', key)
    if not match:
        return None, None
    munged_sym, idx_str = match.group(1), match.group(2)
    # Reverse: last '_XX' → '.XX'
    parts = munged_sym.rsplit('_', 1)
    if len(parts) == 2 and len(parts[1]) <= 3:
        symbol = f"{parts[0]}.{parts[1]}"
    else:
        symbol = munged_sym
    return symbol, int(idx_str)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--shard_dir", required=True)
    parser.add_argument("--date_map", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch_size", type=int, default=512)
    parser.add_argument("--hidden_dim", type=int, default=64)
    parser.add_argument("--window_size_t", type=int, default=32)
    parser.add_argument("--window_size_s", type=int, default=10)
    parser.add_argument("--macro_window", type=int, default=160)
    parser.add_argument("--checkpoint_interval", type=int, default=200,
                        help="Save progress every N shards")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    device = torch.device("cpu")
    torch.set_num_threads(16)  # linux1 has 32 cores, use 16 for inference
    log.info(f"Device: {device}, threads: 16")

    # Load date map
    with open(args.date_map) as f:
        date_map = json.load(f)
    shard_to_date = date_map["shard_to_date"]
    log.info(f"Date map: {date_map['total_dates']} dates, {date_map['total_shards']} shards")

    # Load model
    model = OmegaTIBInference(
        hidden_dim=args.hidden_dim,
        window_size=(args.window_size_t, args.window_size_s),
    ).to(device)

    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    state = {}
    for k, v in ckpt["model_state_dict"].items():
        if k.startswith("masking."):
            continue
        state[k] = v
    model.load_state_dict(state, strict=False)
    model.eval()
    log.info(f"Model loaded: hd={args.hidden_dim}, wt={args.window_size_t}")

    # Discover shards
    all_shards = sorted(glob.glob(os.path.join(args.shard_dir, "omega_shard_*.tar")))
    log.info(f"Total shards: {len(all_shards)}")

    # F4 FIX: Columnar accumulation + chunked parquet writes to avoid OOM.
    # Instead of 9.96M dicts in a list, we accumulate columns and flush
    # to parquet chunk files every checkpoint_interval shards.
    col_symbol, col_date, col_shard = [], [], []
    col_pred, col_target = [], []
    col_bid, col_ask, col_mvd = [], [], []
    chunk_files = []
    chunk_dir = args.output + ".chunks"
    os.makedirs(chunk_dir, exist_ok=True)

    progress_path = args.output + ".progress.pkl"
    start_shard = 0
    z_sparsity_accum = []
    samples_written = 0

    if args.resume and os.path.exists(progress_path):
        with open(progress_path, "rb") as f:
            saved = pickle.load(f)
        start_shard = saved["next_shard"]
        z_sparsity_accum = saved.get("z_sparsity", [])
        chunk_files = saved.get("chunk_files", [])
        samples_written = saved.get("samples_written", 0)
        log.info(f"Resumed from shard {start_shard}, {samples_written} samples in {len(chunk_files)} chunks")

    # Import WebDataset
    import webdataset as wds
    from torch.utils.data import DataLoader

    # Process shards one-by-one for key access
    t0 = time.time()
    samples_total = len(results)

    for shard_i, shard_path in enumerate(all_shards):
        if shard_i < start_shard:
            continue

        shard_num = int(os.path.basename(shard_path).split("_")[-1].split(".")[0])
        date_str = shard_to_date.get(str(shard_num), "unknown")

        # Build dataset for single shard
        dataset = (
            wds.WebDataset([shard_path], resampled=False, handler=wds.warn_and_continue)
            .decode(handler=wds.warn_and_continue)
        )

        # Collect samples from shard
        batch_manifolds = []
        batch_c_frictions = []
        batch_targets = []
        batch_symbols = []
        batch_meta = []  # (bid_p1, ask_p1, macro_v_d)

        for sample in dataset:
            key = sample.get("__key__", "")
            symbol, sample_idx = parse_symbol_from_key(key)
            if symbol is None:
                continue

            matrix = sample.get("manifold_2d.npy")
            if matrix is None:
                continue

            tensor = torch.tensor(matrix, dtype=torch.float32)
            if args.macro_window < tensor.shape[0]:
                tensor = tensor[-args.macro_window:, :, :]

            c_val = float(sample.get("c_friction.npy", np.array([0.842]))[0])
            t_val = float(sample.get("target.npy", np.array([0.0]))[0])

            # Extract LOB data for limit detection (last bar, depth 0)
            last_bar = tensor[-1, 0, :]  # [10]
            bid_p1 = float(last_bar[0])
            ask_p1 = float(last_bar[2])
            macro_v_d = float(last_bar[8])

            batch_manifolds.append(tensor)
            batch_c_frictions.append(c_val)
            batch_targets.append(t_val)
            batch_symbols.append(symbol)
            batch_meta.append((bid_p1, ask_p1, macro_v_d))

        if not batch_manifolds:
            continue

        # Mini-batch inference (avoid CPU L3 cache thrashing with full shard [5000,...])
        manifold_all = torch.stack(batch_manifolds).to(device)
        c_all = torch.tensor(batch_c_frictions, dtype=torch.float32).unsqueeze(-1).to(device)

        pred_parts = []
        with torch.no_grad():
            for mb_start in range(0, len(manifold_all), args.batch_size):
                mb_end = min(mb_start + args.batch_size, len(manifold_all))
                mb = manifold_all[mb_start:mb_end]
                cb = c_all[mb_start:mb_end]
                p = model(mb, cb)
                pred_parts.append(p.cpu())

                # z_core sparsity (sample from last mini-batch)
                if model._z_core is not None:
                    z_sparsity_accum.append(compute_z_sparsity(model._z_core))

            preds = torch.cat(pred_parts)
            pred_bp = (preds.squeeze() * TARGET_STD + TARGET_MEAN).numpy().copy()

        targets_np = np.array(batch_targets)

        # F4 FIX: Columnar accumulation (no dict-per-sample)
        for i in range(len(batch_symbols)):
            bid_p1, ask_p1, mvd = batch_meta[i]
            col_symbol.append(batch_symbols[i])
            col_date.append(date_str)
            col_shard.append(shard_num)
            col_pred.append(float(pred_bp[i]) if pred_bp.ndim > 0 else float(pred_bp))
            col_target.append(float(targets_np[i]))
            col_bid.append(bid_p1)
            col_ask.append(ask_p1)
            col_mvd.append(mvd)

        samples_total = samples_written + len(col_symbol)

        # Progress logging
        if (shard_i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = (shard_i + 1 - start_shard) / elapsed * 3600
            eta_h = (len(all_shards) - shard_i - 1) / rate if rate > 0 else 0
            avg_sparsity = np.mean(z_sparsity_accum) if z_sparsity_accum else 0
            log.info(f"Shard {shard_i+1}/{len(all_shards)} | "
                     f"Samples: {samples_total:,} | "
                     f"Rate: {rate:.0f} shards/h | "
                     f"ETA: {eta_h:.1f}h | "
                     f"z_sparsity: {avg_sparsity:.3f}")

        # F4 FIX: Flush to parquet chunk every checkpoint_interval shards
        if (shard_i + 1) % args.checkpoint_interval == 0 and col_symbol:
            import pyarrow as pa
            import pyarrow.parquet as pq

            chunk_path = os.path.join(chunk_dir, f"chunk_{len(chunk_files):04d}.parquet")
            table = pa.table({
                "symbol": col_symbol, "date": col_date, "shard_idx": col_shard,
                "pred_bp": col_pred, "target_bp": col_target,
                "bid_p1": col_bid, "ask_p1": col_ask, "macro_v_d": col_mvd,
            })
            pq.write_table(table, chunk_path)
            chunk_files.append(chunk_path)
            samples_written += len(col_symbol)
            col_symbol, col_date, col_shard = [], [], []
            col_pred, col_target = [], []
            col_bid, col_ask, col_mvd = [], [], []

            # Save lightweight progress (no data, just pointers)
            tmp_path = progress_path + ".tmp"
            with open(tmp_path, "wb") as f:
                pickle.dump({
                    "next_shard": shard_i + 1,
                    "z_sparsity": z_sparsity_accum,
                    "chunk_files": chunk_files,
                    "samples_written": samples_written,
                }, f, protocol=4)
            os.replace(tmp_path, progress_path)
            log.info(f"Chunk {len(chunk_files)} saved ({samples_written:,} samples total)")

    # Flush remaining data
    if col_symbol:
        import pyarrow as pa
        import pyarrow.parquet as pq

        chunk_path = os.path.join(chunk_dir, f"chunk_{len(chunk_files):04d}.parquet")
        table = pa.table({
            "symbol": col_symbol, "date": col_date, "shard_idx": col_shard,
            "pred_bp": col_pred, "target_bp": col_target,
            "bid_p1": col_bid, "ask_p1": col_ask, "macro_v_d": col_mvd,
        })
        pq.write_table(table, chunk_path)
        chunk_files.append(chunk_path)
        samples_written += len(col_symbol)

    # Merge all chunks into final parquet
    log.info(f"Merging {len(chunk_files)} chunks ({samples_written:,} samples)...")
    import pyarrow as pa
    import pyarrow.parquet as pq

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    tables = [pq.read_table(cf) for cf in chunk_files]
    merged = pa.concat_tables(tables)
    pq.write_table(merged, args.output)

    # Summary
    avg_sparsity = np.mean(z_sparsity_accum) if z_sparsity_accum else 0
    elapsed = time.time() - t0
    log.info(f"Done: {len(results):,} samples in {elapsed/3600:.1f}h")
    log.info(f"M3 z_core avg sparsity: {avg_sparsity:.4f} ({avg_sparsity*100:.1f}%)")
    log.info(f"Output: {args.output}")

    # Save z_sparsity summary
    meta_path = args.output + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump({
            "total_samples": len(results),
            "z_core_sparsity_mean": avg_sparsity,
            "z_core_sparsity_pct": avg_sparsity * 100,
            "elapsed_hours": elapsed / 3600,
            "model": f"T29 hd={args.hidden_dim} wt={args.window_size_t}",
        }, f, indent=2)

    # Cleanup progress file
    if os.path.exists(progress_path):
        os.remove(progress_path)


if __name__ == "__main__":
    main()
