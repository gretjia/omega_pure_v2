# AUDIT VERDICT: PHASE 12 POST-MORTEM & PHASE 13 ARCHITECTURAL ROADMAP (V2)

**Date**: 2026-04-04
**Source**: External Audit AI Agent (Architecture Auditor) — V2 updated verdict
**Source ID**: PHASE12_AUDIT_PROMPT.md → External Audit Agent response (revised)
**Axiom Impact**: UPDATE REQUIRED — Loss function, evaluation metric, model topology, regularization, window isolation
**Supersedes**: 2026-04-04_phase13_audit_verdict_and_roadmap.md (V1: "POST-FLIGHT")

---

**TO:** OMEGA Engineering & Architecture Teams  
**FROM:** External Audit AI Agent (Architecture Auditor)  
**DATE:** 2026-04-04  
**SUBJECT:** Final Verdict on Variance Collapse, Historical Illusions, and Phase 13 Directives  

---

## 1. EXECUTIVE DIAGNOSIS: THE VOLATILITY ILLUSION

The engineering team's Phase 12 analysis is a masterful forensic diagnosis. By systematically untangling codebase bugs (e.g., the critical `strict=False` checkpoint failure) from architectural flaws, we have successfully isolated the true bottlenecks of the OMEGA model.

The data conclusively proves that **the model is not "broken" from a learning perspective; rather, it has perfectly learned the exact mathematical shortcuts incentivized by our flawed objective function and strangled topology.** 

The most critical revelation is the **Phase 6 Historical Baseline Review**. Discovering that our "best" historical model (Train IC=0.066) actually yielded a negative Post-Flight D9-D0 (-5.92 BP) fundamentally shifts our understanding: **OMEGA has never successfully solved the cross-sectional Alpha sorting problem.** Historically, the model has been trapped in a **Volatility Sorting Illusion**. High-volatility stocks possess massive right-tail positive returns, which artificially inflates mean target metrics. However, these same stocks have abysmal hit rates (D9 hit rate 49.0% vs D0 51.4%). OMEGA was simply sorting by historical variance, buying highly volatile "lotto-ticket" stocks, and losing to mean reversion.

Phase 12's "Unbounded Spear" intervention exacerbated this. The **100x gradient compression** of Leaky Blinding on negative returns forced the network to mathematically ignore the left tail, completely sealing its fate as a trivial volatility-magnitude predictor.

---

## 2. RESOLUTION OF UNRESOLVED MYSTERIES & TRIBUNAL VERDICTS

Based on the empirical evidence provided, here are the definitive mathematical answers to the pending investigations and the 6 Tribunal dilemmas:

### 2.1 The Metric Divergence: Pearson IC (+0.0095) vs. Rank IC (-0.0193)
* **Diagnosis:** **Outlier Dominance.** Pearson IC measures linear covariance and is hypersensitive to extreme magnitude. Rank IC (Spearman) measures monotonicity and ignores magnitude.
* **Mechanics:** Because Leaky Blinding and MSE forced the model to chase the extreme right tail of high-volatility stocks, a few massive positive predictions successfully aligned with massive positive targets, dragging the Pearson IC into statistically significant positive territory ($t=2.29$). However, for the bulk of the cross-section (the non-outliers), the model's discriminative logic is actively sorting them backward, yielding a negative Rank IC. 
* **Tribunal Verdict 4:** The -29σ Rank IC confirms the model is a tail-magnitude detector, not a cross-sectional ranker. The signal is inverted because, in A-shares, extreme short-term volatility often precedes mean reversion.

### 2.2 RPB Gradient Death (Grad Norm = 0.08) & Effective Capacity
* **Diagnosis:** **Global Mean Pooling (GMP) is the assassin.**
* **Mechanics:** GMP `torch.mean(x, dim=[1,2])` is a commutative operation—sequence order does not matter ($Mean(A,B) = Mean(B,A)$). Because the loss function is calculated on this averaged scalar, backpropagation routes near-zero gradients to the Relative Position Bias (RPB) table. The network mathematically realizes that spatiotemporal geometry is useless because the GMP bottleneck annihilates it before the output layer. 
* **Tribunal Verdict 3 & 6:** The capacity (24.4K params) is sufficient for a 2.4% SNR environment, but the topology is blocked. 20% of the parameters (RPB) are dead, and missing residual connections force attention layers to waste capacity learning identity mappings. **Deprecate Global Mean Pooling.**

### 2.3 Phase 6 Degradation (IC 0.066 → Post-Flight 0.028 & D9-D0 = -5.92 BP)
* **Diagnosis:** **Train-Serve Skew via Global Evaluation & Checkpoint Corruption.**
* **Mechanics:** A 2.4x decay is partly standard Out-Of-Sample (OOS) decay, but the deeply negative D9-D0 reveals a catastrophic **Global Ranking Mismatch (Issue 4.6)**. IC Loss optimized *relative* daily sorting, but evaluating `torch.topk` globally across all dates selected the most volatile *days* overall, not the best stocks per day. 
* **Tribunal Verdict 5:** The `strict=False` checkpoint bug likely created phantom training metrics by bypassing dropout or leaking state. **All historical baselines are invalidated.**

### 2.4 The Loss Function Dilemma: IC vs. MSE + Leaky Blinding
* **Tribunal Verdict 1:** **DROP LEAKY BLINDING IMMEDIATELY.** Market execution constraints (e.g., short-selling restrictions) belong in the portfolio optimizer, never in the loss function target space.
* **Tribunal Verdict 2:** **REVERT TO IC LOSS (Rank-Based Objective).** In a 2.4% SNR environment with a 190 BP target standard deviation, MSE is mathematically doomed. It will always default to predicting conditional means to minimize massive outlier penalties, washing out the ranking signal. The "microscopic absolute scales" ($10^{-4}$) produced by IC loss are an inference engineering issue, trivially solved via daily cross-sectional Z-score normalization post-forward pass.

---

## 3. PHASE 13 ARCHITECTURAL BLUEPRINT (THE REFORGE)

We must clear the board. Phase 13 will execute a structural resection to unblock the physical information flow and force the model to learn Cross-Sectional Alpha.

### MANDATE A: Objective Function & Metric Isolation
1. **Purge Target Warping:** Remove Leaky Blinding ($0.1$ multiplier) and Static Centering. Pass raw `target_bp` to the loss function.
2. **Strict Cross-Sectional Rank Objective:** Revert to a differentiable ranking loss (e.g., Pearson/Spearman IC Loss). Crucially, this loss **MUST** be computed *strictly per daily cross-sectional shard* (`mask_date`). 
3. **Cross-Sectional Metrics Only:** Refactor `backtest_5a.py`. `D9-D0`, `Pearson IC`, and `Rank IC` must be computed independently for each date, then averaged. Global `torch.topk` sorting is strictly prohibited.

### MANDATE B: Topological Unblocking
1. **Annihilate Global Mean Pooling (CRITICAL):** Replace `torch.mean(z_core, dim=[1, 2])` with **Attention Pooling**, a dedicated `[CLS]` token, or extracting the final temporal token (if causal). We must preserve the spatiotemporal footprint of institutional accumulation.
2. **Restore Residual Connections:** Wrap the TDA layer in a standard residual pathway: `x = LayerNorm(x + self.model.tda_layer(x))`. 
3. **Shatter Window Isolation:** The 5 isolated 32-bar windows prevent the model from seeing patterns spanning more than 0.64 days. Implement cross-window attention or overlapping sliding windows.

### MANDATE C: Regularization & Inference Standardization
1. **Suspend the MDL Guillotine:** Set `lambda_s = 0.0`. As proven by E19, $L_1$ sparsity compression (5.4% $\rightarrow$ 18.5%) actively murders the fragile Alpha signal. We must establish a robust `D9-D0` baseline *before* we attempt to compress the latent space.
2. **Inference Z-Scoring:** Apply a cross-sectional Z-score `(pred - mean)/std` to the model's raw outputs during inference to provide stable thresholds for the trading execution logic.

**NEXT ACTION:** Implement Mandate B (Topological Unblocking). Run the 64-sample Crucible Overfit Test. *Pass Criteria: Loss reaches absolute 0.0, proving gradients to the RPB table are revived and the physical information bottleneck has been cleared.*

**STATUS: APPROVED.** OMEGA is cleared for Phase 13 topology reconstruction.

---

## DIFF vs V1 (自动生成)

### V2 新增内容（V1 中不存在）:
1. **§1 波动率幻觉诊断**: Phase 6 D9-D0=-5.92 BP, D9 hit rate 49.0% vs D0 51.4%, "OMEGA has never solved cross-sectional Alpha"
2. **§2.1 Mechanics**: Pearson IC t=2.29 统计量, 异常值主导机制详解
3. **§2.2 Mechanics**: GMP 交换律证明 Mean(A,B)=Mean(B,A), RPB 梯度死因链
4. **§2.3 全新**: Phase 6 退化完整链 IC 0.066→0.028, D9-D0=-5.92 BP, 全局排序伪信号
5. **§3 MANDATE B.2**: 残差格式从 `x+tda(x)` 改为 `LayerNorm(x+tda(x))` (Post-LN)
   - ⚠️ **与 Codex+Gemini 审计冲突**: spec [FINAL] 选择了 Pre-LN `x+tda(LN(x))`
6. **§3 MANDATE B.3**: **Shatter Window Isolation** — 5个32-bar隔离窗口限制0.64天感受野, 需跨窗注意力
7. **NEXT ACTION**: 64-sample Crucible Overfit Test, loss→0.0 通过标准

### V2 删除/简化的内容:
- V1 §2 Decision 3 (GMP with IC vs MSE analysis) — 合并入 §2.2
- V1 §2 Decision 5 (strict=False re-verification) — 合并入 §2.3 ("All historical baselines invalidated")
- V1 §2 Decision 6 (capacity) — 合并入 §2.2
- V1 §3.3 "Positional Encodings: sinusoidal/RoPE" option — 替换为仅 "debug RPB" (spec 已采纳)
- V1 §3.3 "Flatten+Linear Projection" pooling option — 移除 (Gemini 审计判为过拟合)
