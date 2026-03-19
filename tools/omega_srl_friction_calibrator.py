"""
OMEGA SRL Friction Calibrator (Phase 0.6)
-----------------------------------------
Empirically calibrates per-stock SRL friction coefficient c_i for A-shares.

Method (per architect directive id4):
  1. Identify metaorder proxies via directional runs (consecutive same bs_flag)
  2. Per run: Q = sum(vol_tick), |ΔP| = |last_price - first_price|
  3. Nondimensionalize: X = √(Q/V_D), Y = |ΔP|/σ_D
  4. OLS without intercept: c_i = Σ(X·Y) / Σ(X²)

Physical bounds: 0.05 < c_i < 10.0 (anomalies → use global median)
Output: a_share_c_registry.json

Streaming design: processes one parquet file (= one trading day) at a time.
Data memory bounded per file: pending_runs cleared after each file.
Cross-file state: only per-symbol OLS accumulators (2 floats/symbol ≈ 80KB for 5000 symbols).
Metadata lists (file paths, final c values) are O(num_symbols) ≈ trivial.
"""

import os
import sys
import json
import time
import numpy as np
import pyarrow.parquet as pq
import logging

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Calibration config (from current_spec.yaml srl_calibration)
MIN_DAILY_VOLUME = 1000.0
MAX_Q_RATIO = 0.1       # Runs > 10% of daily volume = anomaly (涨停打板)
C_LOWER_BOUND = 0.05
C_UPPER_BOUND = 10.0


def _fold_run_raw(symbol: str, rs: dict, raw_sqrt_q_dp: dict, raw_q: dict, run_count: dict):
    """Fold a completed run into per-file raw accumulators (2 floats, no list).
    raw_sqrt_q_dp[sym] += √Q · |ΔP|
    raw_q[sym] += Q
    These are normalized by daily V_D and σ_D at end of file.
    """
    q = rs['vol']
    delta_p = abs(rs['last_p'] - rs['first_p'])
    if q > 0 and delta_p > 0:
        q_ratio_proxy = q  # Will be divided by V_D at end of file
        if symbol not in raw_sqrt_q_dp:
            raw_sqrt_q_dp[symbol] = 0.0
            raw_q[symbol] = 0.0
            run_count[symbol] = 0
        raw_sqrt_q_dp[symbol] += np.sqrt(q) * delta_p
        raw_q[symbol] += q
        run_count[symbol] += 1


def calibrate_from_parquet_dir(raw_parquet_dir: str, output_path: str):
    """Stream all parquet files, compute per-stock c_i, write registry."""

    all_files = []
    for root, dirs, files in os.walk(raw_parquet_dir):
        for f in files:
            if f.endswith('.parquet'):
                all_files.append(os.path.join(root, f))
    all_files.sort()

    logging.info(f"[CALIBRATOR] Scanning {len(all_files)} parquet files...")

    # Per-symbol OLS accumulators: sum_xy and sum_xx
    # c_i = sum_xy / sum_xx
    symbol_sum_xy = {}
    symbol_sum_xx = {}
    symbol_count = {}

    start_time = time.time()

    for file_idx, fpath in enumerate(all_files):
        parquet_file = pq.ParquetFile(fpath)

        # Per-symbol daily accumulators (one file = one trading day)
        daily_stats = {}    # symbol → {vol, high, low}
        run_state = {}      # symbol → {bs, vol, first_p, last_p}
        # Per-symbol per-file OLS pre-accumulators (2 floats/symbol, no list)
        # raw_sqrt_q_dp = Σ √Q_k · |ΔP_k|  (before daily normalization)
        # raw_q = Σ Q_k                       (before daily normalization)
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

                # Daily stats
                if symbol not in daily_stats:
                    daily_stats[symbol] = {'vol': 0.0, 'high': price, 'low': price}
                ds = daily_stats[symbol]
                ds['vol'] += vol
                if price > ds['high']:
                    ds['high'] = price
                if price < ds['low']:
                    ds['low'] = price

                # Directional run tracking
                if symbol not in run_state:
                    run_state[symbol] = {'bs': bs, 'vol': vol, 'first_p': price, 'last_p': price}
                    continue

                rs = run_state[symbol]
                if bs == rs['bs']:
                    rs['vol'] += vol
                    rs['last_p'] = price
                else:
                    # Run completed → fold into per-file raw accumulators (no list!)
                    _fold_run_raw(symbol, rs, file_raw_sqrt_q_dp, file_raw_q, file_run_count)
                    rs['bs'] = bs
                    rs['vol'] = vol
                    rs['first_p'] = price
                    rs['last_p'] = price

        # Flush final runs
        for symbol, rs in run_state.items():
            _fold_run_raw(symbol, rs, file_raw_sqrt_q_dp, file_raw_q, file_run_count)

        # End of file: normalize raw accumulators with daily V_D and σ_D
        # OLS: sum_xy += raw_sqrt_q_dp / (√V_D · σ_D)
        #       sum_xx += raw_q / V_D
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

            if symbol not in symbol_sum_xy:
                symbol_sum_xy[symbol] = 0.0
                symbol_sum_xx[symbol] = 0.0
                symbol_count[symbol] = 0

            symbol_sum_xy[symbol] += norm_xy
            symbol_sum_xx[symbol] += norm_xx
            symbol_count[symbol] += file_run_count.get(symbol, 0)

        # Progress
        if (file_idx + 1) % 50 == 0 or file_idx == 0:
            elapsed = time.time() - start_time
            eta = elapsed / (file_idx + 1) * (len(all_files) - file_idx - 1)
            logging.info(
                f"  File {file_idx+1}/{len(all_files)} | "
                f"{len(symbol_sum_xy)} symbols | ETA: {eta/60:.0f}m"
            )

    # Compute c_i for each symbol
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

    # Global A-share median
    if valid_c_list:
        global_c = float(np.median(valid_c_list))
    else:
        global_c = 0.842
        logging.warning("No valid c_i computed, falling back to TSE default 0.842")

    c_factors['__GLOBAL_A_SHARE_C__'] = round(global_c, 6)

    # Fill missing symbols with global median
    for symbol in symbol_sum_xy:
        if symbol not in c_factors:
            c_factors[symbol] = round(global_c, 6)

    # Write output
    with open(output_path, 'w') as f:
        json.dump(c_factors, f, indent=2, ensure_ascii=False)

    total_time = time.time() - start_time
    logging.info("=" * 60)
    logging.info(f"CALIBRATION COMPLETE")
    logging.info(f"  A-Share Global Median <c> = {global_c:.4f} (vs TSE 0.842)")
    logging.info(f"  Valid stocks calibrated: {len(valid_c_list)}")
    logging.info(f"  Total symbols: {len(c_factors) - 1}")
    logging.info(f"  c range: [{min(valid_c_list):.4f}, {max(valid_c_list):.4f}]" if valid_c_list else "  No valid c values")
    logging.info(f"  Time: {total_time/60:.1f} minutes")
    logging.info(f"  Output: {output_path}")
    logging.info("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SRL Friction Calibrator for A-shares")
    parser.add_argument("--base_dir", type=str, required=True,
                        help="Directory containing raw L1 parquet files")
    parser.add_argument("--output", type=str, default="a_share_c_registry.json",
                        help="Output JSON path")
    args = parser.parse_args()

    calibrate_from_parquet_dir(args.base_dir, args.output)
