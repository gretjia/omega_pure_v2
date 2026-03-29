"""
Phase 7 Step 2: Full Inference (T29 Flagship, hd=64) — Optimized
-----------------------------------------------------------------
Run T29 model on ALL 1992 shards. Output predictions.parquet with:
  symbol, date, shard_idx, pred_bp, target_bp, bid_p1, ask_p1, macro_v_d, z_sparsity

Optimizations vs v1:
  - ThreadPoolExecutor prefetches next N shards while GPU processes current
  - Vectorized metadata extraction (no per-sample Python loop)
  - Batched WebDataset decode
  - AMP fp16 on GPU

Usage (Vertex AI):
  python3 phase7_inference.py \
    --checkpoint /gcs/omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt \
    --shard_dir /gcs/omega-pure-data/wds_shards_v3_full \
    --date_map /gcs/omega-pure-data/phase7/shard_date_map.json \
    --output /gcs/omega-pure-data/phase7/predictions.parquet \
    --hidden_dim 64 --window_size_t 32 --batch_size 512
"""

import os
import re
import sys
import glob
import json
import time
import pickle
import signal
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, Future

import torch
import torch.nn.functional as F
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# Emergency checkpoint state for SIGTERM handler
_emergency = {"save_fn": None}

def _sigterm_handler(signum, frame):
    log.warning("SIGTERM received — saving emergency checkpoint")
    if _emergency["save_fn"]:
        _emergency["save_fn"]()
    sys.exit(0)

signal.signal(signal.SIGTERM, _sigterm_handler)

TARGET_MEAN = -5.08
TARGET_STD = 216.24

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gcp'))

from omega_epiplexity_plus_core import OmegaMathematicalCompressor


class OmegaTIBInference(torch.nn.Module):
    def __init__(self, hidden_dim=64, window_size=(32, 10)):
        super().__init__()
        self.model = OmegaMathematicalCompressor(hidden_dim, window_size)
        self.post_proj_norm = torch.nn.LayerNorm(hidden_dim)
        self._z_core = None

    def forward(self, x_2d, c_friction):
        B, T, S, C = x_2d.shape
        delta_p = x_2d[:, :, 0, 7]
        v_d_macro = x_2d[:, :, 0, 8]
        sigma_d_macro = x_2d[:, :, 0, 9]

        with torch.no_grad(), torch.autocast(device_type=x_2d.device.type, enabled=False):
            q_metaorder = self.model.srl_inverter(
                delta_p.float(), sigma_d_macro.float(),
                v_d_macro.float(), c_friction.float()
            )
        q_metaorder = q_metaorder.unsqueeze(-1).unsqueeze(-1).expand(B, T, S, 1)

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
        self._z_core = z_core.detach()
        pooled_z = torch.mean(z_core, dim=[1, 2])
        prediction = self.model.intent_decoder(pooled_z)
        return prediction


_KEY_RE = re.compile(r'^(.+)_(\d{9})$')

def load_shard(shard_path, macro_window):
    """Load all samples from a single shard. Runs in thread pool."""
    import webdataset as wds

    dataset = (
        wds.WebDataset([shard_path], resampled=False, handler=wds.warn_and_continue)
        .decode(handler=wds.warn_and_continue)
    )

    manifolds = []
    c_frictions = []
    targets = []
    symbols = []

    try:
        for sample in dataset:
            key = sample.get("__key__", "")
            m = _KEY_RE.match(key)
            if not m:
                continue
            munged_sym = m.group(1)
            parts = munged_sym.rsplit('_', 1)
            symbol = f"{parts[0]}.{parts[1]}" if len(parts) == 2 and len(parts[1]) <= 3 else munged_sym

            matrix = sample.get("manifold_2d.npy")
            if matrix is None:
                continue

            if matrix.shape[0] > macro_window:
                matrix = matrix[-macro_window:]

            manifolds.append(matrix)
            c_frictions.append(float(sample.get("c_friction.npy", np.array([0.842]))[0]))
            targets.append(float(sample.get("target.npy", np.array([0.0]))[0]))
            symbols.append(symbol)
    except (ValueError, RuntimeError, Exception) as e:
        pass  # Empty/corrupt shard, skip silently

    if not manifolds:
        return None

    # Stack into numpy arrays (avoid per-sample torch.tensor overhead)
    manifold_np = np.stack(manifolds)  # [N, T, S, F]
    c_np = np.array(c_frictions, dtype=np.float32)
    t_np = np.array(targets, dtype=np.float32)

    # Extract metadata vectorized from last bar, depth 0
    last_bars = manifold_np[:, -1, 0, :]  # [N, F]
    bid_p1 = last_bars[:, 0].astype(np.float64)
    ask_p1 = last_bars[:, 2].astype(np.float64)
    macro_v_d = last_bars[:, 8].astype(np.float64)

    return {
        "manifold": manifold_np,
        "c_friction": c_np,
        "target": t_np,
        "symbols": symbols,
        "bid_p1": bid_p1,
        "ask_p1": ask_p1,
        "macro_v_d": macro_v_d,
    }


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
    parser.add_argument("--checkpoint_interval", type=int, default=100,
                        help="Save progress every N shards")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--prefetch", type=int, default=4,
                        help="Number of shards to prefetch in parallel")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(16)
    log.info(f"Device: {device}, prefetch: {args.prefetch}")

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
    state = {k: v for k, v in ckpt["model_state_dict"].items() if not k.startswith("masking.")}
    model.load_state_dict(state, strict=False)
    model.eval()
    log.info(f"Model loaded: hd={args.hidden_dim}, wt={args.window_size_t}")

    # Discover shards
    all_shards = sorted(glob.glob(os.path.join(args.shard_dir, "omega_shard_*.tar")))
    log.info(f"Total shards: {len(all_shards)}")

    # Columnar accumulation
    import pyarrow as pa
    import pyarrow.parquet as pq

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
        log.info(f"Resumed from shard {start_shard}, {samples_written:,} samples in {len(chunk_files)} chunks")

    t0 = time.time()
    samples_total = samples_written
    _current_shard_i = [start_shard]

    def _save_emergency_checkpoint():
        si = _current_shard_i[0]
        if col_symbol:
            cp = os.path.join(chunk_dir, f"chunk_{len(chunk_files):04d}.parquet")
            t = pa.table({"symbol": col_symbol, "date": col_date, "shard_idx": col_shard,
                          "pred_bp": col_pred, "target_bp": col_target,
                          "bid_p1": col_bid, "ask_p1": col_ask, "macro_v_d": col_mvd})
            pq.write_table(t, cp)
            chunk_files.append(cp)
            sw = samples_written + len(col_symbol)
        else:
            sw = samples_written
        with open(progress_path, "wb") as f:
            pickle.dump({"next_shard": si, "z_sparsity": z_sparsity_accum,
                         "chunk_files": chunk_files, "samples_written": sw}, f, protocol=4)
        log.info(f"Emergency checkpoint saved at shard {si}, {sw:,} samples")

    _emergency["save_fn"] = _save_emergency_checkpoint

    # --- Main loop with prefetch ---
    shards_to_process = [(i, p) for i, p in enumerate(all_shards) if i >= start_shard]

    with ThreadPoolExecutor(max_workers=args.prefetch) as executor:
        # Submit initial prefetch batch
        futures = {}
        for shard_i, shard_path in shards_to_process[:args.prefetch]:
            futures[shard_i] = executor.submit(load_shard, shard_path, args.macro_window)

        # Process queue pointer for submitting new prefetch tasks
        next_submit = args.prefetch

        for idx, (shard_i, shard_path) in enumerate(shards_to_process):
            _current_shard_i[0] = shard_i

            shard_num = int(os.path.basename(shard_path).split("_")[-1].split(".")[0])
            date_str = shard_to_date.get(str(shard_num), "unknown")

            # Wait for this shard's data
            data = futures[shard_i].result()
            del futures[shard_i]

            # Submit next prefetch
            if next_submit < len(shards_to_process):
                next_i, next_p = shards_to_process[next_submit]
                futures[next_i] = executor.submit(load_shard, next_p, args.macro_window)
                next_submit += 1

            if data is None:
                continue

            n_samples = len(data["manifold"])

            # Transfer to GPU as single tensor (one H2D copy, not per-sample)
            manifold_all = torch.from_numpy(data["manifold"]).float().to(device)
            c_all = torch.from_numpy(data["c_friction"]).float().unsqueeze(-1).to(device)

            # GPU inference in mini-batches
            pred_parts = []
            use_amp = device.type == "cuda"
            with torch.inference_mode():
                for mb_start in range(0, n_samples, args.batch_size):
                    mb_end = min(mb_start + args.batch_size, n_samples)
                    mb = manifold_all[mb_start:mb_end]
                    cb = c_all[mb_start:mb_end]
                    with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=use_amp):
                        p = model(mb, cb)
                    pred_parts.append(p.float().cpu())

                    if model._z_core is not None:
                        z_sparsity_accum.append(
                            (model._z_core.abs() < 0.01).float().mean().item()
                        )

            preds = torch.cat(pred_parts)
            pred_bp = (preds.view(-1) * TARGET_STD + TARGET_MEAN).numpy()

            # Vectorized columnar accumulation (no per-sample loop)
            n = n_samples
            col_symbol.extend(data["symbols"])
            col_date.extend([date_str] * n)
            col_shard.extend([shard_num] * n)
            col_pred.extend(pred_bp.tolist())
            col_target.extend(data["target"].tolist())
            col_bid.extend(data["bid_p1"].tolist())
            col_ask.extend(data["ask_p1"].tolist())
            col_mvd.extend(data["macro_v_d"].tolist())

            samples_total = samples_written + len(col_symbol)

            # Progress logging every 50 shards
            if (shard_i + 1) % 50 == 0:
                elapsed = time.time() - t0
                processed = shard_i + 1 - start_shard
                rate = processed / elapsed * 3600
                eta_h = (len(all_shards) - shard_i - 1) / rate if rate > 0 else 0
                avg_sp = np.mean(z_sparsity_accum) if z_sparsity_accum else 0
                log.info(f"Shard {shard_i+1}/{len(all_shards)} | "
                         f"Samples: {samples_total:,} | "
                         f"Rate: {rate:.0f} shards/h | "
                         f"ETA: {eta_h:.1f}h | "
                         f"z_sparsity: {avg_sp:.3f}")

            # Checkpoint
            if (shard_i + 1) % args.checkpoint_interval == 0 and col_symbol:
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

    # Flush remaining
    if col_symbol:
        chunk_path = os.path.join(chunk_dir, f"chunk_{len(chunk_files):04d}.parquet")
        table = pa.table({
            "symbol": col_symbol, "date": col_date, "shard_idx": col_shard,
            "pred_bp": col_pred, "target_bp": col_target,
            "bid_p1": col_bid, "ask_p1": col_ask, "macro_v_d": col_mvd,
        })
        pq.write_table(table, chunk_path)
        chunk_files.append(chunk_path)
        samples_written += len(col_symbol)

    # Merge chunks
    log.info(f"Merging {len(chunk_files)} chunks ({samples_written:,} samples)...")
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    tables = [pq.read_table(cf) for cf in chunk_files]
    merged = pa.concat_tables(tables)
    pq.write_table(merged, args.output)

    avg_sparsity = np.mean(z_sparsity_accum) if z_sparsity_accum else 0
    elapsed = time.time() - t0
    log.info(f"Done: {samples_written:,} samples in {elapsed/3600:.1f}h")
    log.info(f"M3 z_core avg sparsity: {avg_sparsity:.4f} ({avg_sparsity*100:.1f}%)")
    log.info(f"Output: {args.output}")

    meta_path = args.output + ".meta.json"
    with open(meta_path, "w") as f:
        json.dump({
            "total_samples": samples_written,
            "z_core_sparsity_mean": avg_sparsity,
            "z_core_sparsity_pct": avg_sparsity * 100,
            "elapsed_hours": elapsed / 3600,
            "model": f"T29 hd={args.hidden_dim} wt={args.window_size_t}",
        }, f, indent=2)

    if os.path.exists(progress_path):
        os.remove(progress_path)


if __name__ == "__main__":
    main()
