"""Phase 11d Post-Flight Analysis — Steps 3-6 of post_flight_plan.md"""
import sys
import pandas as pd
import numpy as np

parquet_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/smoke_test/phase11d_A_val_predictions.parquet"
df = pd.read_parquet(parquet_path)

print(f"=== POST-FLIGHT ANALYSIS: Phase 11d ===")
print(f"File: {parquet_path}")
print(f"Samples: {len(df):,} | Symbols: {df.symbol.nunique()} | Dates: {df.date.nunique()}")
print()

# === Step 3: Threshold Calibration (C-055) ===
print("=== STEP 3: THRESHOLD CALIBRATION (C-055) ===")
pred_std = df.pred_bp.std()
print(f"pred_bp:   mean={df.pred_bp.mean():.2f}  std={pred_std:.2f}  range=[{df.pred_bp.min():.1f}, {df.pred_bp.max():.1f}]")
print(f"target_bp: mean={df.target_bp.mean():.2f}  std={df.target_bp.std():.2f}")
print()

df["pred_decile"] = pd.qcut(df.pred_bp, 10, labels=False, duplicates="drop")
decile_means = df.groupby("pred_decile")["target_bp"].mean()
spread = decile_means.iloc[-1] - decile_means.iloc[0]
mono = sum(1 for i in range(len(decile_means)-1) if decile_means.iloc[i+1] > decile_means.iloc[i])

ratio = spread / pred_std if pred_std > 0 else 0
cost_bp = 25.0
cost_threshold = cost_bp / ratio if ratio > 0 else float("inf")
safe_threshold = (cost_bp * 2) / ratio if ratio > 0 else float("inf")

print(f"D9-D0 spread:    {spread:.2f} BP")
print(f"Monotonicity:    {mono}/{len(decile_means)-1}")
print(f"Spread/pred_std: {ratio:.2f}")
covered = "COVERED" if spread > cost_bp else "NOT COVERED"
print(f"Cost coverage:   spread({spread:.1f}) vs cost({cost_bp} BP) = {covered}")
print()
print(f"CALIBRATED THRESHOLDS (from full val data):")
print(f"  sentinel_error (cost/3):  {cost_threshold/3:.1f} BP")
print(f"  sentinel_warn  (cost):    {cost_threshold:.1f} BP")
print(f"  healthy        (2x cost): {safe_threshold:.1f} BP")
print()

# === Step 4: Full Decile Table ===
print("=== STEP 4: PREDICTION DECILE vs ACTUAL RETURN ===")
header = f"  {'Decile':<8} {'N':>7} {'mean_pred':>10} {'mean_target':>12} {'hit_rate':>9} {'IC':>8}"
print(header)
for d in sorted(df.pred_decile.unique()):
    b = df[df.pred_decile == d]
    mp = b.pred_bp.mean()
    mt = b.target_bp.mean()
    hr = (b.target_bp > 0).mean()
    ic = b.pred_bp.corr(b.target_bp) if len(b) > 2 else float("nan")
    print(f"  D{d:<7} {len(b):>7} {mp:>10.2f} {mt:>12.2f} {hr:>9.1%} {ic:>8.4f}")
print(f"  Spread: {spread:.2f} BP | Mono: {mono}/{len(decile_means)-1}")
print()

# === Step 5: Key Correlations ===
print("=== STEP 5: KEY CORRELATIONS ===")
ic_global = df.pred_bp.corr(df.target_bp)
rank_ic = df.pred_bp.rank().corr(df.target_bp.rank())
corr_zs_pred = df.z_sparsity.corr(df.pred_bp.abs())
corr_zs_target = df.z_sparsity.corr(df.target_bp)
print(f"  Pearson IC:               {ic_global:.4f}")
print(f"  Spearman Rank IC:         {rank_ic:.4f}")
print(f"  Corr(z_sparsity, |pred|): {corr_zs_pred:.4f}  (Phase 10=-0.34, 11c=-0.22)")
print(f"  Corr(z_sparsity, target): {corr_zs_target:.4f}")
print(f"  z_sparsity: mean={df.z_sparsity.mean():.4f} std={df.z_sparsity.std():.4f}")
print()

# === Step 6: Epiplexity Axiom Verification ===
print("=== STEP 6: EPIPLEXITY AXIOM (z_sparsity DECILE vs ALPHA) ===")
df["sp_decile"] = pd.qcut(df.z_sparsity, 10, labels=False, duplicates="drop")
header2 = f"  {'S_Dec':<8} {'N':>7} {'mean_zs':>10} {'mean_target':>12} {'mean_|pred|':>12} {'IC':>8}"
print(header2)
for d in sorted(df.sp_decile.unique()):
    b = df[df.sp_decile == d]
    mzs = b.z_sparsity.mean()
    mt = b.target_bp.mean()
    mpa = b.pred_bp.abs().mean()
    ic = b.pred_bp.corr(b.target_bp) if len(b) > 2 else float("nan")
    tag = " LOW" if d <= 2 else (" HIGH" if d >= 7 else "")
    print(f"  S{d:<7} {len(b):>7} {mzs:>10.5f} {mt:>12.2f} {mpa:>12.2f} {ic:>8.4f}{tag}")

# Final verdict
print()
print("=== VERDICT ===")
print(f"  pred_std = {pred_std:.2f} BP (Phase 11c was 5.64, improvement: {pred_std/5.64:.1f}x)")
print(f"  D9-D0 spread = {spread:.2f} BP (Phase 11c was 8.90)")
print(f"  IC = {ic_global:.4f} (Phase 11c was 0.0210)")
if spread > cost_bp:
    print(f"  RESULT: SPREAD COVERS {cost_bp:.0f} BP COST -> TRADEABLE SIGNAL")
elif spread > 15:
    print(f"  RESULT: SPREAD PARTIAL ({spread:.0f}/{cost_bp:.0f} BP) -> MARGINAL")
else:
    print(f"  RESULT: SPREAD INSUFFICIENT ({spread:.0f}/{cost_bp:.0f} BP) -> NOT TRADEABLE")
