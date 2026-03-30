"""
Phase 7 Step 2: Full Inference (T29 Flagship, hd=64) — v14 Pipe Streaming
--------------------------------------------------------------------------
Run T29 model on ALL shards via WebDataset pipe: streaming from GCS.
No local staging, no GCS FUSE, direct network→memory→GPU.

Audit fixes applied:
  - Gemini: per-sample error handling, z_sparsity weighted accumulation
  - Codex: SIGTERM flag (not direct save), atomic checkpoint, streaming merge
  - GCS Best Practice: pipe:gcloud storage cat (bypass FUSE and staging)

Usage (Vertex AI):
  python3 phase7_inference.py \
    --checkpoint /gcs/.../best.pt \
    --shard_dir gs://omega-pure-data/wds_shards_v3_full \
    --date_map /gcs/.../shard_date_map.json \
    --output /gcs/.../predictions.parquet \
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

import torch
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

# SIGTERM: set flag, save at shard boundary (no async save)
_stop_requested = False

def _sigterm_handler(signum, frame):
    global _stop_requested
    log.warning("SIGTERM received — will save checkpoint at next shard boundary")
    _stop_requested = True

signal.signal(signal.SIGTERM, _sigterm_handler)

TARGET_MEAN = -5.08
TARGET_STD = 216.24

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gcp'))

from omega_epiplexity_plus_core import OmegaMathematicalCompressor

_KEY_RE = re.compile(r'^(.+)_(\d{9})$')


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


def load_shard(shard_path, macro_window):
    """Load all samples from a single shard. Returns None on empty/corrupt."""
    import webdataset as wds

    dataset = (
        wds.WebDataset([shard_path], resampled=False, handler=wds.warn_and_continue)
        .decode(handler=wds.warn_and_continue)
    )

    manifolds = []
    c_frictions = []
    targets = []
    symbols = []
    skipped = 0

    for sample in dataset:
        try:
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
        except Exception as e:
            skipped += 1
            if skipped <= 3:
                log.warning(f"Skipped sample in {shard_path}: {e}")

    if not manifolds:
        return None

    manifold_np = np.stack(manifolds)
    c_np = np.array(c_frictions, dtype=np.float32)
    t_np = np.array(targets, dtype=np.float32)

    last_bars = manifold_np[:, -1, 0, :]
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


def save_checkpoint(progress_path, chunk_dir, chunk_files, col_symbol, col_date,
                    col_shard, col_pred, col_target, col_bid, col_ask, col_mvd,
                    samples_written, shard_i, z_sparse_count, z_total_count):
    """Atomic checkpoint: flush columns to chunk, then update progress."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    sw = samples_written
    if col_symbol:
        chunk_path = os.path.join(chunk_dir, f"chunk_{len(chunk_files):04d}.parquet")
        table = pa.table({
            "symbol": col_symbol, "date": col_date, "shard_idx": col_shard,
            "pred_bp": col_pred, "target_bp": col_target,
            "bid_p1": col_bid, "ask_p1": col_ask, "macro_v_d": col_mvd,
        })
        pq.write_table(table, chunk_path)
        chunk_files.append(chunk_path)
        sw += len(col_symbol)

    # Write to /tmp first (local fs, atomic), then copy to target (may be GCS FUSE)
    import shutil
    local_tmp = f"/tmp/progress_{os.getpid()}.pkl"
    with open(local_tmp, "wb") as f:
        pickle.dump({
            "next_shard": shard_i + 1,
            "z_sparse_count": z_sparse_count,
            "z_total_count": z_total_count,
            "chunk_files": chunk_files,
            "samples_written": sw,
        }, f, protocol=4)
    shutil.copy2(local_tmp, progress_path)
    os.remove(local_tmp)
    return sw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--shard_dir", required=True,
                        help="GCS URI (gs://...) or local path")
    parser.add_argument("--date_map", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch_size", type=int, default=512)
    parser.add_argument("--hidden_dim", type=int, default=64)
    parser.add_argument("--window_size_t", type=int, default=32)
    parser.add_argument("--window_size_s", type=int, default=10)
    parser.add_argument("--macro_window", type=int, default=160)
    parser.add_argument("--checkpoint_interval", type=int, default=100)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--prefetch", type=int, default=4)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(16)
    log.info(f"Device: {device}, prefetch: {args.prefetch}")

    with open(args.date_map) as f:
        date_map = json.load(f)
    shard_to_date = date_map["shard_to_date"]
    log.info(f"Date map: {date_map['total_dates']} dates, {date_map['total_shards']} shards")

    model = OmegaTIBInference(
        hidden_dim=args.hidden_dim,
        window_size=(args.window_size_t, args.window_size_s),
    ).to(device)

    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    state = {k: v for k, v in ckpt["model_state_dict"].items() if not k.startswith("masking.")}
    model.load_state_dict(state, strict=False)
    model.eval()
    log.info(f"Model loaded: hd={args.hidden_dim}, wt={args.window_size_t}")

    # Discover shards — support both GCS URI and local path
    shard_dir = args.shard_dir
    if shard_dir.startswith("gs://"):
        # Use pipe: streaming for GCS
        import subprocess
        result = subprocess.run(
            ["gcloud", "storage", "ls", f"{shard_dir}/omega_shard_*.tar"],
            capture_output=True, text=True, timeout=300
        )
        all_shard_uris = sorted([l.strip() for l in result.stdout.strip().split('\n')
                                  if l.strip().startswith("gs://")])
        log.info(f"Total shards (GCS): {len(all_shard_uris)}")
        use_pipe = True
    else:
        # Local or FUSE path
        all_shard_uris = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
        log.info(f"Total shards (local): {len(all_shard_uris)}")
        use_pipe = False

    import pyarrow as pa
    import pyarrow.parquet as pq
    from concurrent.futures import ThreadPoolExecutor

    col_symbol, col_date, col_shard = [], [], []
    col_pred, col_target = [], []
    col_bid, col_ask, col_mvd = [], [], []
    chunk_files = []
    chunk_dir = args.output + ".chunks"
    os.makedirs(chunk_dir, exist_ok=True)

    progress_path = args.output + ".progress.pkl"
    start_shard = 0
    z_sparse_count = 0
    z_total_count = 0
    samples_written = 0

    if args.resume and os.path.exists(progress_path):
        with open(progress_path, "rb") as f:
            saved = pickle.load(f)
        start_shard = saved["next_shard"]
        z_sparse_count = saved.get("z_sparse_count", 0)
        z_total_count = saved.get("z_total_count", 0)
        chunk_files = saved.get("chunk_files", [])
        samples_written = saved.get("samples_written", 0)
        log.info(f"Resumed from shard {start_shard}, {samples_written:,} samples in {len(chunk_files)} chunks")

    t0 = time.time()
    samples_total = samples_written

    # Build shard processing list
    shards_to_process = []
    for i, uri in enumerate(all_shard_uris):
        if i < start_shard:
            continue
        shard_num = int(os.path.basename(uri).split("_")[-1].split(".")[0])
        date_str = shard_to_date.get(str(shard_num), "unknown")
        # For pipe mode, convert gs:// URI to pipe: command
        if use_pipe:
            shard_path = f"pipe:gcloud storage cat {uri}"
        else:
            shard_path = uri
        shards_to_process.append((i, shard_path, shard_num, date_str))

    log.info(f"Shards to process: {len(shards_to_process)} (starting from {start_shard})")

    # Main loop with prefetch
    with ThreadPoolExecutor(max_workers=args.prefetch) as executor:
        futures = {}
        for idx in range(min(args.prefetch, len(shards_to_process))):
            si, sp, sn, ds = shards_to_process[idx]
            futures[idx] = executor.submit(load_shard, sp, args.macro_window)

        next_submit = args.prefetch

        for queue_idx, (shard_i, shard_path, shard_num, date_str) in enumerate(shards_to_process):
            # Check SIGTERM flag at shard boundary
            if _stop_requested:
                log.warning(f"SIGTERM: saving checkpoint at shard {shard_i}")
                samples_written = save_checkpoint(
                    progress_path, chunk_dir, chunk_files,
                    col_symbol, col_date, col_shard, col_pred, col_target,
                    col_bid, col_ask, col_mvd,
                    samples_written, shard_i - 1, z_sparse_count, z_total_count
                )
                log.info(f"Checkpoint saved: {samples_written:,} samples, shard {shard_i}")
                sys.exit(0)

            # Wait for prefetched data
            data = futures[queue_idx].result()
            del futures[queue_idx]

            # Submit next prefetch
            if next_submit < len(shards_to_process):
                nsi, nsp, nsn, nds = shards_to_process[next_submit]
                futures[next_submit] = executor.submit(load_shard, nsp, args.macro_window)
                next_submit += 1

            if data is None:
                continue

            n_samples = len(data["manifold"])
            manifold_all = torch.from_numpy(data["manifold"]).float().to(device)
            c_all = torch.from_numpy(data["c_friction"]).float().unsqueeze(-1).to(device)

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
                        z_sparse_count += int((model._z_core.abs() < 0.01).sum().item())
                        z_total_count += model._z_core.numel()

            preds = torch.cat(pred_parts)
            pred_bp = (preds.view(-1) * TARGET_STD + TARGET_MEAN).numpy()

            col_symbol.extend(data["symbols"])
            col_date.extend([date_str] * n_samples)
            col_shard.extend([shard_num] * n_samples)
            col_pred.extend(pred_bp.tolist())
            col_target.extend(data["target"].tolist())
            col_bid.extend(data["bid_p1"].tolist())
            col_ask.extend(data["ask_p1"].tolist())
            col_mvd.extend(data["macro_v_d"].tolist())

            samples_total = samples_written + len(col_symbol)

            if (shard_i + 1) % 50 == 0:
                elapsed = time.time() - t0
                processed = shard_i + 1 - start_shard
                rate = processed / elapsed * 3600
                eta_h = (len(all_shard_uris) - shard_i - 1) / rate if rate > 0 else 0
                avg_sp = z_sparse_count / z_total_count if z_total_count > 0 else 0
                log.info(f"Shard {shard_i+1}/{len(all_shard_uris)} | "
                         f"Samples: {samples_total:,} | "
                         f"Rate: {rate:.0f} shards/h | "
                         f"ETA: {eta_h:.1f}h | "
                         f"z_sparsity: {avg_sp:.3f}")

            # Checkpoint at interval
            if (shard_i + 1) % args.checkpoint_interval == 0 and col_symbol:
                samples_written = save_checkpoint(
                    progress_path, chunk_dir, chunk_files,
                    col_symbol, col_date, col_shard, col_pred, col_target,
                    col_bid, col_ask, col_mvd,
                    samples_written, shard_i, z_sparse_count, z_total_count
                )
                col_symbol, col_date, col_shard = [], [], []
                col_pred, col_target = [], []
                col_bid, col_ask, col_mvd = [], [], []
                log.info(f"Chunk {len(chunk_files)} saved ({samples_written:,} samples total)")

    # Flush remaining
    if col_symbol:
        samples_written = save_checkpoint(
            progress_path, chunk_dir, chunk_files,
            col_symbol, col_date, col_shard, col_pred, col_target,
            col_bid, col_ask, col_mvd,
            samples_written, len(all_shard_uris) - 1, z_sparse_count, z_total_count
        )

    # Streaming merge (not all-in-memory)
    log.info(f"Merging {len(chunk_files)} chunks ({samples_written:,} samples)...")
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    writer = None
    for cf in chunk_files:
        t = pq.read_table(cf)
        if writer is None:
            writer = pq.ParquetWriter(args.output, t.schema)
        writer.write_table(t)
        del t
    if writer:
        writer.close()

    avg_sparsity = z_sparse_count / z_total_count if z_total_count > 0 else 0
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
