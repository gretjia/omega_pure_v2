## 背景

After C-049 fix (d744c4d) removed the `* TARGET_STD` scaling from inference paths, dead code remained across the codebase: `TARGET_STD` and `TARGET_MEAN` constants were still defined in multiple files, and `.squeeze()` calls (known C-008 dimension collapse risk) were only partially replaced. A Gemini-assisted cleanup was attempted.

## 执行序列

1. **13:34 — Post-flight verification plan formalized (56bec7d)**
   - Acknowledged need for exhaustive cleanup

2. **13:51 — First cleanup attempt by Gemini (74138a5)**
   - Commit message: "fix: exhaustive cleanup of TARGET_STD/MEAN and squeeze()"
   - Changes applied to `train.py`, `gcp/train.py`, `backtest_5a.py`, `gcp/backtest_5a.py`, `omega_epiplexity_plus_core.py`
   - **Problem 1**: Missed 4x `.squeeze()` sites in `train.py`/`gcp/train.py`:
     - `compute_spear_loss`: `pred.float().squeeze()` and `target.float().squeeze()`
     - `train_one_epoch`: `prediction.squeeze().std()`
     - `validate`: `prediction.squeeze()` in all_preds collection
   - **Problem 2**: Introduced `IndentationError` in `train.py` — file would not compile
   - **Problem 3**: Added duplicate `main()` call at end of file (from d744c4d, not caught)

3. **13:57 — Full revert (897caad)**
   - `git revert 74138a5` — reverted the broken cleanup
   - All changes from the Gemini cleanup rolled back

4. **14:00 — Second cleanup, manual (dd6aeae)**
   - Proper full-stack grep: `grep -rn TARGET_STD *.py gcp/*.py tools/*.py`
   - Removed `TARGET_STD`/`TARGET_MEAN` constants from all 6 .py files (train, gcp/train, backtest_5a, gcp/backtest_5a, phase7_inference, gcp/phase7_inference)
   - Replaced ALL `.squeeze()` with `.view(-1)` in 8 sites across train + core files
   - Removed duplicate `main()` call
   - Verified: `grep TARGET_STD *.py` = 0 code hits, `grep .squeeze() *.py` = test only
   - All 8 files pass `py_compile`

## 环境

- **Tool**: Gemini (external auditor) performed first cleanup attempt
- **Files affected**: 6 Python source files + their gcp/ mirrors
- **Validation gap**: No `py_compile` check was run after the Gemini commit before pushing
