"""
Phase 7 Step 1: Shard → Calendar Date Mapping
----------------------------------------------
Builds approximate mapping from shard index to trading date.

Math: 9.96M samples across 552 trading days.
Each parquet file = 1 trading date. Row count ∝ tick density ∝ sample density.
Cumulative row proportion → cumulative sample count → shard index.

Usage:
  python3 phase7_date_mapper.py \
    --parquet_dir /omega_pool/parquet_data/latest_base_l1/host=linux1/ \
    --total_samples 9960000 --total_shards 1992 \
    --output /omega_pool/phase7/shard_date_map.json
"""

import os
import json
import argparse
import logging
from collections import OrderedDict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

try:
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False


def get_row_count(fpath):
    """Get row count from parquet footer metadata (O(1), no data scan)."""
    if HAS_PYARROW:
        return pq.ParquetFile(fpath).metadata.num_rows
    # Fallback: estimate from file size (crude but works)
    return os.path.getsize(fpath)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet_dir", required=True)
    parser.add_argument("--total_samples", type=int, default=9960000)
    parser.add_argument("--total_shards", type=int, default=1992)
    parser.add_argument("--train_val_boundary", type=int, default=1594)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    # 1. Discover and sort parquet files by date (same as ETL line 579)
    all_files = []
    for root, _, files in os.walk(args.parquet_dir):
        for f in files:
            if f.endswith('.parquet'):
                all_files.append(os.path.join(root, f))
    all_files.sort(key=lambda p: os.path.basename(p)[:8])
    log.info(f"Found {len(all_files)} parquet files")

    if not all_files:
        log.error("No parquet files found!")
        return

    # 2. Read row counts (metadata only, O(1) per file)
    date_rows = OrderedDict()
    total_rows = 0
    for fpath in all_files:
        date_str = os.path.basename(fpath)[:8]
        rows = get_row_count(fpath)
        if date_str not in date_rows:
            date_rows[date_str] = 0
        date_rows[date_str] += rows
        total_rows += rows

    log.info(f"Dates: {len(date_rows)}, Total rows: {total_rows:,}")

    # 3. Proportional mapping: row fraction → sample fraction → shard index
    samples_per_shard = args.total_samples / args.total_shards  # 5000
    cumulative_rows = 0
    shard_to_date = {}
    date_to_shard_range = {}

    for date_str, row_count in date_rows.items():
        # Estimate samples for this date
        row_fraction = row_count / total_rows
        est_samples = row_fraction * args.total_samples

        shard_start = int(cumulative_rows / total_rows * args.total_shards)
        cumulative_rows += row_count
        shard_end = int(cumulative_rows / total_rows * args.total_shards) - 1
        shard_end = max(shard_end, shard_start)

        date_to_shard_range[date_str] = [shard_start, shard_end]
        for s in range(shard_start, shard_end + 1):
            shard_to_date[str(s)] = date_str

    # Fill any gaps (rounding)
    for s in range(args.total_shards):
        if str(s) not in shard_to_date:
            # Find nearest mapped shard
            for delta in range(1, 10):
                if str(s - delta) in shard_to_date:
                    shard_to_date[str(s)] = shard_to_date[str(s - delta)]
                    break

    # 4. Output
    result = {
        "shard_to_date": shard_to_date,
        "date_to_shard_range": date_to_shard_range,
        "total_shards": args.total_shards,
        "total_dates": len(date_rows),
        "total_parquet_rows": total_rows,
        "total_samples_estimated": args.total_samples,
        "train_val_boundary_shard": args.train_val_boundary,
        "dates_list": list(date_rows.keys()),
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    # Sanity checks
    dates = list(date_rows.keys())
    log.info(f"Date range: {dates[0]} → {dates[-1]}")
    log.info(f"Shards mapped: {len(shard_to_date)} / {args.total_shards}")
    log.info(f"Avg shards/day: {args.total_shards / len(date_rows):.1f}")
    log.info(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
