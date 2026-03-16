"""
WebDataset Converter for Omega Pure v2
--------------------------------------
Converts Volume-Clocked Parquet shards into .tar shards.
Essential for Ironclad Anti-OOM Architecture during distributed DDP training.
"""

import webdataset as wds
import pyarrow.parquet as pq
import numpy as np
import glob
import os
import logging

logging.basicConfig(level=logging.INFO)

def convert_to_wds(parquet_dir, wds_dir, window_size=160, max_size=1e9, max_count=10000):
    os.makedirs(wds_dir, exist_ok=True)
    parquet_files = glob.glob(os.path.join(parquet_dir, '*.parquet'))
    
    if not parquet_files:
        logging.warning(f"No Parquet files found in {parquet_dir}. Waiting for ETL.")
        return

    pattern = os.path.join(wds_dir, "shard-%06d.tar")
    
    # maxsize handles 1GB shards natively to avoid OOM
    with wds.ShardWriter(pattern, maxsize=max_size, maxcount=max_count) as sink:
        idx = 0
        for fpath in parquet_files:
            logging.info(f"Converting {fpath} to WebDataset shards...")
            pf = pq.ParquetFile(fpath)
            
            # Use iter_batches again to prevent OOM while converting to WDS
            for batch in pf.iter_batches(batch_size=50000):
                df = batch.to_pandas()
                if 'matrix' not in df.columns:
                    continue
                
                for _, row in df.iterrows():
                    # Reshape the flat list back to the (160, num_features) max receptive field matrix
                    matrix = np.array(row['matrix'], dtype=np.float32).reshape(window_size, -1)
                    
                    # Write pure tensor bytes to the .tar 
                    sink.write({
                        "__key__": f"sample_{idx:08d}",
                        "data.npy": matrix,
                    })
                    idx += 1

if __name__ == '__main__':
    parquet_input_dir = '/data/l1_volume_clock' # 188GB dir
    wds_output_dir = '/data/wds_shards'         # Target tar shards dir
    convert_to_wds(parquet_input_dir, wds_output_dir)
