> **⚠️ HISTORICAL** — Based on Phase 6 T29 checkpoint. INS-072 invalidated Phase 6 baselines (C-062). Phase 15 confirmed IC=0.029 as selection bias (true mean ~0.010).

# Phase 7 Comprehensive Report — T29 Flagship Backtest

**Date**: 2026-03-30
**Model**: T29 (hd=64, 19.7K params, MDL compression-is-intelligence)
**Data**: 9,423,943 samples, 551 trading days, 20230103 → 20260130
**Strategy**: T+1 overnight momentum — SRL metaorder detection → cross-sectional ranking → long top quintile

---

## 1. Executive Summary

| Metric | Result | Target | Verdict |
|--------|--------|--------|---------|
| Asymmetry Payoff Ratio | **1.20** | > 3.0 | **FAIL** |
| Profit Factor | **1.20** | > 1.5 | **FAIL** |
| Annualized Return | +4.58% | — | Marginal |
| Sharpe Ratio | 0.49 | — | Weak |
| Max Drawdown | -26.5% | — | Deep |

**Verdict**: Phase 7 两项核心 Taleb 指标均未达标。但 17 项深度诊断揭示了关键证据：**信号是真实的，问题出在信号强度不足和度量 bug**，而非模型失效。

---

## 2. Backtest Results (Original Simulation)

### 2.1 Return Metrics

| Metric | Value |
|--------|-------|
| Annualized Return | +4.58% |
| Total Return | +10.29% (NAV 1.1029) |
| Sharpe Ratio | 0.4927 |
| Sortino Ratio | 0.8974 |
| Calmar Ratio | 0.1729 |
| Max Drawdown | -26.50% |
| Max DD Duration | 372 days |
| Breakeven Cost | 44 BP (actual 25 BP) |

### 2.2 Trade Metrics

| Metric | Value |
|--------|-------|
| Total Trades | 14,477 |
| Daily Avg Trades | 26.3 |
| Win Rate | 49.97% |
| Mean Win | 225.97 BP |
| Mean Loss | 188.20 BP |
| Asymmetry Ratio | 1.2007 |
| Profit Factor | 1.1992 |
| Max Single Win | +1,884 BP |
| Max Single Loss | -3,182 BP |

### 2.3 Signal Metrics (Reported by Simulation)

| Metric | Value | Note |
|--------|-------|------|
| Daily IC Mean | 0.027686 | **See Section 4: actual signal is stronger than this** |
| IC Std | 0.072271 | |
| ICIR | 0.3831 | |
| IS IC | 0.027703 | |
| OOS IC | 0.027575 | |
| Monotonicity | 2/9 | **BUG: uses global pooled decile, see Section 4.1** |
| L/S Spread | -5.92 BP | **BUG: same root cause** |

### 2.4 Annual Performance

| Year | Return | Sharpe | Win Rate | Trades | Characterization |
|------|--------|--------|----------|--------|-----------------|
| 2023 | -20.09% | -4.72 | 46.4% | 4,899 | Bear market — signal near-zero |
| 2024 | +8.87% | +0.98 | 51.1% | 4,942 | Recovery — signal improving |
| 2025 | +25.67% | +3.20 | 76.7% | 159* | Bull market — signal strongest |
| 2026 | +0.62% | +4.00 | — | 14 days | Too few days for judgment |

*trades.json capped at 10,000; equity curve covers all trades.

### 2.5 Exit Reason Analysis

| Exit Reason | Count | Pct | Avg PnL |
|-------------|-------|-----|---------|
| natural_horizon | 9,983 | 99.8% | Positive |
| trailing_stop | 17 | 0.2% | -2,098 BP avg |

**BUG**: Trailing stop at -10% is only a LABEL — it does NOT cap PnL. 12/17 stop-triggered trades had losses exceeding -10%, with worst at -31.7%. Root cause: overnight gap in 创业板/科创板 (20% daily limit) pierces stop, and the code only changes `exit_reason` without capping `trade_pnl`.

### 2.6 Limit Filter Impact

| Metric | Value |
|--------|-------|
| Limit-filtered samples | 4,270,846 (45.3%) |
| T+1 lock count | 0 |

45% of the universe filtered by limit-up/limit-down spread-lock heuristic.

---

## 3. Simulation Fixes Applied (This Session)

### 3.1 Trailing Stop Bug Fix

**Before**: L148-149 only changed `exit_reason` label, L152 `trade_pnl = entry_target - half_cost` unaffected.

**After**: Board-aware loss cap that physically constrains per-trade loss:
- Main board (000/600/601/603): cap at -1000 BP/day (-10% daily limit)
- 创业板/科创板 (300/301/688): cap at -2000 BP/day (-20% daily limit)
- Multi-day holds: cap = -board_limit × hold_days

### 3.2 Fix Impact

| Variant | Ann.Ret | Sharpe | Sortino | MaxDD | Asymmetry | PF |
|---------|---------|--------|---------|-------|-----------|-----|
| Original (no cap) | 4.58% | 0.49 | 0.90 | -26.5% | 1.20 | 1.20 |
| +board_loss_cap | 6.31% | 0.66 | 1.25 | -25.1% | 1.21 | 1.21 |
| +exclude 688 | 7.77% | 0.79 | 1.52 | -25.3% | 1.22 | 1.24 |

Board loss cap improved Sharpe +34% and Sortino +39%, but asymmetry barely moved (+0.01). Tail capping only affects 17 trades out of 14,477 — insufficient mass to move mean_loss.

---

## 4. Deep Signal Diagnostics (17 Tests)

### 4.1 CRITICAL: Global vs Daily Decile Discrepancy

**The simulation's reported decile means and monotonicity are WRONG.**

| Decile | Global (Reported) | Daily CS (True) |
|--------|-------------------|-----------------|
| D1 (lowest pred) | +3.33 BP | **-3.88 BP** |
| D2 | +4.47 BP | -2.67 BP |
| D3 | +4.57 BP | -1.85 BP |
| D5 | +3.89 BP | -0.59 BP |
| D7 | +1.58 BP | +1.85 BP |
| D9 | -1.45 BP | +7.43 BP |
| D10 (highest pred) | -2.59 BP | **+14.20 BP** |

**Root cause**: Prediction level drifts across dates (daily mean ranges +14 to +105 BP). Global pooling conflates the temporal drift with the cross-sectional signal, producing an **inverted** decile table.

| Monotonicity | Reported | Actual (daily CS) |
|---|---|---|
| Score | 2/9 | **5.26/9** (mean), 62.4% of days ≥5/9 |

**The trading logic is correct** (ranks within each day's candidates). Only the diagnostic metric is wrong.

### 4.2 Prediction Distribution — Signal Resolution

```
Pred IQR:     20.5 BP (49% within ±10 BP of median)
Target std: 197.9 BP (kurtosis=588, skew=+4.2)
```

The model compresses its predictions into a **very narrow band** (~20 BP range for 50% of stocks) while actual returns span hundreds of BP. The cross-sectional ranking is based on tiny differences — this limits how much alpha can be extracted.

### 4.3 IC Computation Parity

| IC Type | Value | Context |
|---------|-------|---------|
| Training IC | 0.0661 | Per-batch, during gradient descent |
| Global IC (pooled) | **-0.0065** | All 9.4M samples — meaningless due to time drift |
| Daily CS-IC | 0.0277 | Cross-sectional, 551 days — correct |
| Rank IC (Spearman) | 0.0223 | Rank-based CS IC |
| Per-shard IC | 0.0302 | Closer to training context |

**Training IC 0.066 → backtest IC 0.028 is NOT 58% degradation.** It is a difference in measurement granularity (per-batch vs per-day cross-section). Per-shard IC (0.030) is closer to training context and still lower, suggesting some genuine gap, but not catastrophic.

### 4.4 IS vs OOS — No Overfitting

| Split | IC | ICIR | Top Decile Ret |
|-------|-----|------|---------------|
| IS (shard < 1594, ~80%) | 0.0277 | 0.369 | +13.37 BP |
| OOS (shard ≥ 1594, ~20%) | 0.0276 | 0.550 | +19.62 BP |
| **OOS/IS Ratio** | **1.00** | | |

Zero overfitting. OOS even slightly better than IS (higher ICIR and top-decile return).

### 4.5 Quarterly IC — Strong Regime Dependence

| Quarter | IC | ICIR | %IC>0 |
|---------|-----|------|-------|
| 2023Q1 | +0.020 | 0.42 | 61% |
| 2023Q3 | **+0.002** | **0.04** | 57% |
| 2024Q2 | +0.037 | 0.41 | 59% |
| 2025Q1 | +0.045 | 0.63 | 73% |
| 2025Q3 | +0.030 | **0.79** | 76% |
| 2026Q1 | +0.035 | **1.06** | 86% |

2023Q3 IC ≈ 0 (bear market signal failure) → 2025 IC 0.03-0.05 (bull market signal strength). This single regime pattern drives the -20%/+26% annual swing.

### 4.6 IC by Board Type

| Board | IC | ICIR | Note |
|-------|-----|------|------|
| 科创板 688 | **0.039** | **0.49** | Strongest signal |
| 创业板 300 | 0.037 | 0.48 | Strong |
| 主板 | 0.027 | 0.42 | Weakest |

**Excluding 688 removes the strongest signal.** The simulation improvement from excluding 688 (Sharpe 0.66→0.79) came from risk reduction, not signal improvement.

### 4.7 IC by Liquidity

| Quartile | IC | ICIR |
|----------|-----|------|
| Q1 (lowest liquidity) | **0.038** | **0.48** |
| Q2 | 0.032 | 0.40 |
| Q3 | 0.030 | 0.37 |
| Q4 (highest liquidity) | 0.021 | 0.26 |

Low-liquidity stocks: IC 1.8x higher. Consistent with metaorder detection theory — institutional order flow is more visible in thin markets.

### 4.8 Conditional IC — Conviction Filter

| Filter | IC | ICIR | Avg Stocks/Day |
|--------|-----|------|---------------|
| All | 0.028 | 0.38 | 17,077 |
| |pred-median| > 5 BP | 0.032 | 0.39 | 12,199 |
| |pred-median| > 10 BP | 0.037 | 0.40 | 7,928 |
| |pred-median| > 20 BP | **0.044** | **0.42** | 2,716 |
| |pred-median| > 30 BP | **0.054** | **0.47** | 864 |

High-conviction predictions are significantly more accurate. At |pred-median|>30, IC doubles to 0.054 with 864 stocks/day — still sufficient for 50-position portfolio.

### 4.9 Long vs Short Decomposition

| Side | Daily Mean Ret | Sharpe | Alpha vs Middle |
|------|---------------|--------|----------------|
| Top Decile (Long) | +14.20 BP | 3.55 | **+13.34 BP** |
| Bottom Decile (Short) | -3.88 BP | -2.90 | +4.74 BP |
| Middle 80% | +0.87 BP | — | baseline |

Long signal is **3x stronger** than short signal. The model is significantly better at picking winners than avoiding losers.

**Annual long vs short:**

| Year | Top Decile | Bottom Decile | Spread |
|------|-----------|--------------|--------|
| 2023 | +3.08 BP | -4.14 BP | +7.22 BP |
| 2024 | +12.16 BP | -6.92 BP | +19.09 BP |
| 2025 | +26.24 BP | -1.09 BP | +27.33 BP |

### 4.10 Prediction Persistence

Day-to-day top-decile overlap: **52.1%**. The model is "sticky" — it keeps recommending similar stocks across consecutive days. This is consistent with detecting multi-day institutional accumulation, but creates concentration risk.

### 4.11 IC Predictability

No strong predictor of high-IC days found:

| Feature | Corr with IC |
|---------|-------------|
| pred_std | -0.11 |
| target_std | -0.03 |
| n_stocks | +0.09 |
| mean_volume | +0.10 |

The model does not "know when it knows" at the daily aggregate level.

### 4.12 Tail Capture — The Asymmetry Bottleneck

| Target Tail | Captured by Pred-Top-Decile | Lift |
|-------------|---------------------------|------|
| Top 1% | 20.1% | 2.01x |
| Top 5% | 18.7% | 1.87x |
| **Bottom 1%** | **18.4%** | **1.84x** |
| Bottom 5% | 16.1% | 1.61x |

**The model captures upside and downside tails equally.** It selects high-dispersion (volatile) stocks, not directionally-advantaged ones. This is the mathematical root cause of asymmetry = 1.2 instead of 3.0.

### 4.13 Theoretical Asymmetry Limit

With IC=0.028 and target_std=198 BP:
- Expected top-decile excess return = IC × σ × z ≈ 7 BP (actual: 12 BP — model outperforms theory)
- To achieve asymmetry > 3.0: need tail capture lift ≥ 5x (current: 2x)
- Required IC: **> 0.10** or fundamentally different loss function
- **Asymmetry 3.0 is mathematically unreachable at IC=0.028**

---

## 5. Data Artifacts

### 5.1 predictions.parquet (173 MB)

| Column | Type | Description |
|--------|------|-------------|
| symbol | string | A-share ticker (e.g., 000620.SZ) |
| date | string | Trading date YYYYMMDD |
| shard_idx | int64 | WebDataset shard index (0-1991) |
| pred_bp | double | Model prediction in basis points |
| target_bp | double | Forward 20-bar VWAP return in BP |
| bid_p1 | double | Best bid price |
| ask_p1 | double | Best ask price |
| macro_v_d | double | Daily volume macro feature |

**Schema note**: z_sparsity (MDL compression metric) was not included in inference output — should be added in future runs.

### 5.2 phase7_results.json

Full simulation output metrics (see Section 2). **Known issues**: `monotonicity` and `long_short_spread_bp` use global pooled deciles (see Section 4.1).

### 5.3 equity_curve.csv (551 rows)

Daily NAV with positions count, trades opened/closed.

### 5.4 trades.json (10,000 trades, capped)

Per-trade records with symbol, dates, pred, actual, PnL, exit reason.

---

## 6. Known Bugs in `phase7_simulate.py`

| Bug | Severity | Status | Impact |
|-----|----------|--------|--------|
| Trailing stop is label-only (no PnL cap) | HIGH | **Fixed** (board_loss_cap) | 17 trades uncapped (-31% max) |
| Global decile pooling (not daily CS) | MEDIUM | **Identified** | Reported mono 2/9 → actual 5.3/9 |
| `len(results)` undefined (v1) | HIGH | **Fixed** (→ `samples_written`) | Crash on startup |

---

## 7. Phase 8 Evidence-Based Recommendations

### 7.1 Mathematical Reality Check

| Question | Answer | Evidence |
|----------|--------|---------|
| Is the signal real? | **Yes** | Daily CS-IC=0.028, 65% days IC>0, IS≈OOS |
| Is it strong enough for asymmetry>3.0? | **No** | Theoretical limit at IC=0.028 gives max ~1.2 asymmetry |
| Is there overfitting? | **No** | OOS/IS IC ratio = 1.00 |
| Does the model know when it knows? | **Partially** | Conviction filter: IC 0.028→0.054. But no daily-level predictor. |
| Which side is stronger? | **Long** | Long alpha 13.3 BP vs short alpha 4.7 BP (3x) |

### 7.2 Priority-Ranked Directions for Phase 8

| Priority | Direction | Evidence | Expected Impact |
|----------|-----------|----------|----------------|
| **P0** | Fix simulate decile metric (daily CS) | Test 8: global vs daily completely inverted | Correct diagnostics |
| **P1** | Asymmetric loss function (quantile regression or pinball loss) | Test 12: model captures up/down tails equally | Could push tail capture from 2x→3x+ |
| **P2** | Conviction filter (|pred-median|>20 BP) | Test 6: IC doubles to 0.044 | Higher per-trade alpha, fewer trades |
| **P3** | Regime conditioning (reduce exposure when IC low) | Test 4: 2023Q3 IC≈0 destroys full-year return | Avoid -20% bear market years |
| **P4** | IC improvement (architecture/data) | Test 17: currently extracting 2.8% of perfect IC | Root cause of weak asymmetry |
| **P5** | Board-weighted sizing (not exclusion) | Test 10: 688 IC=0.039 is strongest | Keep signal, reduce tail risk |
| **P6** | Add z_sparsity to inference output | Column missing from predictions.parquet | MDL metric could be confidence signal |

### 7.3 What NOT to Do

| Temptation | Why Wrong | Evidence |
|------------|-----------|---------|
| Exclude 科创板 688 | Removes strongest signal (IC=0.039) | Test 10 |
| Over-optimize simulate params | Asymmetry 3.0 unreachable at IC=0.028 | Test 17 |
| Attribute IC drop to overfitting | IS≈OOS, gap is measurement difference | Test 3, 12 |
| Use global IC as diagnostic | Global IC=-0.007 is meaningless | Test 3 |
| Add trailing stop without board awareness | 20% boards gap through 10% stop | Section 2.5 |

---

## 8. Appendix: Simulation Parameters

```yaml
model: T29 (hd=64, wt=32, lr=3.2e-4, lambda_s=1e-7, wu=2, aw=1e-3)
checkpoint: gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt
cost_bp: 25 (stamp_5 + commission_6 + slippage_7 + impact_7)
long_pctile: 0.80 (top 20%)
max_positions: 50
trailing_stop_pct: -10%
train_val_boundary: shard 1594 (80/20 split)
target_definition: 20-bar forward VWAP return (≈0.4 trading days)
strategy: T+1 overnight momentum (buy close, sell next day)
```

---

*Generated 2026-03-30. Source data in `phase7_results/`.*
