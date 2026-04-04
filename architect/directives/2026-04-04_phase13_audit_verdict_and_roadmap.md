# AUDIT VERDICT: PHASE 12 POST-FLIGHT & PHASE 13 ARCHITECTURAL ROADMAP

**Date**: 2026-04-04
**Source**: External Audit AI Agent (post Phase 12 post-flight)
**Source ID**: PHASE12_AUDIT_PROMPT.md → External Audit Agent response
**Axiom Impact**: UPDATE REQUIRED — Loss function, evaluation metric, model topology, regularization

---

**TO:** OMEGA Engineering & Architecture Teams  
**FROM:** External Audit AI Agent  
**DATE:** 2026-04-04  
**SUBJECT:** Resolution of Phase 11/12 Variance Collapse & Phase 13 Directives  

---

## 1. EXECUTIVE SUMMARY & STRUCTURAL DIAGNOSIS

Phase 12's intervention ("Unbounded Spear") achieved theoretical mathematical convergence but suffered a catastrophic translation failure to trading viability. The combination of **Leaky Blinding** and **MSE** warped the network's gradient geometry. The 100x gradient compression ($0.1^2$) on negative returns mathematically incentivized the model to ignore downside movement and exclusively fit the high-volatility positive right-tail. Consequently, the model ceased predicting directional Alpha and became a trivial volatility magnitude predictor, converging on an artificial offset.

Coupled with a low Signal-to-Noise Ratio (SNR = 2.4%), MSE defaulted to predicting conditional means. The architecture is currently suffering from severe topological paralysis: **Global Mean Pooling** is destroying spatiotemporal sequence data, **missing residual connections** are wasting capacity, and a **global ranking evaluation bug** is misrepresenting the model's true cross-sectional discriminative power.

---

## 2. THE TRIBUNAL VERDICTS: RESOLVING PENDING DECISIONS

### DECISION 1: Maintain or Drop "Leaky Blinding"?
**VERDICT: DROP IMMEDIATELY.**
* **Rationale:** While the financial intuition—ignoring downside retail panic due to short-selling restrictions in A-shares—is valid, the mathematical implementation is fatal. Scaling negative targets by 0.1 prior to an MSE loss compresses the gradient penalty by a factor of 100. The network takes the path of least mathematical resistance: it ignores negative returns and acts as a volatility magnitude predictor. This directly caused the Volatility Prediction Bias (Issue 3.1) and Artificial Target Convergence (Issue 3.2). Constraints like "long-only" belong in the portfolio execution logic, not the loss function's target space.

### DECISION 2: Revert to IC Loss or Fix MSE?
**VERDICT: REVERT TO IC LOSS (Rank-Based Objective).**
* **Rationale:** In a high-variance (Std = 189.60 BP), low-SNR (2.4%) environment, MSE is catastrophically vulnerable to outliers and will invariably default to fitting conditional means to minimize large symmetric penalties, wiping out the weak discriminative ranking signal (Issue 3.4). The trading execution relies entirely on daily cross-sectional sorting (buying D9, avoiding D0). IC Loss optimizes directly for this ordinality. The microscopic absolute scales ($10^{-4}$) produced by IC loss are an inference engineering issue, solvable via Daily Cross-Sectional Z-Score normalization post-forward pass.

### DECISION 3: The Global Mean Pooling Contradiction
**VERDICT: HYPOTHESIS CONFIRMED, BUT POOLING MUST BE DEPRECATED.**
* **Rationale:** Your hypothesis is mathematically sound. IC Loss survived Global Mean Pooling (GMP) in Phase 6 because it evaluates *relative* ordinality (covariances); relative ranking relationships can survive linear averaging better than exact absolute values. MSE, which requires exact absolute reconstruction, breaks completely under GMP. Regardless of the loss function, collapsing 1,600 spatiotemporal tokens into 16 scalars (Issue 4.1) acts as a severe low-pass filter, destroying localized institutional accumulation footprints.

### DECISION 4: Interpret the -29σ Rank IC
**VERDICT: GLOBAL VOLATILITY SORTING DISGUISED AS MEAN REVERSION.**
* **Rationale:** A -28.4σ Rank IC indicates a highly robust, non-random signal. Given the spatiotemporal limitations (hard-capped 32-bar isolated windows), the model might be reacting to immediate intraday price shocks and subsequent retail mean reversion. However, this is drastically exacerbated by the **Global Ranking Mismatch (Issue 4.6)**. Because the evaluation metric pools all dates globally, the model is simply sorting global volatility. High-volatility stocks have massive right tails (pulling the mean target up to +9.04) but lower win rates (49%). You must evaluate the model strictly cross-sectionally per day to determine if this inverted signal is real or an artifact of global pooling.

### DECISION 5: Historical Baseline Integrity
**VERDICT: MANDATORY RE-VERIFICATION.**
* **Rationale:** The `torch.compile(strict=False)` silent checkpoint failure is a critical breach in the scientific chain of custody. If the Phase 6 (IC=0.066) and Phase 11c (D9-D0=8.90 BP) baselines were achieved using partially uninitialized weights or dropped state tensors acting as stochastic regularization, their benchmark status is completely invalid. You cannot calibrate Phase 13 against corrupted baselines.

### DECISION 6: Effective Model Capacity
**VERDICT: FIX TOPOLOGY BEFORE SCALING PARAMETERS.**
* **Rationale:** 24.4K parameters is an appropriate capacity constraint for a noisy 2.4% SNR environment to prevent overfitting. However, the model cannot even overfit a tiny 64-sample batch (Issue 4.5). This proves the network is suffering from a physical information bottleneck, not just parameter starvation. 20% of the model (the TDA RPB table) has dead gradients (Issue 4.2), and missing residual connections (Issue 4.4) force attention layers to waste capacity learning identity mappings.

---

## 3. PHASE 13 ARCHITECTURAL DIRECTIVES

To resolve the mathematical and structural collapses, execute the following mandates for Phase 13:

1. **Objective Function:** Deprecate MSE, Static Centering, and Leaky Blinding. Reinstantiate IC Loss (Pearson/Spearman) to isolate the discriminative Alpha ranking signal.
2. **Cross-Sectional Evaluation (CRITICAL):** Refactor `backtest_5a.py` and the training loop to compute `D9-D0` and Rank IC strictly **cross-sectionally per daily shard**. Remove the `torch.topk` global pool over all dates to prevent volatility bias (Issue 4.6).
3. **Topological Unblocking:**
   - **Residuals:** Insert standard residual connections around the TDA layer (`x = x + self.model.tda_layer(x)`).
   - **Positional Encodings:** Debug the inert RPB table gradients, or replace it with standard sinusoidal encodings / RoPE to restore spatial awareness.
   - **Pooling:** Replace Global Mean Pooling with Attention Pooling, a `[CLS]` token, or Flattening + Linear Projection.
4. **Regularization:** Remove the L1 regularization (MDL Guillotine) on `z_core` (Issue 3.5) to prevent indiscriminate destruction of the weak discriminative signal.
5. **Inference Scaling:** Implement daily cross-sectional Z-score standardization on model predictions to provide stable thresholds for execution logic.
