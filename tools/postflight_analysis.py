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

# === Step 7: CROSS-SECTIONAL ANALYSIS (INS-067, C-065/C-066) ===
print()
print("=" * 70)
print("=== STEP 7: CROSS-SECTIONAL ANALYSIS (per-date, INS-067) ===")
print("  Global D9-D0 mixes all dates → volatility sorting bias.")
print("  Cross-sectional: rank within each date, then average.")
print()

min_stocks = 50
dates_with_enough = df.groupby("date").size()
valid_dates = dates_with_enough[dates_with_enough >= min_stocks].index
df_cs = df[df.date.isin(valid_dates)].copy()
print(f"  Dates total: {df.date.nunique()} | With >={min_stocks} stocks: {len(valid_dates)}")
print(f"  Samples used: {len(df_cs):,} / {len(df):,}")
print()

# Per-date IC
daily_ics = []
daily_rank_ics = []
daily_spreads = []
daily_monos = []

for date, grp in df_cs.groupby("date"):
    if len(grp) < min_stocks:
        continue
    # Pearson IC
    ic = grp.pred_bp.corr(grp.target_bp)
    if not np.isnan(ic):
        daily_ics.append(ic)
    # Spearman Rank IC
    ric = grp.pred_bp.rank().corr(grp.target_bp.rank())
    if not np.isnan(ric):
        daily_rank_ics.append(ric)
    # Per-date decile spread
    try:
        grp_dec = pd.qcut(grp.pred_bp, 10, labels=False, duplicates="drop")
        dec_means = grp.groupby(grp_dec)["target_bp"].mean()
        if len(dec_means) >= 2:
            sp = dec_means.iloc[-1] - dec_means.iloc[0]
            daily_spreads.append(sp)
            mn = sum(1 for i in range(len(dec_means)-1) if dec_means.iloc[i+1] > dec_means.iloc[i])
            daily_monos.append(mn / max(len(dec_means)-1, 1))
    except Exception:
        pass

print("=== CROSS-SECTIONAL IC ===")
if daily_ics:
    ic_arr = np.array(daily_ics)
    ric_arr = np.array(daily_rank_ics) if daily_rank_ics else np.array([0])
    print(f"  Daily Pearson IC:  mean={ic_arr.mean():.4f}  std={ic_arr.std():.4f}  "
          f"t-stat={ic_arr.mean()/(ic_arr.std()/np.sqrt(len(ic_arr))+1e-8):.2f}  "
          f"N_days={len(ic_arr)}")
    print(f"  Daily Rank IC:     mean={ric_arr.mean():.4f}  std={ric_arr.std():.4f}  "
          f"t-stat={ric_arr.mean()/(ric_arr.std()/np.sqrt(len(ric_arr))+1e-8):.2f}  "
          f"N_days={len(ric_arr)}")
    print(f"  ICIR (IC/std):     {ic_arr.mean()/(ic_arr.std()+1e-8):.4f}")
print()

print("=== CROSS-SECTIONAL D9-D0 SPREAD ===")
if daily_spreads:
    sp_arr = np.array(daily_spreads)
    print(f"  Daily D9-D0:  mean={sp_arr.mean():.2f} BP  std={sp_arr.std():.2f}  "
          f"t-stat={sp_arr.mean()/(sp_arr.std()/np.sqrt(len(sp_arr))+1e-8):.2f}  "
          f"N_days={len(sp_arr)}")
    print(f"  Positive days: {(sp_arr > 0).sum()}/{len(sp_arr)} ({(sp_arr > 0).mean()*100:.1f}%)")
    mn_arr = np.array(daily_monos)
    print(f"  Avg monotonicity: {mn_arr.mean():.2f}")
print()

print("=== CROSS-SECTIONAL vs GLOBAL COMPARISON ===")
print(f"  {'Metric':<25} {'Global':>12} {'Cross-Sect':>12} {'Delta':>10}")
print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*10}")
cs_ic = np.mean(daily_ics) if daily_ics else 0
cs_ric = np.mean(daily_rank_ics) if daily_rank_ics else 0
cs_spread = np.mean(daily_spreads) if daily_spreads else 0
print(f"  {'Pearson IC':<25} {ic_global:>12.4f} {cs_ic:>12.4f} {cs_ic - ic_global:>+10.4f}")
print(f"  {'Rank IC':<25} {rank_ic:>12.4f} {cs_ric:>12.4f} {cs_ric - rank_ic:>+10.4f}")
print(f"  {'D9-D0 Spread (BP)':<25} {spread:>12.2f} {cs_spread:>12.2f} {cs_spread - spread:>+10.2f}")
print()

# Cross-sectional verdict
print("=== CROSS-SECTIONAL VERDICT ===")
if daily_spreads:
    if cs_spread > cost_bp:
        print(f"  CS D9-D0 = {cs_spread:.2f} BP > {cost_bp} BP cost -> TRADEABLE (cross-sectional)")
    elif cs_spread > 5:
        print(f"  CS D9-D0 = {cs_spread:.2f} BP -> MARGINAL (cross-sectional)")
    elif cs_spread > 0:
        print(f"  CS D9-D0 = {cs_spread:.2f} BP -> WEAK POSITIVE (cross-sectional)")
    else:
        print(f"  CS D9-D0 = {cs_spread:.2f} BP -> NEGATIVE (cross-sectional, model inverts within-day)")
    if cs_spread > 0 and spread <= 0:
        print(f"  *** SIGNAL EXISTS but was HIDDEN by global sorting bias! ***")
    elif cs_spread <= 0 and spread <= 0:
        print(f"  *** Signal truly absent — both global and cross-sectional negative ***")
else:
    print("  Insufficient data for cross-sectional analysis")
