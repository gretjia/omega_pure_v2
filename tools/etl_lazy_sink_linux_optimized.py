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

import fcntl
import gc
import glob
import logging

import pyarrow as pa
import pyarrow.parquet as pq
import numpy as np
import pandas as pd
from numba import jit

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

def process_file_in_batches(fpath, out_fpath, vol_threshold=50000, window_size=160):
    """
    Reads L1 Base data using iter_batches to strictly avoid df.collect() OOMs.
    Generates Volume-Clocked Parquet shards of `window_size` per symbol.
    """
    if os.path.exists(out_fpath):
        logging.info(f"Skipping already processed file: {out_fpath}")
        return

    pf = pq.ParquetFile(fpath)
    writer = None
    
    # State tracking per symbol
    # { 'symbol': { 'leftover_df': pd.DataFrame, 'bucket_history': list } }
    symbol_states = {}
    
    # Increased default batch size to 300,000 for better throughput
    batch_size = int(os.getenv("OMEGA_ETL_BATCH_SIZE", "300000"))
    
    for batch in pf.iter_batches(batch_size=batch_size):
        # Enable multi-threaded conversion to pandas
        df_chunk = batch.to_pandas(use_threads=True)
        if 'vol_tick' not in df_chunk.columns or 'price' not in df_chunk.columns or 'symbol' not in df_chunk.columns:
            continue
            
        batch_windows = []
        
        for sym, group in df_chunk.groupby('symbol'):
            if sym not in symbol_states:
                symbol_states[sym] = {'leftover_df': pd.DataFrame(), 'bucket_history': []}
            
            state = symbol_states[sym]
            
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
                
                state['bucket_history'].append([
                    prices[0], np.max(prices), np.min(prices), prices[-1], 
                    np.sum(vols), srl, epi
                ])
                
                if len(state['bucket_history']) == window_size:
                    window_matrix = np.array(state['bucket_history'], dtype=np.float32)
                    batch_windows.append({
                        'symbol': sym,
                        'matrix': window_matrix.flatten().tolist()
                    })
                    state['bucket_history'].pop(0)  # slide window by 1
                    
        if batch_windows:
            res_table = pa.Table.from_pandas(pd.DataFrame(batch_windows))
            if writer is None:
                writer = pq.ParquetWriter(out_fpath, res_table.schema, compression='snappy')
            writer.write_table(res_table)
            del res_table

        del batch_windows
        del df_chunk
        del batch
        gc.collect()

    if writer is not None:
        writer.close()
    logging.info(f"Finished processing -> {out_fpath}")

def acquire_single_instance_lock():
    lock_path = os.getenv("OMEGA_ETL_LOCKFILE", "/tmp/etl_lazy_sink_linux.lock")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("Another etl_lazy_sink_linux.py instance is already running")
    return lock_fd

def main():
    lock_fd = acquire_single_instance_lock()
    input_dir = '/omega_pool/parquet_data/latest_base_l1/host=linux1'
    output_dir = '/omega_pool/l1_volume_clock_v2'
    os.makedirs(output_dir, exist_ok=True)
    
    input_files = glob.glob(os.path.join(input_dir, '**', '*.parquet'), recursive=True)
    if not input_files:
        logging.warning(f"No parquet files in {input_dir}. Ready for execution on real data.")
        
    for fpath in input_files:
        out_fpath = os.path.join(output_dir, os.path.basename(fpath))
        process_file_in_batches(fpath, out_fpath, vol_threshold=50000, window_size=160)

    os.close(lock_fd)

if __name__ == '__main__':
    main()
