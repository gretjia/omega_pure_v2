## WHY Chain

1. Phase 11c changed loss function semantics (Softmax → Huber) — a paradigm shift
2. Huber delta=50 BP and lambda_s=1e-3 were not calibrated for the new output scale (C-051)
3. lambda_s=1e-3 structure tax was too aggressive — killed z_core activation (0.44%)
4. Model collapsed to predicting unconditional mean (~30 BP) — zero discriminative signal
5. Dashboard showed `Std_yhat=489 BP` — appeared healthy, but this was 216x inflated by old Docker code (C-053)
6. No independent validation was run on E0-E1 checkpoints outside the Docker container
7. Training ran for 20 full epochs (~9h GPU) before anyone checked with fixed inference code

**Root**: Trusted the dashboard (which ran old code) instead of running an independent smoke test with the fixed inference pipeline after E0-E1.

## 模式泛化

**Unvalidated Long Training**: When a paradigm shift introduces multiple interacting changes (loss function + regularization + output scale), the model may be catastrophically broken from E0 but appear healthy on dashboard metrics that are themselves computed by stale code.

Prevention requires an **independent verification loop**:
- After E0-E1 completes, download checkpoint
- Run inference with the LATEST (not Docker-embedded) inference script
- Assert pred_std is in a physically plausible range (e.g., 30-300 BP for T+1 overnight)
- Only continue training if smoke test passes

The key insight: training logs and dashboards are part of the system under test — they cannot validate themselves (Ω1: only trust measured results from independent tools).
