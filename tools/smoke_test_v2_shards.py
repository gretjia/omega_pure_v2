
import pyarrow.parquet as pq
import numpy as np
import pandas as pd
import sys
import os

def smoke_test(file_path):
    print(f"--- Smoke Test: {file_path} ---")
    try:
        # 1. Read the first few rows
        table = pq.read_table(file_path)
        df = table.to_pandas()
        
        print(f"Columns found: {df.columns.tolist()}")
        print(f"Total rows in shard: {len(df)}")
        
        if 'symbol' not in df.columns or 'matrix' not in df.columns:
            print("❌ ERROR: Missing required columns 'symbol' or 'matrix'")
            return False
            
        # 2. Verify matrix shape and content
        first_matrix = df['matrix'].iloc[0]
        matrix_len = len(first_matrix)
        print(f"First matrix length: {matrix_len}")
        
        # Expected: 160 rows * 7 features (price_open, high, low, close, vol, srl, epi)
        expected_len = 160 * 7
        if matrix_len != expected_len:
            print(f"❌ ERROR: Matrix length {matrix_len} does not match expected {expected_len}")
            return False
            
        # 3. Try to reshape
        reshaped = np.array(first_matrix, dtype=np.float32).reshape(160, 7)
        print("✅ Reshape to (160, 7) SUCCESSFUL")
        
        # 4. Check for NaNs or Inf
        if np.isnan(reshaped).any() or np.isinf(reshaped).any():
            print("⚠️ WARNING: Found NaN or Inf values in matrix")
        else:
            print("✅ Data integrity check: No NaNs or Inf")
            
        # 5. Check symbol diversity
        unique_symbols = df['symbol'].unique()
        print(f"Number of unique symbols in this shard: {len(unique_symbols)}")
        if len(unique_symbols) < 1:
             print("❌ ERROR: No symbols found")
             return False

        print("--- SMOKE TEST PASSED ---")
        return True
    except Exception as e:
        print(f"❌ SMOKE TEST FAILED with error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python smoke_test_v2_shards.py <path_to_parquet>")
        sys.exit(1)
    
    path = sys.argv[1]
    if os.path.isdir(path):
        import glob
        files = glob.glob(os.path.join(path, "*.parquet"))
        if not files:
            print(f"No parquet files in {path}")
            sys.exit(1)
        # Test the first file
        smoke_test(files[0])
    else:
        smoke_test(path)
