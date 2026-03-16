"""
ETL Lazy Sink Pipeline for Omega Pure v2
----------------------------------------
Implements:
1. Volume Clock (Turnover Clock): Buckets rows using cumulative volume.
2. Max-Receptive-Field ETL: Outputs the maximum possible window (e.g. 160 rows).
3. Ironclad Anti-OOM: Uses PyArrow iter_batches to stream without ANY global .collect().
"""

import pyarrow.parquet as pq
import pyarrow as pa
import numpy as np
import pandas as pd
import os
import glob
from numba import jit
import logging

logging.basicConfig(level=logging.INFO)

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

def process_file_in_batches(fpath, out_fpath, vol_threshold=100000, window_size=160):
    """
    Reads L1 Base data using iter_batches to strictly avoid df.collect() OOMs.
    Generates Volume-Clocked Parquet shards of `window_size`.
    """
    pf = pq.ParquetFile(fpath)
    writer = None
    
    # State tracking across batches
    leftover_df = pd.DataFrame()
    bucket_history = []
    
    for batch in pf.iter_batches(batch_size=500000):
        df_chunk = batch.to_pandas()
        if 'vol_tick' not in df_chunk.columns or 'price' not in df_chunk.columns:
            continue
            
        if leftover_df.empty:
            df = df_chunk
            df['cum_vol'] = df['vol_tick'].cumsum()
        else:
            last_cum_vol = leftover_df['cum_vol'].iloc[-1]
            df_chunk['cum_vol'] = df_chunk['vol_tick'].cumsum() + last_cum_vol
            df = pd.concat([leftover_df, df_chunk], ignore_index=True)
            
        df['vol_bucket'] = df['cum_vol'] // vol_threshold
        
        grouped = df.groupby('vol_bucket')
        bucket_ids = sorted(list(grouped.groups.keys()))
        
        if len(bucket_ids) <= 1:
            leftover_df = df
            continue
            
        # The last bucket is incomplete, save it for the next batch
        complete_buckets = bucket_ids[:-1]
        leftover_df = df[df['vol_bucket'] == bucket_ids[-1]].copy()
        
        batch_windows = []
        for bkt in complete_buckets:
            group = grouped.get_group(bkt)
            prices = group['price'].values
            vols = group['vol_tick'].values
            srl, epi = compute_srl_epiplexity(prices, vols)
            
            # Collapse rows to 2D Matrix Row representation
            bucket_history.append([
                prices[0],              # open
                np.max(prices),         # high
                np.min(prices),         # low
                prices[-1],             # close
                np.sum(vols),           # volume
                srl,                    # srl_residual
                epi                     # epiplexity
            ])
            
            # Form maximum possible windows when history hits max receptive field
            if len(bucket_history) == window_size:
                window_matrix = np.array(bucket_history, dtype=np.float32)
                batch_windows.append({'matrix': window_matrix.flatten().tolist()})
                bucket_history.pop(0)  # slide window by 1
                
        if batch_windows:
            # We construct the chunk locally, memory bound by batch_size & window_size
            res_table = pa.Table.from_pandas(pd.DataFrame(batch_windows))
            if writer is None:
                writer = pq.ParquetWriter(out_fpath, res_table.schema, compression='snappy')
            writer.write_table(res_table)
            
    if writer is not None:
        writer.close()
    logging.info(f"Finished processing -> {out_fpath}")

def main():
    input_dir = '/data/base_l1'  # Replace with actual 2.2TB input dir
    output_dir = '/data/l1_volume_clock' # Output 188GB dir
    os.makedirs(output_dir, exist_ok=True)
    
    input_files = glob.glob(os.path.join(input_dir, '*.parquet'))
    if not input_files:
        logging.warning(f"No parquet files in {input_dir}. Ready for execution on real data.")
        
    for fpath in input_files:
        out_fpath = os.path.join(output_dir, os.path.basename(fpath))
        process_file_in_batches(fpath, out_fpath, vol_threshold=50000, window_size=160)

if __name__ == '__main__':
    main()
