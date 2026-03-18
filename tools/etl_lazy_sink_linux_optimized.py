"""
ETL Lazy Sink Pipeline for Omega Pure v2 - Optimized for Linux1
---------------------------------------------------------------
Implements:
1. Volume Clock (Turnover Clock): Buckets rows using cumulative volume.
2. Max-Receptive-Field ETL: Outputs the maximum possible window (e.g. 160 rows).
3. Ironclad Anti-OOM: Uses PyArrow iter_batches to stream without ANY global .collect().
4. Performance Tuning: Increased threads and batch size for AMD AI Max 395.
"""

import os
# Optimized for 64GB RAM limit and 32-core CPU
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "8")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "8")

import gc
import glob
import logging
import sys

import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
import pandas as pd
from numba import jit

# Conditional import for Unix-specific file locking
if sys.platform != "win32":
    import fcntl

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@jit(nopython=True)
def compute_srl_epiplexity(prices, volumes):
    if len(prices) < 2:
        return 0.0, 0.0
    returns = np.diff(prices)
    # SRL Residual
    srl = np.sum(returns) / (np.sum(np.abs(returns)) + 1e-8)
    # Epiplexity
    epi = np.std(returns) * np.sum(volumes[1:])
    return srl, epi

def compute_rolling_adv_threshold(group, default_threshold=50000):
    # Fallback to default if we can't compute historical ADV safely in this streaming context
    # Ideally, this would use a pre-computed ADV lookup table, but for streaming, we approximate
    # by taking the daily volume and dividing by 50 bars.
    daily_vol = group['vol_tick'].sum()
    # If the chunk is less than a day, extrapolate or use default to prevent micro-bars
    estimated_adv = max(daily_vol, default_threshold * 50)
    return max(int(estimated_adv / 50), 1000)

def process_file_in_batches(fpath, out_fpath, window_size=160, stride=20):
    """
    Reads L1 Base data using iter_batches to strictly avoid df.collect() OOMs.
    Generates Volume-Clocked Parquet shards of `window_size` per symbol using a Ring Buffer.
    Restores 10-level spatial depth (Bid/Ask).
    """
    if os.path.exists(out_fpath):
        logging.info(f"Skipping already processed file: {out_fpath}")
        return

    pf = pq.ParquetFile(fpath)
    writer = None
    
    # State tracking per symbol
    # { 'symbol': { 'leftover_df': pd.DataFrame, 'bucket_history': list, 'dynamic_threshold': int } }
    symbol_states = {}
    
    # Increased default batch size to match Windows (500,000)
    batch_size = int(os.getenv("OMEGA_ETL_BATCH_SIZE", "500000"))
    
    for batch in pf.iter_batches(batch_size=batch_size):
        # Disable multi-threaded conversion as it causes a regression in this specific workload
        df_chunk = batch.to_pandas(use_threads=False)
        if 'vol_tick' not in df_chunk.columns or 'price' not in df_chunk.columns or 'symbol' not in df_chunk.columns:
            continue
            
        batch_windows = []
        
        for sym, group in df_chunk.groupby('symbol'):
            if sym not in symbol_states:
                # Architect Directive 1: Dynamic Rolling ADV Threshold (Relative Capacity Clock)
                dyn_threshold = compute_rolling_adv_threshold(group)
                symbol_states[sym] = {'leftover_df': pd.DataFrame(), 'bucket_history': [], 'dynamic_threshold': dyn_threshold}
            
            state = symbol_states[sym]
            vol_threshold = state['dynamic_threshold']
            
            if state['leftover_df'].empty:
                df = group
                df['cum_vol'] = df['vol_tick'].cumsum()
            else:
                last_cum_vol = state['leftover_df']['cum_vol'].iloc[-1]
                group['cum_vol'] = group['vol_tick'].cumsum() + last_cum_vol
                df = pd.concat([state['leftover_df'], group], ignore_index=True)
                
            df['vol_bucket'] = df['cum_vol'] // vol_threshold
            grouped = df.groupby('vol_bucket')
            bucket_ids = sorted(list(grouped.groups.keys()))
            
            if len(bucket_ids) <= 1:
                state['leftover_df'] = df
                continue
                
            complete_buckets = bucket_ids[:-1]
            state['leftover_df'] = df[df['vol_bucket'] == bucket_ids[-1]].copy()
            
            for bkt in complete_buckets:
                bkt_group = grouped.get_group(bkt)
                prices = bkt_group['price'].values
                vols = bkt_group['vol_tick'].values
                srl, epi = compute_srl_epiplexity(prices, vols)
                
                # Architect Directive 2: Restore the Spatial Axis (10-level depth)
                # We snapshot the LOB state at the *end* of the volume bucket.
                last_row = bkt_group.iloc[-1]
                
                # We construct a spatial representation: 10 Bid levels + 10 Ask levels
                # Shape: [10_spatial_levels, Features(Price, Vol, SRL, Epi)]
                # For simplicity in 2D flattening, we interleave Bid/Ask or stack them.
                spatial_snapshot = []
                for i in range(1, 11):
                    # Bid Side
                    bid_p = last_row.get(f'bid_p{i}', 0.0)
                    bid_v = last_row.get(f'bid_v{i}', 0.0)
                    spatial_snapshot.append([bid_p, bid_v, srl, epi])
                    
                    # Ask Side
                    ask_p = last_row.get(f'ask_p{i}', 0.0)
                    ask_v = last_row.get(f'ask_v{i}', 0.0)
                    spatial_snapshot.append([ask_p, ask_v, srl, epi])
                
                # Append the 20-element spatial array for this time step
                state['bucket_history'].append(spatial_snapshot)
                
                # Architect Directive 3: Translation-Invariant Ring Buffer
                if len(state['bucket_history']) == window_size:
                    # Current shape: [160_time, 20_spatial, 4_features]
                    window_matrix = np.array(state['bucket_history'], dtype=np.float32)
                    batch_windows.append({
                        'symbol': sym,
                        'matrix': window_matrix.flatten().tolist()
                    })
                    # Slide the window by `stride` instead of tumbling (clearing all)
                    state['bucket_history'] = state['bucket_history'][stride:]
                    
        if batch_windows:
            res_table = pa.Table.from_pandas(pd.DataFrame(batch_windows))
            if writer is None:
                writer = pq.ParquetWriter(out_fpath, res_table.schema, compression='snappy')
            writer.write_table(res_table)
            del res_table

        del batch_windows
        del df_chunk
        del batch
        # Removed explicit gc.collect() as it creates massive per-batch overhead.
        # Python's generational GC will handle cleanup efficiently enough.

    if writer is not None:
        writer.close()
    logging.info(f"Finished processing -> {out_fpath}")

def acquire_single_instance_lock():
    if sys.platform == "win32":
        # Windows fallback: Skip strict file locking or implement msvcrt equivalent if needed.
        # For this controlled dual-node setup, skipping is safe enough on Windows.
        return None
        
    lock_path = os.getenv("OMEGA_ETL_LOCKFILE", "/tmp/etl_lazy_sink_linux.lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("Another etl_lazy_sink_linux.py instance is already running")
    return lock_fd

def main():
    lock_fd = acquire_single_instance_lock()
    
    # OS-specific path routing
    if sys.platform == "win32":
        input_dir = 'D:/Omega_frames/latest_base_l1'
        output_dir = 'D:/Omega_frames/l1_volume_clock_v2'
    else:
        input_dir = '/omega_pool/parquet_data/latest_base_l1/host=linux1'
        output_dir = '/omega_pool/l1_volume_clock_v2'
        
    os.makedirs(output_dir, exist_ok=True)
    
    input_files = glob.glob(os.path.join(input_dir, '**', '*.parquet'), recursive=True)
    if not input_files:
        logging.warning(f"No parquet files in {input_dir}. Ready for execution on real data.")
        
    for fpath in input_files:
        out_fpath = os.path.join(output_dir, os.path.basename(fpath))
        # Removed hardcoded vol_threshold, now dynamically computed per symbol (Relative Capacity Clock)
        process_file_in_batches(fpath, out_fpath, window_size=160, stride=20)

    if lock_fd is not None:
        os.close(lock_fd)

if __name__ == '__main__':
    main()
