## WHY Chain

1. Phase 11c changed the loss function from Softmax cross-entropy (normalized logits) to Pointwise Huber (absolute BP)
2. This changed the **semantic meaning** of model output from "relative ranking scores" to "BP predictions"
3. The change was applied only to `compute_spear_loss` in `train.py` — the training pipeline
4. `backtest_5a.py` and `phase7_inference.py` still contained `* TARGET_STD + TARGET_MEAN` reverse scaling, designed for the old normalized output
5. 20 BP absolute predictions * 216.24 = 4319 BP — a 216x inflation that destroyed backtest results

**Root**: Architecture-level semantic change (output unit) treated as a point fix (loss function only). No full-stack grep for downstream consumers of model output.

## 模式泛化

**Train-Serve Skew**: When the training pipeline changes the semantics of model output (units, scale, distribution), every downstream consumer (inference, backtest, monitoring, dashboard) must be updated atomically. This is a **full-stack semantic change**, not a training-only change.

The pattern is especially dangerous because:
- Training code runs fine (loss computed correctly in new units)
- Inference/backtest code runs fine (no errors, just wrong numbers)
- The bug is **silent** — only detectable by checking output magnitude against physical priors
