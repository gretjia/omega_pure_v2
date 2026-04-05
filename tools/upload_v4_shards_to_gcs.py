"""
ETL v4 Shard Upload + Quality Check
------------------------------------
1. Merge worker shards into single sequence
2. Quality checks (date field, tensor shape, file count, size)
3. Upload to GCS via Mac Studio proxy (192.168.3.93:7897)
4. Verify uploaded files match local

Usage (on windows1):
  set PYTHONUNBUFFERED=1
  C:\Python314\python.exe -u tools\upload_v4_shards_to_gcs.py ^
    --shard_dir D:\Omega_frames\wds_shards_v4 ^
    --gcs_bucket omega-pure-data ^
    --gcs_prefix wds_shards_v4 ^
    --workers 8
"""

import os
import sys
import json
import glob
import time
import tarfile
import shutil
import hashlib
import argparse
import logging
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============================================================
# Phase 1: Merge worker shards
# ============================================================

def merge_worker_shards(shard_dir, num_workers):
    """Merge worker_NN/ subdirs into single numbered sequence.
    R-022 (C-075): validates ALL workers completed before merging.
    """
    import pickle

    # ===== R-022 GATE: verify all workers completed =====
    incomplete = []
    for w in range(num_workers):
        worker_dir = os.path.join(shard_dir, f"worker_{w:02d}")
        ckpt_path = os.path.join(worker_dir, "_checkpoint.pkl")
        if not os.path.exists(worker_dir):
            incomplete.append(f"worker_{w:02d}: directory missing")
            continue
        if not os.path.exists(ckpt_path):
            incomplete.append(f"worker_{w:02d}: no checkpoint")
            continue
        with open(ckpt_path, 'rb') as f:
            ckpt = pickle.load(f)
        if ckpt.get('file_idx', -1) < 1:
            incomplete.append(f"worker_{w:02d}: file_idx={ckpt.get('file_idx')}")

    if incomplete:
        logging.error(f"[MERGE] R-022 GATE FAILED — {len(incomplete)} workers incomplete:")
        for msg in incomplete:
            logging.error(f"  ✗ {msg}")
        logging.error("[MERGE] Aborting merge to preserve checkpoint resume capability (C-075)")
        return -1

    logging.info(f"[MERGE] R-022 gate PASSED: all {num_workers} workers have checkpoints")

    # ===== Collect shards =====
    merged = []
    for w in range(num_workers):
        worker_dir = os.path.join(shard_dir, f"worker_{w:02d}")
        worker_shards = sorted(glob.glob(os.path.join(worker_dir, "omega_shard_*.tar")))
        merged.extend(worker_shards)
        logging.info(f"  Worker {w:02d}: {len(worker_shards)} shards")

    logging.info(f"Total shards from {num_workers} workers: {len(merged)}")

    # ===== Renumber into root dir (copy first, delete after — C-075 reversibility) =====
    for idx, src in enumerate(merged):
        dst = os.path.join(shard_dir, f"omega_shard_{idx:05d}.tar")
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)

    # Verify copies before deleting originals
    for idx, src in enumerate(merged):
        dst = os.path.join(shard_dir, f"omega_shard_{idx:05d}.tar")
        if os.path.getsize(dst) != os.path.getsize(src):
            logging.error(f"[MERGE] Size mismatch: {src} vs {dst}, aborting cleanup")
            return len(merged)

    # Now safe to delete originals
    for src in merged:
        os.remove(src)

    # Remove worker dirs
    for w in range(num_workers):
        worker_dir = os.path.join(shard_dir, f"worker_{w:02d}")
        try:
            for f in glob.glob(os.path.join(worker_dir, "_checkpoint*")):
                os.remove(f)
            os.rmdir(worker_dir)
        except OSError:
            pass

    logging.info(f"[MERGE] {len(merged)} shards merged and renumbered")
    return len(merged)


# ============================================================
# Phase 2: Quality Checks
# ============================================================

def quality_check(shard_dir, expected_min_shards=100):
    """Comprehensive quality check on v4 shards."""
    shards = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
    logging.info(f"\n{'='*60}")
    logging.info(f" QUALITY CHECK — {len(shards)} shards")
    logging.info(f"{'='*60}")

    errors = []
    warnings = []

    # --- Check 1: Shard count ---
    if len(shards) < expected_min_shards:
        errors.append(f"Shard count {len(shards)} < expected minimum {expected_min_shards}")
    logging.info(f"[CHECK 1] Shard count: {len(shards)}")

    # --- Check 2: Total size ---
    total_bytes = sum(os.path.getsize(s) for s in shards)
    total_gb = total_bytes / (1024**3)
    logging.info(f"[CHECK 2] Total size: {total_gb:.1f} GB ({total_bytes:,} bytes)")
    if total_gb < 10:
        warnings.append(f"Total size {total_gb:.1f} GB seems small")

    # --- Check 3: Per-shard size distribution ---
    sizes = [os.path.getsize(s) / (1024**2) for s in shards]
    avg_mb = sum(sizes) / len(sizes)
    min_mb = min(sizes)
    max_mb = max(sizes)
    logging.info(f"[CHECK 3] Shard sizes: avg={avg_mb:.0f}MB, min={min_mb:.0f}MB, max={max_mb:.0f}MB")
    empty_shards = [s for s, sz in zip(shards, sizes) if sz < 1]
    if empty_shards:
        errors.append(f"{len(empty_shards)} empty/tiny shards: {empty_shards[:3]}")

    # --- Check 4: Sample deep inspection (3 shards) ---
    inspect_indices = [0, len(shards)//2, len(shards)-1]
    total_samples = 0
    dates_seen = set()
    symbols_seen = set()

    for shard_idx in inspect_indices:
        shard_path = shards[shard_idx]
        shard_name = os.path.basename(shard_path)
        try:
            with tarfile.open(shard_path, 'r') as tf:
                members = tf.getnames()
                json_members = [m for m in members if m.endswith('.json')]
                npy_members = [m for m in members if m.endswith('manifold_2d.npy')]

                # Count samples in this shard
                shard_samples = len(json_members)
                total_samples += shard_samples

                # Check first few samples
                checked = 0
                for jm in json_members[:5]:
                    meta = json.loads(tf.extractfile(jm).read())

                    # 4a: date field exists
                    if 'date' not in meta:
                        errors.append(f"{shard_name}: meta.json missing 'date' field")
                        break
                    if meta['date'] in ('None', '', None):
                        errors.append(f"{shard_name}: date is None/empty")
                        break

                    dates_seen.add(meta['date'])
                    symbols_seen.add(meta.get('symbol', ''))
                    checked += 1

                # 4b: Check tensor shape from first manifold
                if npy_members:
                    import io
                    npy_data = tf.extractfile(npy_members[0]).read()
                    arr = np.load(io.BytesIO(npy_data))
                    if arr.shape != (160, 10, 10):
                        errors.append(f"{shard_name}: tensor shape {arr.shape} != (160, 10, 10)")
                    else:
                        # NaN/Inf check
                        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
                            errors.append(f"{shard_name}: tensor contains NaN/Inf")

                logging.info(
                    f"[CHECK 4] {shard_name}: {shard_samples} samples, "
                    f"{checked} meta checked OK"
                )
        except Exception as e:
            errors.append(f"{shard_name}: failed to open — {e}")

    logging.info(f"[CHECK 4] Dates sampled: {len(dates_seen)} unique, range: "
                 f"{min(dates_seen) if dates_seen else '?'} ~ {max(dates_seen) if dates_seen else '?'}")
    logging.info(f"[CHECK 4] Symbols sampled: {len(symbols_seen)} unique")

    # --- Check 5: Estimate total sample count ---
    # Average samples per inspected shard × total shards
    avg_per_shard = total_samples / len(inspect_indices)
    est_total = int(avg_per_shard * len(shards))
    logging.info(f"[CHECK 5] Estimated total samples: ~{est_total:,} "
                 f"(based on {len(inspect_indices)} inspected shards)")

    # --- Summary ---
    logging.info(f"\n{'='*60}")
    if errors:
        logging.error(f" QUALITY CHECK FAILED — {len(errors)} errors:")
        for e in errors:
            logging.error(f"   ✗ {e}")
        return False
    else:
        if warnings:
            for w in warnings:
                logging.warning(f"   ⚠ {w}")
        logging.info(f" QUALITY CHECK PASSED")
        logging.info(f"   Shards: {len(shards)}")
        logging.info(f"   Size: {total_gb:.1f} GB")
        logging.info(f"   Est. samples: ~{est_total:,}")
        logging.info(f"   Date range: {min(dates_seen)} ~ {max(dates_seen)}")
        logging.info(f"   Tensor shape: (160, 10, 10) verified")
        logging.info(f"   Date field: present in all checked samples")
        logging.info(f"{'='*60}")
        return True


# ============================================================
# Phase 3: Upload to GCS
# ============================================================

def upload_to_gcs(shard_dir, bucket_name, gcs_prefix, project_id="gen-lang-client-0250995579"):
    """Upload all shards to GCS via Mac Studio proxy."""
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\tmp\gcs_creds.json'
    os.environ['https_proxy'] = 'http://192.168.3.93:7897'
    os.environ['http_proxy'] = 'http://192.168.3.93:7897'

    from google.cloud import storage
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)

    shards = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
    logging.info(f"\n[UPLOAD] {len(shards)} shards → gs://{bucket_name}/{gcs_prefix}/")

    uploaded = 0
    failed = []
    start = time.time()

    for i, shard_path in enumerate(shards):
        fname = os.path.basename(shard_path)
        blob_name = f"{gcs_prefix}/{fname}"
        local_size = os.path.getsize(shard_path)

        try:
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(shard_path, timeout=600)

            # Verify size
            blob.reload()
            if blob.size != local_size:
                failed.append(f"{fname}: size mismatch local={local_size} gcs={blob.size}")
                logging.error(f"  ✗ {fname}: SIZE MISMATCH")
            else:
                uploaded += 1

            if (i + 1) % 10 == 0 or i == 0:
                elapsed = time.time() - start
                rate_mbps = (sum(os.path.getsize(shards[j]) for j in range(i+1)) / (1024**2)) / elapsed
                eta_min = ((len(shards) - i - 1) / (i + 1)) * elapsed / 60
                logging.info(
                    f"  [{i+1}/{len(shards)}] {fname} ({local_size/(1024**2):.0f}MB) "
                    f"| {rate_mbps:.1f} MB/s | ETA: {eta_min:.0f}min"
                )
        except Exception as e:
            failed.append(f"{fname}: {e}")
            logging.error(f"  ✗ {fname}: {e}")

    elapsed = time.time() - start
    logging.info(f"\n[UPLOAD] Done: {uploaded}/{len(shards)} uploaded in {elapsed/60:.1f}min")

    if failed:
        logging.error(f"[UPLOAD] {len(failed)} FAILURES:")
        for f in failed:
            logging.error(f"  ✗ {f}")
        return False
    return True


# ============================================================
# Phase 4: GCS Verification
# ============================================================

def verify_gcs(shard_dir, bucket_name, gcs_prefix, project_id="gen-lang-client-0250995579"):
    """Verify GCS files match local."""
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'C:\tmp\gcs_creds.json'
    os.environ['https_proxy'] = 'http://192.168.3.93:7897'
    os.environ['http_proxy'] = 'http://192.168.3.93:7897'

    from google.cloud import storage
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)

    local_shards = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
    local_map = {os.path.basename(s): os.path.getsize(s) for s in local_shards}

    gcs_blobs = list(bucket.list_blobs(prefix=f"{gcs_prefix}/omega_shard_"))
    gcs_map = {os.path.basename(b.name): b.size for b in gcs_blobs}

    logging.info(f"\n[VERIFY] Local: {len(local_map)} shards, GCS: {len(gcs_map)} blobs")

    mismatches = []
    missing = []

    for fname, local_sz in local_map.items():
        if fname not in gcs_map:
            missing.append(fname)
        elif gcs_map[fname] != local_sz:
            mismatches.append(f"{fname}: local={local_sz} gcs={gcs_map[fname]}")

    if missing:
        logging.error(f"[VERIFY] {len(missing)} missing on GCS: {missing[:5]}")
    if mismatches:
        logging.error(f"[VERIFY] {len(mismatches)} size mismatches: {mismatches[:5]}")

    if not missing and not mismatches:
        logging.info(f"[VERIFY] ALL {len(local_map)} shards verified on GCS")
        return True
    return False


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL v4 Upload + QC")
    parser.add_argument("--shard_dir", required=True)
    parser.add_argument("--gcs_bucket", default="omega-pure-data")
    parser.add_argument("--gcs_prefix", default="wds_shards_v4")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--skip_merge", action="store_true")
    parser.add_argument("--skip_upload", action="store_true")
    parser.add_argument("--qc_only", action="store_true")
    args = parser.parse_args()

    logging.info("=" * 60)
    logging.info(" ETL v4 POST-PROCESSING PIPELINE")
    logging.info("=" * 60)

    # Phase 1: Merge
    if not args.skip_merge and not args.qc_only:
        logging.info("\n[PHASE 1] Merging worker shards...")
        n_shards = merge_worker_shards(args.shard_dir, args.workers)
    else:
        n_shards = len(glob.glob(os.path.join(args.shard_dir, "omega_shard_*.tar")))
        logging.info(f"\n[PHASE 1] Skip merge, {n_shards} shards found")

    # Phase 2: Quality Check
    logging.info("\n[PHASE 2] Running quality checks...")
    qc_pass = quality_check(args.shard_dir)
    if not qc_pass:
        logging.error("QUALITY CHECK FAILED — aborting upload")
        sys.exit(1)

    if args.qc_only:
        logging.info("QC-only mode, stopping here.")
        sys.exit(0)

    # Phase 3: Upload
    if not args.skip_upload:
        logging.info("\n[PHASE 3] Uploading to GCS...")
        upload_ok = upload_to_gcs(args.shard_dir, args.gcs_bucket, args.gcs_prefix)
        if not upload_ok:
            logging.error("UPLOAD FAILED")
            sys.exit(1)

        # Phase 4: Verify
        logging.info("\n[PHASE 4] Verifying GCS upload...")
        verify_ok = verify_gcs(args.shard_dir, args.gcs_bucket, args.gcs_prefix)
        if not verify_ok:
            logging.error("VERIFICATION FAILED")
            sys.exit(1)

    logging.info("\n" + "=" * 60)
    logging.info(" ALL PHASES COMPLETE — ETL v4 shards on GCS")
    logging.info("=" * 60)
