## 背景

Phase 11c introduced a paradigm shift (Softmax → Pointwise Huber). The Docker image `phase11-v3` was built and submitted to Vertex AI as part of the same deployment. However, the C-049 inference scale bug was only discovered and fixed AFTER the Docker image was already built and the training job was running.

## 执行序列

1. **08:48 — Feature commit + Docker build (89b4ebf)**
   - `gcp/safe_build_and_canary.sh` built Docker image `phase11-v3`
   - Image contains `train.py` with `compute_spear_loss` (new Huber loss) BUT ALSO:
     - `TARGET_STD = 216.24` constant still defined
     - `pred_std_bp = preds.std().item() * TARGET_STD` in validation monitoring
     - `.squeeze()` calls throughout
   - Training job submitted to Vertex AI with this image

2. **10:49 — Code fix committed to git (d744c4d)**
   - Removed `* TARGET_STD` from validation monitoring
   - Replaced `.squeeze()` with `.view(-1)`
   - **But Docker image was already built and running** — fix only exists in git, not in the running container

3. **Epochs 0-14 — Dashboard shows inflated values**
   - Validation code inside Docker: `pred_std_bp = preds.std().item() * TARGET_STD`
   - Actual pred_std: ~2.3 BP (brain-dead model)
   - Dashboard reported: 2.3 * 216.24 = ~489 BP (appeared healthy)
   - Vertex AI Experiments dashboard showed 15 epochs of 216x hallucinated metrics
   - Operator saw "489 BP" and thought the model was producing meaningful variance

4. **Post-E15 — Suspicion arose, local verification attempted**
   - Downloaded checkpoint to local machine
   - Ran `backtest_5a.py` with FIXED code (d744c4d applied locally)
   - Discovered pred_std = 5.6 BP — brain-dead
   - Realized dashboard values had been hallucinations from stale Docker code for the entire run

5. **16:43 — Postmortem (6f71ba9)**
   - C-053 lesson: "Docker build timestamp must post-date code fix commits"
   - Created `tools/paradigm_shift_checklist.md` with explicit step: "rebuild Docker AFTER all fixes"

## 环境

- **Docker registry**: GCR, image tag `phase11-v3`
- **Docker build time**: 08:48 (commit 89b4ebf)
- **Code fix time**: 10:49 (commit d744c4d) — 2 hours AFTER Docker build
- **Vertex AI**: Job 5314881274131775488, running on n1-standard-8 + T4 Spot
- **Gap**: Git HEAD was 2 commits ahead of Docker image for the entire training run
