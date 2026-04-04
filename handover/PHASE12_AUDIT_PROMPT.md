# Phase 12 审计入场指令

> 本文档是递交给外部审计 AI Agent 的完整 briefing。包含入口路径、问题清单、数据证据、和待裁决疑问。

---

## 一、入口路径

```
1. 读本文件                                          ← 你在这里
2. 读 handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md      ← 11 轮外部审计完整报告（含数据表、诊断、6 个裁决问题）
3. 读 architect/current_spec.yaml                    ← 权威架构规范（张量、物理常数、训练参数）
4. 读核心代码（按需）:
   - omega_epiplexity_plus_core.py                   ← 数学核心（~255 行）
   - train.py                                        ← 训练循环（~800 行，重点看 OmegaTIBWithMasking.forward 和 compute_spear_loss）
   - backtest_5a.py                                  ← 推理+统计测试（~310 行）
5. 历史对比: architect/INDEX.md                       ← 37 条指令时间线，追溯 Loss 函数演变
```

---

## 二、Phase 12 做了什么

**目标**: 解决 Phase 11 的方差坍缩（pred_std=5.64 BP，模型输出常数）。

**方案**: Unbounded Spear — Scaled MSE + Static Centering + Leaky Blinding（架构师指令 INS-057~064）。

**训练配置**: 20 epochs, hidden_dim=64, window=(32,10), lambda_s=1e-4, batch=256, lr=3.2e-4, T4 GPU on-demand。

**训练结果**: SUCCEEDED。Best D9-D0=+4.48 BP at E0, final E19 D9-D0=+1.28 BP。

**Post-flight 结果**: 1,904,747 samples, 5,200 symbols, 399 val shards → **NOT TRADEABLE**。

---

## 三、核心数学问题（11 轮外部审计暴露）

### 问题 1: 模型在预测波动率，不是 Alpha

**证据**:

| Decile | mean_pred (BP) | mean_target (BP) | hit_rate |
|--------|---------------|-----------------|----------|
| D0 (最差) | -9.04 | +4.53 | **51.4%** |
| D9 (最好) | +84.12 | +9.04 | **49.0%** |

- D9（模型最看好的股票）的胜率 (49.0%) **低于** D0 (51.4%)
- 但 D9 的 mean_target (9.04) 高于 D0 (4.53) — 因为 D9 是高波动股（大涨大跌），均值被肥右尾拉高
- **Gemini 数学证明**: Leaky Blinding (负收益×0.1) 将负收益梯度压缩 **100 倍** (0.1²)。模型被数学激励去忽略负收益，只追高波动

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.1（Gemini Item 7: Decile Anomaly）

### 问题 2: pred_mean 完美收敛到错误目标

**证据**:

```
Leaky Blinding 后目标期望值:
  E[T_leaky] = 0.5 × E[T|T>0] + 0.5 × 0.1 × E[T|T<0]
             = 0.5 × 158.6 + 0.5 × 0.1 × (-144.6)
             = 79.3 - 7.23 = 72.07 BP
  
  居中后: E[T_centered] = 72.07 - 40.0 = +32.07 BP

实测 pred_mean = +34.42 BP  ←  精确匹配 32.07 (误差 7%)
```

模型没有 stuck，它完美学到了变换后目标的均值。**但这个均值不是 Alpha，是 Leaky Blinding 制造的人工偏移。**

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.1（Gemini Item 5: Path A Centering Bias）

### 问题 3: Rank IC 在 29σ 显著为负

**证据**:

```
Spearman Rank IC = -0.0206
标准误 = 1/√(1,904,747) = 0.000725
Z-score = -0.0206 / 0.000725 = -28.4σ
```

这不是噪声。模型的排序能力**系统性地比随机差**。它在一致性地反向排序。

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.1（Gemini Item 2: Negative Rank IC）

### 问题 4: MSE 在高方差目标下退化为条件均值预测

**证据**:

```
target: mean=6.93 BP, std=189.60 BP
signal (D9-D0): 4.51 BP
SNR = 4.51 / 189.60 = 0.024 (2.4%)
```

MSE 梯度 ∝ (pred - target)。当 target 方差 (190 BP) >> 信号 (4.5 BP) 时，MSE 被方差主导，模型退化为拟合条件均值（最小化方差贡献），无法学排序。

**对比**: Phase 6 用 IC Loss（直接优化排序）→ IC=0.066。Phase 12 用 MSE → IC=0.005。**IC Loss 表现好 13 倍。**

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.1（Gemini Item 4: MSE vs Ranking）+ §六（Codex Architecture Item 3）

### 问题 5: MDL 压缩杀信号

**证据**:

| 指标 | E0 (lambda_s=0) | E19 (lambda_s=1e-4) |
|------|-----------------|---------------------|
| D9-D0 | 4.51 BP | 1.29 BP |
| Pearson IC | 0.0046 | 0.0001 |
| z_sparsity | 5.4% | 18.5% |

D9-D0 从 E0→E19 **单调下降**。MDL 的 L1 正则化在压缩 z_core 的同时杀死了仅有的微弱判别信号。

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §二（E0 vs E19 对比表）

---

## 四、核心模型问题（Vertex AI 实测 + Codex 静态分析）

### 问题 6: Global Mean Pooling 摧毁时空结构

**证据**:

```python
# omega_epiplexity_plus_core.py:183
pooled_z = torch.mean(z_core, dim=[1, 2])  # [B, 160, 10, 16] → [B, 16]
```

160 个时间步 × 10 个空间深度 = 1,600 个 token，全部平均为 16 个数字。对立模式相互抵消。模型输出的预测只基于 16 个均值——时间序列模式、空间结构全部丢失。

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.3（Codex: CRITICAL — Global mean pooling）

### 问题 7: TDA 位置编码梯度极弱，形同虚设

**证据**（Vertex AI 实测 gradient flow check）:

```
intent_decoder.bias:              grad_norm = 4811      ← 最强
bottleneck.2.bias:                grad_norm = 3145
tda_layer.qkv.weight:            grad_norm = 498
tda_layer.rpb_table:              grad_norm = 0.08      ← 比 decoder 弱 60,000x
```

RPB（Relative Position Bias）是 TDA 的核心可学习参数（4,788 params, 占模型 20%），控制"哪个时间步关注哪个时间步"。梯度 0.08 意味着这些参数在训练中几乎不更新——**注意力的时空位置编码形同虚设**。

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.2（Gradient Flow Check）

### 问题 8: 5 个窗口完全隔离，跨窗口模式不可学

**证据**:

```
Input: [B, 160, 10, 10]
Window: (32, 10)
时间: 160 / 32 = 5 个窗口
空间: 10 / 10 = 1 个窗口

窗口间无交互: 无 shifted window, 无第二层 attention, 无跨窗口混合器
```

如果机构建仓信号跨越 32 bars（~0.64 交易日），模型**结构上不可能捕捉**。感受野硬顶 32 bars。

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.3（Codex: HIGH — No global token mixing）

### 问题 9: 无残差连接

**证据**:

```python
# train.py:239 (实际训练路径)
structured_features = self.model.tda_layer(x)     # 直接替换，无 x + tda(x)
z_core = self.model.epiplexity_bottleneck(structured_features)
```

标准 Transformer: `out = x + attention(x)`。本模型: `out = attention(x)`。模型必须通过 attention 学恒等映射才能保留原始特征。

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.3（Codex: MEDIUM — No residual path）

### 问题 10: Overfit Test 不完美

**证据**（Vertex AI 实测，1 batch × 2000 步，lambda_s=0）:

```
Step    0: Loss = 8.35
Step  200: Loss = 0.21  (-97%)
Step 1000: Loss = 0.096
Step 2000: Loss = 0.073  ← 未归零
```

24,437 参数模型记忆 64 个样本 2000 步后 loss 仍为 0.073。模型**能学**（下降 99%），但**记忆不彻底**。瓶颈可能在 global mean pooling 的信息丢失。

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.1（Overfit Test）

### 问题 11（NEW）: D9-D0 验证指标是全局排序，非截面排序

**证据**:

```python
# train.py:484-488
n_samples = preds.numel()        # 所有日期混在一起
k = max(n_samples // 10, 1)
_, top_idx = torch.topk(preds, k)  # 全局 top 10%
```

如果策略是每日 rebalance（截面选股），正确做法是按日期分组，每个日期内部排序，然后聚合 D9-D0。当前全局排序可能**高估或低估**真实截面判别力。

**审计源**: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §六（Codex Architecture: BONUS CRITICAL）

---

## 五、已确认无问题的部分

以下经 11 轮外部审计确认正确:

- ✅ **代码无 bug**: Forward pass 4 路一致（FRT/SRL/symlog/LayerNorm 全部对齐）
- ✅ **Gradient flow**: 全 14 个参数组梯度非零
- ✅ **Checkpoint 加载**: `_orig_mod.` strip 修复后 keys=15, missing=[] 
- ✅ **Spec-code 对齐**: 所有训练参数与 spec 一致（lambda_s/static_mean/outlier_clamp/mse_scale/leaky_factor）
- ✅ **物理公理**: δ=0.5 不可变，c_default=0.842
- ✅ **数据管线**: target 从 ETL 到 Loss 全程 BP 单位，无 double-scaling
- ✅ **torch.compile bug 已修复**: save 端 strip + load 端防御性 strip + 诊断日志

---

## 六、待裁决的核心疑问

### Q1: Leaky Blinding 是否必须删除？

Gemini 证明它导致模型预测波动率。但架构师设计 Leaky Blinding 的原因是"A 股做空受限，负收益多为散户恐慌非机构行为"（INS-060）。

**数据**: 删除 leaky blinding 会让模型面对完整的负收益梯度，MSE 对 -500 BP 跌停板的惩罚将与 +500 BP 涨停板等量。这对检测**买方机构**是否合理？

### Q2: 要回到 IC Loss 吗？

Phase 6 IC=0.066 是历史最高（13x Phase 12）。但架构师废弃 IC Loss 的原因是"预测绝对尺度极小"（INS-018），导致回测时信号量级不够。

**数据**: Phase 6 best trial T29 的 pred 量级在 1e-4 级别，需要极精确的阈值才能做交易决策。IC Loss 优化排序但不优化尺度——这对实际交易是否是问题？

### Q3: Global Mean Pooling vs 什么？

两路 Codex 都判 CRITICAL。但 Phase 6 **同一架构**（包括 mean pooling）达到 IC=0.066。

**疑问**: 如果 mean pooling 是瓶颈，Phase 6 为什么成功？是因为 IC Loss 恰好与 mean pooling 兼容（IC 是排序指标，对绝对位置不敏感），而 MSE 不兼容（MSE 需要精确的绝对值预测）？

### Q4: -29σ 的 Rank IC 是反信号还是特征反转？

Gemini 提出 FRT（Financial Relativity Transform）可能反转了信号方向：机构建仓造成短期价格冲击（正向），但 FRT 归一化后变成相对值，如果市场存在短期均值回复，模型可能在学回复而非延续。

**数据**: 如果把 Rank IC 取反（即做空模型看好的、做多模型看差的），D9-D0 变成 -4.51 BP，仍不覆盖 25 BP 成本。单纯反转不解决问题。

### Q5: torch.compile bug 是否污染了历史基准？

Phase 12 之前的推理可能都受 `_orig_mod.` bug 影响（`strict=False` 静默跳过所有权重）。

**疑问**: Phase 11c 的 D9-D0=8.90 BP 和 Phase 6 的 IC=0.066 是否需要用修复后代码重新验证？如果历史基准不可信，我们对"哪个 Loss 最好"的判断也不可信。

### Q6: 19.7K→24.4K 模型是否容量不足？

Codex 认为容量足够（Phase 6 同架构 IC=0.066）。但 Gemini 指出 SNR=2.4% 的信号需要精细提取，24.4K 参数中 87% (21,236) 在 TDA 层，而 TDA 的 RPB 梯度极弱。

**疑问**: 有效容量可能远小于 24.4K。如果 TDA 20% 参数（RPB）形同虚设，模型实际有效参数只有 ~19.6K。这够吗？

---

## 七、附录：数据资产位置

```
# Post-flight predictions (可直接加载做分析)
gs://omega-pure-data/postflight/phase12_val_predictions.parquet          # E0 best.pt
gs://omega-pure-data/postflight/phase12_latest_val_predictions.parquet   # E19 latest.pt

# Checkpoints
gs://omega-pure-data/checkpoints/phase12_unbounded_v1/best.pt           # E0, D9-D0=4.48
gs://omega-pure-data/checkpoints/phase12_unbounded_v1/latest.pt         # E19

# Training log
gs://omega-pure-data/checkpoints/phase12_unbounded_v1/train.log

# Docker image (含修复后代码)
us-central1-docker.pkg.dev/gen-lang-client-0250995579/omega-training/omega-tib:phase12-postflight-v1

# Overfit test
gs://omega-pure-data/checkpoints/phase12_overfit_test/
```

---

*Prepared: 2026-04-04. 11 rounds external audit (Codex×8 + Gemini×3) + Vertex AI实测。*
*All findings traceable to audit source in `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md`.*
