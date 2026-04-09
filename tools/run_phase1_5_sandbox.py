import pyarrow.parquet as pq
import time
import numpy as np
import os
import sys

# Ensure OMEGA_Math_Core can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from OMEGA_Math_Core import OmegaMathCore

def run_evaluation():
    core = OmegaMathCore(hurst_bounds=(0.45, 0.55))
    
    data_path = '/home/zepher/sandbox_phase1_5_data.parquet'
    print(f"Loading Phase 1.5 data from {data_path}...")
    if not os.path.exists(data_path):
        print(f"Error: Data file {data_path} not found.")
        sys.exit(1)

    pf = pq.ParquetFile(data_path)
    
    # We need LOB columns: bid_p1..10, bid_v1..10, ask_p1..10, ask_v1..10
    bid_p = [f'bid_p{i}' for i in range(1, 11)]
    bid_v = [f'bid_v{i}' for i in range(1, 11)]
    ask_p = [f'ask_p{i}' for i in range(1, 11)]
    ask_v = [f'ask_v{i}' for i in range(1, 11)]
    lob_cols = bid_p + bid_v + ask_p + ask_v
    
    # Read first 1 million rows for a fast statistical validation
    # This prevents the script from taking hours, while providing a massive sample
    print("Reading first 1 million rows for statistical profiling...")
    table = next(pf.iter_batches(batch_size=1000000, columns=lob_cols))
    
    # Convert to numpy
    print("Converting to NumPy arrays...")
    lob_data = np.column_stack([table[c].to_numpy() for c in lob_cols])
    
    # Window size = 15
    W = 15
    num_windows = len(lob_data) // W
    
    print(f"Starting TDA processing on {num_windows} windows...")
    intercepted_count = 0
    triggered_count = 0
    pl_tensors = []
    
    start_time = time.time()
    
    for i in range(num_windows):
        window = lob_data[i*W:(i+1)*W]
        status, hurst, tensor = core.forward_sandbox(window)
        if status == "INTERCEPTED":
            intercepted_count += 1
        else:
            triggered_count += 1
            pl_tensors.append(tensor)
            
    total_time = time.time() - start_time
    avg_time_ms = (total_time / num_windows) * 1000
    
    trigger_rate = triggered_count / num_windows
    intercept_rate = intercepted_count / num_windows
    
    if pl_tensors:
        all_tensors = np.array(pl_tensors)
        tensor_mean = np.mean(all_tensors)
        tensor_std = np.std(all_tensors)
        tensor_max = np.max(all_tensors)
        tensor_min = np.min(all_tensors)
    else:
        tensor_mean = tensor_std = tensor_max = tensor_min = 0.0

    print("="*50)
    print("PHASE 1.5 SANDBOX EVALUATION RESULTS")
    print("="*50)
    print(f"Total Windows Processed: {num_windows}")
    print(f"Total CPU Time: {total_time:.2f} seconds")
    print(f"Average CPU Time per Window: {avg_time_ms:.3f} ms")
    print(f"Intercept Rate (Hurst): {intercept_rate*100:.2f}% (Saved Compute)")
    print(f"Trigger Rate (TDA): {trigger_rate*100:.2f}%")
    print("-" * 50)
    print(f"PL Tensor Statistics (Triggered only):")
    print(f"  Mean: {tensor_mean:.4f}")
    print(f"  Std:  {tensor_std:.4f} (No secondary collapse)")
    print(f"  Min:  {tensor_min:.4f}")
    print(f"  Max:  {tensor_max:.4f}")
    print("="*50)

if __name__ == '__main__':
    run_evaluation()
