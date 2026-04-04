## 修复

Commit dd6aeae (2026-04-01 14:00) — manual full-stack cleanup after reverting Gemini's broken attempt:

1. Removed `TARGET_STD = 216.24` and `TARGET_MEAN = -5.08` constants from:
   - `train.py`, `gcp/train.py`
   - `backtest_5a.py`, `gcp/backtest_5a.py`
2. Replaced ALL `.squeeze()` with `.view(-1)` in:
   - `compute_spear_loss`: `pred.float().squeeze()` → `pred.float().view(-1)` (+ target)
   - `train_one_epoch`: `prediction.squeeze().std()` → `prediction.view(-1).std()`
   - `validate`: `prediction.squeeze()` → `prediction.view(-1)`
   - `compute_epiplexity_mdl_loss`: `prediction.squeeze()` → `prediction.view(-1)`
3. Removed duplicate `main()` call from `train.py` and `gcp/train.py`
4. Added INS-052 (Train-Serve Skew demon) and INS-053 (clean baseline backtest protocol)

## 验证

- `grep TARGET_STD *.py gcp/*.py` = 0 code hits (only comments/lessons remain)
- `grep '.squeeze()' *.py gcp/*.py` = test files only (no production code)
- All 8 modified files pass `py_compile`
- Commit message explicitly lists verification commands and results

## 执法

**doc_only** — C-050 lesson added to OMEGA_LESSONS.md: "grep -r full-stack scan before declaring cleanup complete."

The `tools/paradigm_shift_checklist.md` (created in commit 6f71ba9) includes step: "grep -r all deprecated symbols across *.py, gcp/*.py, tools/*.py — zero hits required before commit."
