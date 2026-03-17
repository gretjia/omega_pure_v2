import os
import glob
import random
import pyarrow.parquet as pq
import pandas as pd
import numpy as np
import logging
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def simple_acf(x, nlags):
    n = len(x)
    variance = np.var(x)
    if variance == 0:
        return np.zeros(nlags)
    x = x - np.mean(x)
    result = np.correlate(x, x, mode='full')[-n:]
    result /= (variance * n)
    return result[:nlags+1]

def sample_files(base_dir, fraction=0.01):
    all_files = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f.endswith('.parquet'):
                all_files.append(os.path.join(root, f))
    if not all_files:
        logging.error(f"No parquet files found in {base_dir}")
        return []
    sampled = random.sample(all_files, max(1, int(len(all_files) * fraction)))
    logging.info(f"Sampled {len(sampled)} files out of {len(all_files)}")
    return sampled

def phase1_vol_threshold(files, target_bars_per_day=50):
    daily_vols = []
    logging.info("Starting Phase 1: Calculating vol_threshold...")
    for f in files:
        try:
            pf = pq.ParquetFile(f)
            for batch in pf.iter_batches(batch_size=500000):
                df = batch.to_pandas()
                if 'time' not in df.columns or 'vol_tick' not in df.columns or 'symbol' not in df.columns:
                    continue
                
                # Use existing 'date' column if it exists, otherwise derive from 'time'
                if 'date' not in df.columns:
                    df['date'] = df['time'].astype(str).str[:10]
                
                grouped = df.groupby(['symbol', 'date'])['vol_tick'].sum().reset_index()
                daily_vols.append(grouped)
        except Exception as e:
            logging.warning(f"Error processing {f}: {e}")

    if not daily_vols:
        logging.warning("No volume data found in sample. Defaulting to 50000.")
        return 50000
        
    all_daily_vols = pd.concat(daily_vols, ignore_index=True)
    median_daily_vol = all_daily_vols['vol_tick'].median()
    threshold = int(median_daily_vol / target_bars_per_day)
    logging.info(f"Median Daily Volume across sample: {median_daily_vol:.2f}")
    logging.info(f"Target Bars/Day: {target_bars_per_day}")
    logging.info(f"Derived vol_threshold: {threshold}")
    return max(threshold, 1000)

def phase2_window_size(files, vol_threshold):
    logging.info(f"Starting Phase 2: Calculating window_size using vol_threshold={vol_threshold}...")
    max_lag = 150
    all_drop_idxs = []
    
    # Process up to 5 files for ACF to save time but get enough data
    for f in files[:5]:
        symbol_histories = {}
        try:
            pf = pq.ParquetFile(f)
            for batch in pf.iter_batches(batch_size=500000):
                df = batch.to_pandas()
                if 'vol_tick' not in df.columns or 'price' not in df.columns or 'symbol' not in df.columns:
                    continue
                
                # Pre-sort by symbol to speed up grouping
                for sym, group in df.groupby('symbol'):
                    group = group.copy()
                    if sym not in symbol_histories:
                        symbol_histories[sym] = {'leftover': pd.DataFrame(), 'buckets': []}
                        
                    sh = symbol_histories[sym]
                    if sh['leftover'].empty:
                        group['cum_vol'] = group['vol_tick'].cumsum()
                    else:
                        last_cum_vol = sh['leftover']['cum_vol'].iloc[-1]
                        group['cum_vol'] = group['vol_tick'].cumsum() + last_cum_vol
                        group = pd.concat([sh['leftover'], group], ignore_index=True)
                        
                    group['vol_bucket'] = group['cum_vol'] // vol_threshold
                    bkt_grouped = group.groupby('vol_bucket')
                    bucket_ids = sorted(list(bkt_grouped.groups.keys()))
                    
                    if len(bucket_ids) <= 1:
                        sh['leftover'] = group
                        continue
                        
                    complete_buckets = bucket_ids[:-1]
                    sh['leftover'] = group[group['vol_bucket'] == bucket_ids[-1]].copy()
                    
                    for bkt in complete_buckets:
                        bkt_df = bkt_grouped.get_group(bkt)
                        prices = bkt_df['price'].values
                        if len(prices) > 1:
                            returns = np.diff(prices)
                            srl = np.sum(returns) / (np.sum(np.abs(returns)) + 1e-8)
                            sh['buckets'].append(srl)
                            
            # Compute ACF
            for sym, sh in symbol_histories.items():
                arr = np.array(sh['buckets'])
                if len(arr) > max_lag:
                    acf_vals = simple_acf(arr, max_lag)
                    drop_idx = max_lag
                    for i in range(1, len(acf_vals)):
                        if abs(acf_vals[i]) < 0.05:
                            drop_idx = i
                            break
                    all_drop_idxs.append(drop_idx)
        except Exception as e:
            logging.warning(f"Error processing {f}: {e}")

    if not all_drop_idxs:
        logging.warning("Not enough continuous buckets to compute ACF. Defaulting to 160.")
        return 160
        
    window = int(np.median(all_drop_idxs))
    logging.info(f"Derived window_size (Median ACF drop < 0.05): {window}")
    return max(window, 40)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", type=str, required=True, help="Path to raw 2.2TB Parquet files")
    parser.add_argument("--fraction", type=float, default=0.02, help="Fraction of files to sample")
    args = parser.parse_args()
    
    files = sample_files(args.base_dir, fraction=args.fraction)
    if not files:
        logging.error("No files found. Exiting.")
        exit(1)
        
    vt = phase1_vol_threshold(files)
    ws = phase2_window_size(files, vt)
    
    print("\n" + "="*40)
    print(" EMPIRICAL CALIBRATION COMPLETE")
    print("="*40)
    print(f" [Derived Constants]")
    print(f" vol_threshold = {vt}")
    print(f" window_size   = {ws}")
    print("="*40)
