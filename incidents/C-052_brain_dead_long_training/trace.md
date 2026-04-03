## 背景

Phase 11c (commit 89b4ebf) launched a Vertex AI training job with the Pointwise Huber loss. The model was expected to output absolute BP predictions. However, the combination of C-051 (lambda_s and Huber delta miscalibration after paradigm shift) and C-053 (Docker built before code fix) meant the model was effectively brain-dead from epoch 0. This was not discovered until 20 epochs (~9h GPU) had completed.

## 执行序列

1. **08:48 — Phase 11c deployed (89b4ebf)**
   - Docker image `phase11-v3` built and submitted to Vertex AI
   - Training job 5314881274131775488 started on n1-standard-8 + T4 Spot
   - Huber delta=50 BP, lambda_s=1e-3

2. **Epochs 0-19 — Training proceeds without intervention**
   - Dashboard reported `Std_yhat=489 BP` at E2 — appeared non-trivial
   - **Critical**: dashboard values computed by code inside Docker image (old code with `* TARGET_STD`)
   - Actual pred_std was ~5.6 BP (216x smaller) — model predicting near-constant ~30 BP
   - z_core activation at 0.44% — MDL compression term (lambda_s=1e-3) killed all structure
   - No independent inference run on E0 or E1 checkpoint to verify output sanity

3. **Post-training analysis — 20 epochs complete**
   - Downloaded checkpoint, ran local inference with **fixed** code (d744c4d)
   - Observed: pred_std = 5.6 BP, predictions clustered at ~30 BP (mean of target distribution)
   - Model had collapsed to predicting the unconditional mean — zero signal
   - 9h GPU time wasted on a brain-dead model

4. **16:43 — Postmortem documented (6f71ba9)**
   - C-052 lesson: long training needs independent E0-E1 smoke test
   - C-053 lesson: Docker timestamp must post-date code fixes
   - C-054: paradigm shifts are full-stack atomic events

## 环境

- **Compute**: Vertex AI, n1-standard-8 + NVIDIA T4, Spot VM
- **Docker**: `phase11-v3` — built from 89b4ebf (BEFORE d744c4d fix)
- **Data**: WebDataset shards on GCS, pd-ssd staging
- **Dashboard**: Vertex AI Experiments — values from in-Docker code (old, inflated by 216x)
- **Duration**: ~9 hours wall-clock for 20 epochs
