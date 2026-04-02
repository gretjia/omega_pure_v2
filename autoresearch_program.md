# Autoresearch Goal: Cure Variance Collapse (Phase 11d)

## Background
The model is suffering from Variance Collapse ("脑死亡", INS-054). To escape the L1 regularization (`lambda_s * s_t`) and the `Huber loss` clipping (`delta`), it has learned to turn off all features (`z_core=0`) and output a near-constant prediction. The variance (`Std_yhat`) has plummeted to 13-23 BP, while we need it to naturally stay above 30 BP.

## Objective
Modify the `compute_spear_loss` function in `train.py`. Your goal is to design a new loss function topology or algebraic combination that maximizes the `FINAL_REWARD` when running `python tools/autoresearch_sandbox.py`.

The reward function in our sandbox is:
`Reward = Val_PfRet - 2.0 * max(0.0, 30.0 - Val_Std_yhat)`

This explicitly penalizes the model if it outputs a constant (`Std_yhat` < 30 BP), while rewarding high portfolio returns (`Val_PfRet`).

## Constraints
1. **ONLY** modify `compute_spear_loss` in `train.py`. Do not touch other files.
2. Do **NOT** change the function signature of `compute_spear_loss`.
3. The function MUST return a tuple of `(total_loss, pf_ret, s_t)`. `total_loss` must be a scalar tensor with `.backward()` attached.

## Ideas to try:
- **Leaky target blinding:** Instead of clamping negative returns to zero (`torch.clamp(target, min=0.0)`), allow a small gradient for negative returns.
- **Log-Cosh loss:** Try replacing Huber loss with Log-Cosh for a smoother gradient transition.
- **Dynamic feature tax:** Make the `lambda_s` penalty decay dynamically if `pred.std()` is too low.
- **Variance bonus:** Add `- alpha * pred.std()` directly into the `total_loss` to force the network to increase dispersion.
- **Asymmetric Pearson:** Re-introduce Pearson correlation but bound it.

## Execution
Run `python tools/autoresearch_sandbox.py`. Check the `FINAL_REWARD`. Iterate.