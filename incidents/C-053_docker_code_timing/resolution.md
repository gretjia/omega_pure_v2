## 修复

1. Phase 11c training results discarded — 20 epochs with stale Docker code
2. Phase 11d (commit 3565610) rebuilt Docker with all fixes applied:
   - d744c4d (inference scale fix)
   - dd6aeae (full-stack cleanup: TARGET_STD removal, .squeeze() → .view(-1))
   - New hyperparameters (delta=200, lambda_s=1e-4)
3. Verified Docker image contents matched git HEAD before submitting new job

## 验证

- `docker run --rm phase11d python -c "import train; print('OK')"` — confirms latest code
- Independent inference run on E0 checkpoint (outside Docker) confirmed pred_std in physical range
- Dashboard values cross-checked against independent local inference — values match (no 216x gap)

## 执法

**doc_only** — C-053 lesson in OMEGA_LESSONS.md:
"Docker build timestamp must post-date ALL code fix commits. After any fix to files inside the Docker image, rebuild + canary. 'Fixed in git' does not mean 'fixed in Docker.'"

`tools/paradigm_shift_checklist.md` (commit 6f71ba9) includes step:
"After all fixes pass py_compile + grep verification, rebuild Docker image. Verify image commit hash matches git HEAD."

Future enforcement opportunity: Add git commit hash as Docker label at build time, and have `safe_submit.sh` compare Docker label commit vs current git HEAD. Reject if they differ.
