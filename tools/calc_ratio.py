import os
import glob
import pandas as pd
import numpy as np
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunks_dir', required=True)
    args = parser.parse_args()
    
    pq_files = sorted(glob.glob(os.path.join(args.chunks_dir, 'chunk_*.parquet')))
    if not pq_files:
        print('No parquet files found.')
        return
    
    print(f'Loading {len(pq_files)} chunks...')
    dfs = [pd.read_parquet(f) for f in pq_files]
    df = pd.concat(dfs, ignore_index=True)
    
    preds = df['pred_bp'].values
    targets = df['target_bp'].values
    
    std_yhat = np.std(preds)
    
    p90 = np.percentile(preds, 90)
    p10 = np.percentile(preds, 10)
    
    mask_d9 = preds >= p90
    mask_d0 = preds <= p10
    
    ret_d9 = targets[mask_d9].mean() if mask_d9.any() else 0.0
    ret_d0 = targets[mask_d0].mean() if mask_d0.any() else 0.0
    
    spread = ret_d9 - ret_d0
    ratio = spread / std_yhat if std_yhat > 0 else 0
    cost_threshold = 25.0 / ratio if ratio > 0 else 0
    safe_threshold = 50.0 / ratio if ratio > 0 else 0
    
    print('='*60)
    print('EMPIRICAL CALIBRATION REPORT (Phase 11d Config B - E5 checkpoint)')
    print('='*60)
    print(f'Total Samples evaluated: {len(preds):,}')
    print(f'Std_yhat (pred_std):     {std_yhat:.4f} BP')
    print(f'D9 Return (Top 10%):     {ret_d9:.4f} BP')
    print(f'D0 Return (Bot 10%):     {ret_d0:.4f} BP')
    print(f'D9-D0 Spread:            {spread:.4f} BP')
    print('-'*60)
    print(f'EMPIRICAL RATIO (Spread / Std_yhat): {ratio:.4f}x')
    print(f'CALIBRATED Cost Threshold (25BP):    {cost_threshold:.4f} BP (Must be > this)')
    print(f'CALIBRATED Safe Threshold (50BP):    {safe_threshold:.4f} BP (Healthy zone)')
    print('='*60)
    
if __name__ == '__main__':
    main()