## 修复

1. Training job results discarded — model was brain-dead (pred_std=5.6 BP, zero signal)
2. Phase 11d (commit 3565610, 2026-04-01 15:42) launched with recalibrated hyperparameters:
   - Huber delta raised: 50 → 200 BP (less aggressive gradient clipping)
   - lambda_s reduced: 1e-3 → 1e-4 (lighter structure tax, allow z_core to survive)
   - Added variance sentinel: auto-abort if pred_std drops below threshold
3. Created `tools/monitor_phase11d.sh` (commit 6f71ba9) for independent checkpoint monitoring

## 验证

- Phase 11d checkpoint verified by independent inference run (not dashboard)
- pred_std confirmed in physically plausible range after E0
- Variance sentinel active in training loop

## 执法

**doc_only** — C-052 lesson in OMEGA_LESSONS.md:
"Long training (>2h) must have independent E0-E1 smoke test: download checkpoint, run fixed inference script, assert pred_std in physical range. Dashboard values from inside Docker are not independent validation."

`tools/monitor_phase11d.sh` provides a manual monitoring script but is not an automated gate. Future enforcement: integrate variance sentinel as hard abort into `train.py` training loop (partially done in Phase 11d via variance sentinel).
