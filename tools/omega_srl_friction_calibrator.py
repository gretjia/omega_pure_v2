"""
OMEGA SRL Friction Calibrator (Phase 0.6 — Multiprocessing)
------------------------------------------------------------
Per-stock c_i via OLS without intercept on directional runs.
Embarrassingly parallel at file level: each worker processes independent trading days.

OOM Risk Audit:
  - Per worker: O(num_symbols × 2 floats) ≈ 80KB + PyArrow batch ~80MB = ~80MB
  - 12 workers peak: ~960MB / 128GB RAM = 0.8% → no OOM risk
  - No shared memory, no gc.collect(), OMP=1 per worker

Spec Alignment:
  - OLS c_i = sum_xy / sum_xx (addition is commutative → multiprocessing safe)
  - Physical bounds [0.05, 10.0], fallback to global median
  - Output: a_share_c_registry.json
"""

import os
import sys
import json
import time
import numpy as np
import pyarrow.parquet as pq
import logging
from multiprocessing import Pool

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(process)d] %(levelname)s - %(message)s')

MIN_DAILY_VOLUME = 1000.0
MAX_Q_RATIO = 0.1
C_LOWER_BOUND = 0.05
C_UPPER_BOUND = 10.0


def _process_single_file(fpath: str) -> dict:
    """Process one parquet file (one trading day). Returns per-symbol OLS contributions.

    Returns: {symbol: (norm_xy, norm_xx, count), ...}
    Memory: O(num_symbols_in_file × 3 floats) ≈ trivial
    """
    try:
        parquet_file = pq.ParquetFile(fpath)
    except Exception as e:
        return {}

    daily_stats = {}
    run_state = {}
    file_raw_sqrt_q_dp = {}
    file_raw_q = {}
    file_run_count = {}

    for batch in parquet_file.iter_batches(batch_size=200000):
        n = batch.num_rows
        sym_col = batch.column('symbol')
        price_col = batch.column('price')
        vol_col = batch.column('vol_tick')
        bs_col = batch.column('bs_flag')

        for i in range(n):
            symbol = sym_col[i].as_py()
            if not symbol:
                continue
            price = price_col[i].as_py() or 0.0
            vol = vol_col[i].as_py() or 0.0
            bs = bs_col[i].as_py()

            if price <= 0 or vol <= 0:
                continue

            if symbol not in daily_stats:
                daily_stats[symbol] = {'vol': 0.0, 'high': price, 'low': price}
            ds = daily_stats[symbol]
            ds['vol'] += vol
            if price > ds['high']:
                ds['high'] = price
            if price < ds['low']:
                ds['low'] = price

            if symbol not in run_state:
                run_state[symbol] = {'bs': bs, 'vol': vol, 'first_p': price, 'last_p': price}
                continue

            rs = run_state[symbol]
            if bs == rs['bs']:
                rs['vol'] += vol
                rs['last_p'] = price
            else:
                _fold_run(symbol, rs, file_raw_sqrt_q_dp, file_raw_q, file_run_count)
                rs['bs'] = bs
                rs['vol'] = vol
                rs['first_p'] = price
                rs['last_p'] = price

    # Flush final runs
    for symbol, rs in run_state.items():
        _fold_run(symbol, rs, file_raw_sqrt_q_dp, file_raw_q, file_run_count)

    # Normalize with daily V_D and σ_D, return per-symbol contributions
    result = {}
    for symbol in file_raw_sqrt_q_dp:
        if symbol not in daily_stats:
            continue
        ds = daily_stats[symbol]
        v_d = ds['vol']
        sigma_d = ds['high'] - ds['low']

        if v_d < MIN_DAILY_VOLUME or sigma_d < 1e-6:
            continue

        sqrt_v_d = np.sqrt(v_d)
        norm_xy = file_raw_sqrt_q_dp[symbol] / (sqrt_v_d * sigma_d + 1e-10)
        norm_xx = file_raw_q[symbol] / (v_d + 1e-10)
        count = file_run_count.get(symbol, 0)

        result[symbol] = (norm_xy, norm_xx, count)

    return result


def _fold_run(symbol, rs, raw_sqrt_q_dp, raw_q, run_count):
    q = rs['vol']
    delta_p = abs(rs['last_p'] - rs['first_p'])
    if q > 0 and delta_p > 0:
        q_ratio = q  # normalized at end of file
        if symbol not in raw_sqrt_q_dp:
            raw_sqrt_q_dp[symbol] = 0.0
            raw_q[symbol] = 0.0
            run_count[symbol] = 0
        raw_sqrt_q_dp[symbol] += np.sqrt(q) * delta_p
        raw_q[symbol] += q
        run_count[symbol] += 1


def calibrate_from_parquet_dir(raw_parquet_dir: str, output_path: str, workers: int = 1):
    """Parallel calibration: each worker processes independent files."""

    all_files = []
    for root, dirs, files in os.walk(raw_parquet_dir):
        for f in files:
            if f.endswith('.parquet'):
                all_files.append(os.path.join(root, f))
    all_files.sort()

    logging.info(f"[CALIBRATOR] {len(all_files)} files, {workers} workers")
    start_time = time.time()

    # Parallel map over files
    if workers > 1:
        with Pool(processes=workers) as pool:
            file_results = []
            for i, result in enumerate(pool.imap_unordered(_process_single_file, all_files)):
                file_results.append(result)
                if (i + 1) % 50 == 0 or i == 0:
                    elapsed = time.time() - start_time
                    eta = elapsed / (i + 1) * (len(all_files) - i - 1)
                    logging.info(f"  {i+1}/{len(all_files)} files done | ETA: {eta/60:.1f}m")
    else:
        file_results = []
        for i, fpath in enumerate(all_files):
            file_results.append(_process_single_file(fpath))
            if (i + 1) % 50 == 0 or i == 0:
                elapsed = time.time() - start_time
                eta = elapsed / (i + 1) * (len(all_files) - i - 1)
                logging.info(f"  {i+1}/{len(all_files)} files | ETA: {eta/60:.0f}m")

    # Merge all workers' results (addition is commutative)
    logging.info("[CALIBRATOR] Merging worker results...")
    symbol_sum_xy = {}
    symbol_sum_xx = {}
    symbol_count = {}

    for result in file_results:
        for symbol, (xy, xx, cnt) in result.items():
            if symbol not in symbol_sum_xy:
                symbol_sum_xy[symbol] = 0.0
                symbol_sum_xx[symbol] = 0.0
                symbol_count[symbol] = 0
            symbol_sum_xy[symbol] += xy
            symbol_sum_xx[symbol] += xx
            symbol_count[symbol] += cnt

    # Compute c_i
    c_factors = {}
    valid_c_list = []

    for symbol in symbol_sum_xy:
        xx = symbol_sum_xx[symbol]
        xy = symbol_sum_xy[symbol]
        if xx < 1e-10:
            continue
        c_i = xy / xx

        if C_LOWER_BOUND < c_i < C_UPPER_BOUND:
            c_factors[symbol] = round(float(c_i), 6)
            valid_c_list.append(c_i)

    global_c = float(np.median(valid_c_list)) if valid_c_list else 0.842
    c_factors['__GLOBAL_A_SHARE_C__'] = round(global_c, 6)

    for symbol in symbol_sum_xy:
        if symbol not in c_factors:
            c_factors[symbol] = round(global_c, 6)

    with open(output_path, 'w') as f:
        json.dump(c_factors, f, indent=2, ensure_ascii=False)

    total_time = time.time() - start_time
    logging.info("=" * 60)
    logging.info(f"CALIBRATION COMPLETE")
    logging.info(f"  A-Share Global Median <c> = {global_c:.4f} (vs TSE 0.842)")
    logging.info(f"  Valid stocks: {len(valid_c_list)}")
    logging.info(f"  c range: [{min(valid_c_list):.4f}, {max(valid_c_list):.4f}]" if valid_c_list else "  No valid c")
    logging.info(f"  Workers: {workers}")
    logging.info(f"  Time: {total_time/60:.1f} minutes")
    logging.info(f"  Output: {output_path}")
    logging.info("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SRL Friction Calibrator (multiprocessing)")
    parser.add_argument("--base_dir", type=str, required=True)
    parser.add_argument("--output", type=str, default="a_share_c_registry.json")
    parser.add_argument("--workers", type=int, default=12,
                        help="Number of parallel workers (default 12)")
    args = parser.parse_args()

    calibrate_from_parquet_dir(args.base_dir, args.output, args.workers)
