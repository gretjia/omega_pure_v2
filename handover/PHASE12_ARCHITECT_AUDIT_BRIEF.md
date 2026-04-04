# Phase 12 架构师审计简报
**Date**: 2026-04-04
**Prepared by**: Claude (Coding Partner) + 11 轮外部审计 (Codex × 8 + Gemini × 3) + Vertex AI 实测

---

## 一、本轮做了什么

### 1. 全链外部审计（Ω5 合规）
在进入 post-flight 前，对所有代码进行了 8 轮独立外部审计：
- **Codex**: Core model 正确性 / Spec-code 对齐 / Train-serve skew / 指令合规 / 修复验证 / torch.compile 验证
- **Gemini**: 数学正确性 / 修复数学验证

**审计结论**: 活跃路径代码全部合规。发现并修复了 **torch.compile `_orig_mod.` 静默加载 bug** — 这是一个 CRITICAL 级别的发现，可能是历次"训练成功推理失败"的根因。

### 2. Phase 12 Post-Flight 双模型推理
- **E0 (best.pt)**: MDL 未激活，D9-D0=4.48 BP（训练时 val 最优）
- **E19 (latest.pt)**: MDL 激活后 18 个 epoch，z_sparsity 从 5.4%→18.5%
- 两者均在 Vertex AI T4 GPU 上完成 1.9M 样本推理

---

## 二、Post-Flight 核心数据

### 十分位表（E0 best.pt, 1,904,747 samples, 5,200 symbols）

| Decile | N | mean_pred (BP) | mean_target (BP) | hit_rate | IC |
|--------|------|---------------|-----------------|----------|--------|
| D0 | 190,492 | -9.04 | **4.53** | 51.4% | 0.0160 |
| D1 | 190,668 | 7.01 | 6.62 | 51.0% | 0.0051 |
| D2 | 190,424 | 15.75 | 7.45 | 50.3% | -0.0018 |
| D3 | 190,777 | 22.91 | 6.41 | 49.5% | -0.0001 |
| D4 | 190,456 | 29.58 | 6.64 | 49.3% | 0.0001 |
| D5 | 190,616 | 36.30 | 7.20 | 49.2% | -0.0012 |
| D6 | 190,283 | 43.48 | 7.26 | 49.1% | 0.0007 |
| D7 | 190,598 | 51.72 | 7.28 | 49.0% | 0.0023 |
| D8 | 190,029 | 62.46 | 6.86 | 48.6% | -0.0025 |
| **D9** | 190,404 | **84.12** | **9.04** | 49.0% | -0.0005 |

**D9-D0 Spread = 4.51 BP** | **Monotonicity = 7/9** | **Cost = 25 BP** | **NOT COVERED**

### 关键指标对比

| 指标 | E0 (best.pt) | E19 (latest.pt) | Phase 11c | Phase 6 (IC Loss) |
|------|-------------|-----------------|-----------|-------------------|
| pred_std | 26.61 BP | 18.57 BP | 5.64 BP | — |
| D9-D0 | 4.51 BP | 1.29 BP | 8.90 BP | — |
| Pearson IC | 0.0046 | 0.0001 | 0.0210 | 0.066 |
| Spearman Rank IC | **-0.0206** | **-0.0297** | — | — |
| z_sparsity | 5.4% | 18.5% | — | — |
| Corr(z_sp, |pred|) | -0.001 | +0.225 | -0.22 | — |

---

## 三、诊断分析

### 3.1 Unbounded Spear 解决了什么
✅ **方差坍缩已治愈**: pred_std 从 Phase 11c 的 5.64 BP 恢复到 26.61 BP
✅ **模型不再是常数预测器**: pred 范围 [-95, +226] BP，有实质性变异
✅ **MDL 压缩生效**: z_sparsity 从 E0 的 5.4% 升至 E19 的 18.5%

### 3.2 Unbounded Spear 没解决什么
❌ **排序能力比随机差**: Spearman Rank IC = -0.02 (负值意味着反向排序)
❌ **D9-D0 从 Phase 11c 退步**: 8.90 → 4.51 BP (虽然 Phase 11c 用旧代码也有问题)
❌ **MDL 杀信号**: D9-D0 从 E0→E19 单调下降 (4.51 → 1.29)

### 3.3 根因假说

**假说 A: SRL 物理信号被 Leaky Blinding + Static Centering 扭曲**
- target 经过 leaky(0.1x for negatives) + centering(-40) 后，分布严重变形
- 模型在拟合一个人工扭曲的目标，而非真实收益分布
- 证据: D0 (模型最不看好的) 实际收益 +4.53 BP，与 D9 (+9.04) 差距很小

**假说 B: MSE 本质不适合排序任务**
- Phase 6 用 IC Loss 达到 IC=0.066，是目前最高
- 所有后续 Phase (MSE/Huber/Softmax/Unbounded MSE) IC 都在退步
- MSE 惩罚绝对误差，但交易只关心排序——IC Loss 才是排序原生的

**假说 C: 19.7K 参数模型在 Unbounded MSE 下无法同时学尺度和排序**
- pred_mean=34.42 BP vs target_mean=6.93 BP — 模型预测偏高 5x
- 模型在努力匹配 centered target 的均值（0 附近），但牺牲了排序质量
- Path A (只居中 target) 强迫模型输出 Excess BP，但可能梯度信号被均值拟合主导

**假说 D (最关键): torch.compile bug 污染了历次基准**
- Phase 12 之前的所有推理/回测可能都受 `_orig_mod.` bug 影响
- 这意味着 Phase 11c 的 D9-D0=8.90 可能也是随机权重的结果
- 需要用修复后的代码重新跑历史最佳 checkpoint 的 post-flight

---

## 四、代码健康状态（审计确认）

### 已修复的全部问题

| 编号 | 问题 | 严重度 | 状态 |
|------|------|--------|------|
| F-12 | torch.compile `_orig_mod.` 静默加载失败 | CRITICAL | ✅ 修复+验证 |
| C1 | backtest defaults 不匹配训练配置 | CRITICAL | ✅ 修复 |
| C4 | pred_bp 缺少 ×10000 | CRITICAL | ✅ 修复 |
| H1 | SRL overflow 无 clamp | HIGH | ✅ 修复 |
| H2 | costs_bp 15→25 | HIGH | ✅ 修复 |
| L1-5 | 死代码清理 + 默认值对齐 | LOW | ✅ 修复 |
| SYNC | gcp/ 目录同步 | HIGH | ✅ 修复 |

### Spec-Code 对齐状态
- ✅ 所有物理常数（δ=0.5, c_default=0.842）
- ✅ Loss 函数（Unbounded Spear 全参数）
- ✅ 张量形状（[B, 160, 10, 10]）
- ✅ 训练参数（lambda_s=1e-4, static_mean_bp=40.0 等）
- ⚠️ epochs: YAML=20 vs spec=15（无害偏差）

---

## 五、模型基础健康检查（Vertex AI 实测 + Codex 静态分析）

### 5.1 Overfit Test（Vertex AI T4, 1 batch × 2000 步, lambda_s=0）

| Step | Loss | 观察 |
|------|------|------|
| 0 | 8.35 | 起始 |
| 200 | 0.21 | -97% 快速下降 |
| 1000 | 0.096 | 继续下降 |
| 2000 | **0.073** | **未归零** — 64 样本记忆不彻底 |

**结论**: 模型能学（loss 下降 99%），但 24.4K 参数模型 2000 步仍无法完美记忆 64 个样本。瓶颈可能在 global mean pooling (160×10→1) 导致的信息丢失。

### 5.2 Gradient Flow Check（合成数据，全 14 个参数组）

```
intent_decoder.bias:              grad_norm = 4811      [OK] ← 最强
bottleneck.2.bias:                grad_norm = 3145      [OK]
bottleneck.2.weight:              grad_norm = 730       [OK]
bottleneck.0.bias:                grad_norm = 715       [OK]
bottleneck.0.weight:              grad_norm = 588       [OK]
tda_layer.qkv.weight:            grad_norm = 498       [OK]
tda_layer.proj.weight:            grad_norm = 474       [OK]
tda_layer.proj.bias:              grad_norm = 336       [OK]
input_proj.weight:                grad_norm = 165       [OK]
post_proj_norm.bias:              grad_norm = 118       [OK]
post_proj_norm.weight:            grad_norm = 40        [OK]
input_proj.bias:                  grad_norm = 0.06      [OK]
tda_layer.rpb_table:              grad_norm = 0.08      [OK] ← 极弱！
```

**GRADIENT FLOW: ALL 14 PASS — 无死参数。**

**但 RPB（相对位置偏置表）梯度仅 0.08 — 比 decoder 弱 60,000x。**
这是 TDA 层的核心可学习参数（1197 entries × 4 heads = 4788 params, 占模型 20%），却几乎不更新。意味着 **注意力的空间-时间位置编码在训练中形同虚设**。

### 5.3 模型架构结构性限制（Codex 静态分析）

| 发现 | 严重度 | 详情 |
|------|--------|------|
| **5 窗口完全隔离** | HIGH | 160 步 ÷ 32 = 5 个窗口，窗口间 token 永不交互。时间感受野硬顶 32 bars (~0.64 天)。无 shifted window、无第二层、无跨窗口混合器 |
| **无残差连接** | MEDIUM | `structured = tda(x)` 直接替换输入，无 `x + tda(x)`。模型必须通过 attention 学恒等映射才能保留原始特征 |
| **Global mean pooling** | CRITICAL | `torch.mean(z_core, dim=[1,2])` 将 [B,160,10,16] 压成 [B,16]。对立模式相互抵消，时序/空间结构全部丢失 |
| **24,437 参数分布** | INFO | input_proj 448 + LayerNorm 128 + TDA 21,236 (87%) + bottleneck 2,608 + decoder 17 |

### 5.4 Output Sanity

```
pred:   shape=[4,1], mean=0.2405, std=0.0004  — raw logit 合理
z_core: shape=[4,160,10,16], mean=0.018, std=0.097, sparsity=9.3% — 瓶颈激活正常
```

### 5.5 综合诊断

**模型本身没有 bug**。梯度流完整，所有参数都在更新，能学（loss 下降 99%）。

但存在 **四个结构性限制** 导致信号无法转化为排序能力：

1. **Loss 目标被 Leaky Blinding 扭曲** → 模型预测波动率而非 Alpha（Gemini 证明）
2. **MSE 无法学排序** → target std=190 >> signal=4.5 时退化为均值预测
3. **Global mean pooling** → 160×10 流形被压成 16 个均值，时空结构全丢
4. **TDA RPB 梯度极弱** → 注意力的位置编码形同虚设，20% 参数被浪费

---

## 六、三路全盘审计汇总（第二轮：Codex ×2 + Gemini ×1）

### Gemini 数学审计（7 项，4 CRITICAL）

| 项目 | 判定 | 核心发现 |
|------|------|----------|
| SNR | PASS | 4.51/189.6 = 2.4% SNR，1.9M 样本足够检测（需 136K） |
| Rank IC 负值 | **CRITICAL** | -0.02 在 29σ 显著，系统性反向排序 |
| Leaky Blinding | **CRITICAL** | 负收益梯度被压缩 100x，模型忽略负收益 → 预测波动率 |
| MSE vs 排序 | **FAIL** | MSE 在高方差下退化为条件均值预测，不学排序 |
| Path A 偏差 | **CRITICAL** | pred_mean=34.42 精确匹配变换目标期望 32.07 — 模型完美收敛到错误目标 |
| Epiplexity | FAIL | z_core 活跃但与预测无关 — 瓶颈传递噪声 |
| Decile 异常 | **CRITICAL** | D9 hit_rate < D0 hit_rate — 模型选高波动股，不是高收益股 |

### Codex 架构审计（8 项 + 1 BONUS）

| 项目 | 严重度 | 核心发现 |
|------|--------|----------|
| 模型容量 | LOW | 24.4K 足够（Phase 6 同架构 IC=0.066） |
| 信息流 | HIGH | FRT 删除绝对价格，可能丢失有用信息 |
| Loss vs 任务 | **CRITICAL** | MSE 优化绝对误差，任务需要排序 |
| Static centering | LOW | 无害（40/190 = 21%） |
| Leaky blinding | HIGH | 90% 压缩负收益 → 短侧分离被摧毁 |
| 空间窗口 | LOW | ws=10 全深度合理 |
| **Global mean pooling** | **CRITICAL** | 160×10 → 16 均值，时空结构全丢 |
| Phase 6 对比 | HIGH | IC Loss 历史最佳，建议 Rank Loss + 小 MSE 锚定 |
| **验证指标全局排序** | **CRITICAL** | D9-D0 混合所有日期排序，非截面排序 |

### Codex 全盘代码审计（A-G 7 个维度）

| 维度 | 判定 | 发现 |
|------|------|------|
| A: Forward 一致性 | **FAIL** | Core bare forward (无 FRT) 被 v3_smoke_test.py 调用 |
| B: Checkpoint 流 | WARNING | phase7_inference.py 未强制检查 missing_keys |
| C: Loss 函数 | WARNING | 实现正确，但 PfRet 使用 raw logit 做 weight |
| D: D9-D0 实现 | PASS | topk on raw logits 排序正确 |
| E: 数据管线 | WARNING | phase7 手动预处理 vs loader 的 dynamic_processor 不一致 |
| F: 信号丢失嫌疑 | WARNING | Global mean pooling 最可疑 |
| G: 回归检查 | PASS | 无遗留危险代码 |

---

## 七、请架构师裁决

### 问题 1: Leaky Blinding 必须删除还是修改？
Gemini 数学证明：leaky(0.1x) 导致模型预测波动率而非 Alpha。D9 选的是高波动股（hit_rate=49%），不是高收益股。三个选项：
- (A) 完全删除 leaky blinding，使用原始 target
- (B) 对称变换：rank normalization（最推荐，消除量纲问题）
- (C) 对称 clamp（如 ±500 BP，不区分正负）

### 问题 2: 要回到 IC Loss 还是混合 Loss？
Phase 6 IC Loss → IC=0.066（历史最高）。所有后续 MSE 系列 IC ≤ 0.005。但架构师废弃 IC Loss 的原因是"预测绝对尺度极小"（INS-018）。三个选项：
- (A) 纯 IC Loss（回到 Phase 6 范式）
- (B) IC Loss + 小权重 MSE 锚定尺度（Codex 推荐）
- (C) ListMLE / Pairwise Margin Loss（排序任务标准方案）

### 问题 3: Global Mean Pooling 要换什么？
两路 Codex + Gemini 一致认为 mean pooling 是信号丢失主因。选项：
- (A) Last-N temporal pooling（只看最后 N bars 的均值）
- (B) Temporal attention pooling（可学习的时间聚合）
- (C) Max pooling（保留最强信号，不抵消）

### 问题 4: TDA 窗口隔离要修复吗？
5 个 32-bar 窗口完全隔离，跨窗口模式结构上不可学。RPB 梯度仅 0.08（形同虚设）。选项：
- (A) 加 shifted window（Swin-style，偶数层平移半窗口）
- (B) 加第二层 attention（全局 attention 或更大窗口）
- (C) 增加残差连接 x + attention(x)
- (D) 暂不改（Phase 6 同架构达到 IC=0.066，说明不是根本限制）

### 问题 5: D9-D0 验证指标要改为截面排序吗？
当前按全局混合日期排序。如果策略是每日 rebalance，应改为按日期截面排序后聚合。这可能改变"哪个 epoch 最优"的判断。

### 问题 6: 需要用修复后代码重跑历史 checkpoint 吗？
torch.compile `_orig_mod.` bug 可能导致历次推理结果都是随机权重。建议用修复后代码重跑 Phase 6/11c 的 best.pt，确认历史基准可信度。

---

## 六、附录

### 数据资产位置
- E0 predictions: `gs://omega-pure-data/postflight/phase12_val_predictions.parquet`
- E19 predictions: `gs://omega-pure-data/postflight/phase12_latest_val_predictions.parquet`
- Checkpoints: `gs://omega-pure-data/checkpoints/phase12_unbounded_v1/{best,latest}.pt`
- 训练日志: `gs://omega-pure-data/checkpoints/phase12_unbounded_v1/train.log`

### 推理配置
- Docker: `omega-tib:phase12-postflight-v1`
- GPU: T4 (Vertex AI n1-standard-8)
- Mode: val-only (399 shards, 1.9M samples, 5200 symbols)
- I/O: GCS FUSE 直读 (Gemini 推荐, 替代 pipe:gcloud)
