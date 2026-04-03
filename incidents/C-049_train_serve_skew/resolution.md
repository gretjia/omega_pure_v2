## 修复

Commit d744c4d (2026-04-01 10:49):
- Removed `* TARGET_STD + TARGET_MEAN` from `backtest_5a.py` and `gcp/backtest_5a.py`
- Removed `* TARGET_STD` from validation pred_std monitoring in `train.py` and `gcp/train.py`
- Replaced `.squeeze()` with `.view(-1)` across all sites (C-008 prevention)
- Model output now used directly as absolute BP — no reverse scaling

## 验证

- `backtest_5a.py` output predictions in ~20 BP range (physically plausible for T+1 overnight)
- `gcp/train.py` validation pred_std reported in raw BP (not inflated)
- Confirmed by grep: no remaining `* TARGET_STD` in inference/backtest code paths

## 执法

**doc_only** — C-049 lesson added to OMEGA_LESSONS.md (commit 203f0a4).

Post-incident, C-054 created `tools/paradigm_shift_checklist.md` (commit 6f71ba9) as an executable checklist for future architecture-level changes. Requires full-stack grep of all output consumers before any loss function or output semantics change.
