"""
Parquet Pre-Sort by Symbol — DuckDB External Sort Edition
---------------------------------------------------------
Sorts each date-organized parquet file by 'symbol' column using DuckDB's
out-of-core external merge sort. Produces parquet with tight row group
min/max statistics for PyArrow Scanner predicate pushdown.

DuckDB handles larger-than-memory files via automatic disk spill.

Cost: ~170s/file × 743 files ≈ 35h (one-time, with checkpoint resume)
Benefit: ETL multi-worker goes from N× full scan to ~1× total I/O (permanent)

Usage:
  python tools/sort_parquet_by_symbol.py \
    --input_dir /path/to/raw_parquet \
    --output_dir /path/to/sorted \
    --memory_limit 40GB

  # Resume after interruption (skips already-sorted files):
  python tools/sort_parquet_by_symbol.py \
    --input_dir /path/to/raw_parquet \
    --output_dir /path/to/sorted \
    --memory_limit 40GB
"""

import os
import sys
import time
import glob
import json
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

try:
    import duckdb
except ImportError:
    logging.error("duckdb not installed. Run: pip install duckdb")
    sys.exit(1)

try:
    import pyarrow.parquet as pq
except ImportError:
    pq = None


def sort_single_file(input_path: str, output_path: str,
                     memory_limit: str = '40GB',
                     threads: int = 8,
                     temp_dir: str = '/tmp/duckdb_sort_tmp',
                     row_group_size: int = 100_000) -> dict:
    """Sort a single parquet file by symbol using DuckDB external sort.

    Atomic write: writes to .tmp then renames, so interrupted sorts
    never leave corrupt output files.

    Returns dict with stats: {rows, input_mb, output_mb, seconds}.
    """
    t0 = time.time()
    input_mb = os.path.getsize(input_path) / (1024 ** 2)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    tmp_path = output_path + ".tmp"

    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{memory_limit}'")
    con.execute(f"SET threads = {threads}")
    con.execute(f"SET temp_directory = '{temp_dir}'")

    # Escape single quotes in paths (Windows backslash paths are OK for DuckDB)
    in_escaped = input_path.replace("'", "''")
    out_escaped = tmp_path.replace("'", "''")

    con.execute(f"""
        COPY (
            SELECT * FROM read_parquet('{in_escaped}')
            ORDER BY symbol
        ) TO '{out_escaped}'
        (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE {row_group_size})
    """)
    con.close()

    # Atomic rename
    os.replace(tmp_path, output_path)

    output_mb = os.path.getsize(output_path) / (1024 ** 2)
    elapsed = time.time() - t0

    # Read row count from output metadata (cheap)
    n_rows = 0
    if pq:
        try:
            n_rows = pq.ParquetFile(output_path).metadata.num_rows
        except Exception:
            pass

    return {
        'rows': n_rows,
        'input_mb': input_mb,
        'output_mb': output_mb,
        'seconds': elapsed,
    }


def verify_sorted(output_path: str) -> bool:
    """Verify row groups have sorted, non-overlapping symbol ranges."""
    if pq is None:
        logging.warning("[VERIFY] pyarrow not available, skipping verification")
        return True

    pf = pq.ParquetFile(output_path)
    metadata = pf.metadata

    symbol_col_idx = None
    for i in range(metadata.row_group(0).num_columns):
        if metadata.row_group(0).column(i).path_in_schema == 'symbol':
            symbol_col_idx = i
            break

    if symbol_col_idx is None:
        logging.error(f"[VERIFY] No 'symbol' column found in {output_path}")
        return False

    n_groups = metadata.num_row_groups
    if n_groups < 2:
        return True

    # Verify row groups are sorted: each group's min >= prev group's min
    prev_min = None
    overlaps = 0
    for rg_idx in range(n_groups):
        stats = metadata.row_group(rg_idx).column(symbol_col_idx).statistics
        if stats is None or not stats.has_min_max:
            logging.warning(f"[VERIFY] Row group {rg_idx} missing statistics")
            continue
        rg_min = stats.min
        if prev_min is not None and rg_min < prev_min:
            overlaps += 1
        prev_min = rg_min

    if overlaps > 0:
        logging.error(f"[VERIFY] {output_path}: {overlaps} out-of-order row groups!")
        return False

    logging.info(f"[VERIFY] {output_path}: {n_groups} row groups, sorted OK")
    return True


def run_sort_pipeline(input_dir: str = None, output_dir: str = None,
                      file_list_path: str = None,
                      memory_limit: str = '40GB',
                      threads: int = 8,
                      row_group_size: int = 100_000):
    """Sort all parquet files with DuckDB. Resume-safe (skips existing)."""

    # Gather file list
    if file_list_path and os.path.exists(file_list_path):
        with open(file_list_path) as f:
            all_files = [line.strip() for line in f if line.strip()]
        logging.info(f"[SORT] Using file list: {file_list_path} ({len(all_files)} files)")
    elif input_dir:
        all_files = []
        for root, dirs, files in os.walk(input_dir):
            for fname in files:
                if fname.endswith('.parquet'):
                    all_files.append(os.path.join(root, fname))
        all_files.sort(key=lambda p: os.path.basename(p)[:8])
        logging.info(f"[SORT] Scanning {input_dir}: {len(all_files)} parquet files")
    else:
        logging.error("[SORT] Must specify --input_dir or --file_list")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    temp_dir = os.path.join(output_dir, '_duckdb_tmp')
    total_start = time.time()
    skipped = 0
    processed = 0
    failed = 0
    total_files = len(all_files)

    # Progress state file for monitoring
    progress_path = os.path.join(output_dir, '_sort_progress.json')

    for idx, fpath in enumerate(all_files):
        # Preserve relative subdirectory structure
        if input_dir:
            rel_path = os.path.relpath(fpath, input_dir)
        else:
            rel_path = os.path.basename(fpath)
        out_path = os.path.join(output_dir, rel_path)
        fname = os.path.basename(fpath)

        # Resume: skip already-sorted files (atomic write guarantees completeness)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            skipped += 1
            if skipped <= 3 or skipped % 100 == 0:
                logging.info(f"[SORT] Skip (exists): {fname}")
            continue

        # Clean up any leftover .tmp from previous interrupted run
        tmp_path = out_path + ".tmp"
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        try:
            stats = sort_single_file(fpath, out_path,
                                     memory_limit=memory_limit,
                                     threads=threads,
                                     temp_dir=temp_dir,
                                     row_group_size=row_group_size)
            processed += 1

            total_done = skipped + processed
            total_elapsed = time.time() - total_start
            avg_per_file = total_elapsed / max(processed, 1)
            remaining = total_files - total_done
            eta_h = (avg_per_file * remaining) / 3600

            if processed <= 3 or processed % 10 == 0:
                logging.info(
                    f"[SORT] {total_done}/{total_files} | {fname} | "
                    f"{stats['rows']/1e6:.1f}M rows | "
                    f"{stats['input_mb']:.0f}→{stats['output_mb']:.0f}MB | "
                    f"{stats['seconds']:.1f}s | ETA: {eta_h:.1f}h"
                )

            # Write progress for external monitoring
            if processed % 5 == 0:
                with open(progress_path, 'w') as pf:
                    json.dump({
                        'total_files': total_files,
                        'processed': processed,
                        'skipped': skipped,
                        'failed': failed,
                        'current_file': fname,
                        'avg_seconds_per_file': round(avg_per_file, 1),
                        'eta_hours': round(eta_h, 1),
                        'elapsed_hours': round(total_elapsed / 3600, 1),
                    }, pf)

        except Exception as e:
            failed += 1
            logging.error(f"[SORT] FAILED {fname}: {e}")
            # Remove partial output
            for p in [out_path, out_path + ".tmp"]:
                if os.path.exists(p):
                    os.remove(p)

    total_time = time.time() - total_start

    # Clean up DuckDB temp dir
    if os.path.exists(temp_dir):
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    logging.info(
        f"\n[SORT] Done. {processed} sorted, {skipped} skipped, {failed} failed | "
        f"{total_time/3600:.1f}h total"
    )

    if failed > 0:
        logging.error(f"[SORT] {failed} files failed — re-run to retry (resume-safe)")
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sort parquet files by symbol (DuckDB external sort)"
    )
    parser.add_argument("--input_dir", type=str,
                        help="Directory containing raw parquet files")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="Output directory for sorted parquet files")
    parser.add_argument("--file_list", type=str, default=None,
                        help="Text file with parquet paths (for split execution)")
    parser.add_argument("--memory_limit", type=str, default='40GB',
                        help="DuckDB memory limit (default 40GB)")
    parser.add_argument("--threads", type=int, default=8,
                        help="DuckDB threads (default 8)")
    parser.add_argument("--row_group_size", type=int, default=100_000,
                        help="Row group size (default 100000)")
    parser.add_argument("--verify_only", action="store_true",
                        help="Only verify existing sorted files")
    args = parser.parse_args()

    if args.verify_only:
        if pq is None:
            logging.error("pyarrow required for --verify_only")
            sys.exit(1)
        files = glob.glob(os.path.join(args.output_dir, "**/*.parquet"), recursive=True)
        ok = all(verify_sorted(f) for f in sorted(files))
        sys.exit(0 if ok else 1)

    run_sort_pipeline(args.input_dir, args.output_dir,
                      args.file_list, args.memory_limit,
                      args.threads, args.row_group_size)
