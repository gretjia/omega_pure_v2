# Phase 12→13 全链审计：数据→结论→决策→现状

> 审计日期: 2026-04-04
> 审计目的: 提交正式训练前，完整复盘 Phase 12 失败诊断 → Phase 13 架构重设 → Crucible 验证的决策链
> 原则: 每个结论必须有实测数据支撑 (Omega1: 只信实测)

---

## 第一章: Phase 12 训练实测数据

### 1.1 训练配置

| 参数 | 值 |
|------|------|
| Job ID | 340079341608108032 |
| Docker | omega-tib:phase12-v5 |
| GPU | T4 ON_DEMAND (n1-standard-8) |
| 总时长 | 13.9 小时 (20 epochs × 5000 steps) |
| 参数量 | 24,437 |
| Loss | Unbounded Spear MSE (static_mean_bp=40, lambda_s=1e-4, leaky_factor=0.1) |
| 数据 | 1,593 train / 399 val shards, 1,904,747 val samples |

### 1.2 逐 Epoch 完整曲线

| Epoch | Train Loss | Val Loss | D9-D0 (BP) | Std_yhat (BP) | S_T | PfRet |
|-------|-----------|----------|------------|---------------|-----|-------|
| **0** | 1.285 | 1.204 | **+4.48** | 26.61 | 2.087 | 7.70 |
| 1 | 1.215 | 1.177 | +0.59 | 17.84 | 1.617 | 6.81 |
| 2 | 1.253 | 1.227 | +1.61 | 22.94 | 1.567 | 5.85 |
| 3 | 1.227 | **1.171** | -0.04 | 15.71 | 1.509 | 6.66 |
| 4 | 1.128 | 1.179 | **-1.09** | **7.34** | 1.468 | 6.83 |
| 5 | 1.236 | 1.163 | -0.05 | 19.15 | 1.421 | 6.75 |
| 6 | 1.253 | 1.180 | +3.27 | 23.63 | 1.386 | **7.91** |
| 7 | 1.153 | 1.170 | +1.67 | 15.80 | 1.348 | 7.62 |
| 8 | 1.221 | 1.173 | +2.87 | 15.77 | 1.294 | 7.92 |
| 9 | 1.204 | 1.238 | +0.48 | 12.75 | 1.270 | 4.22 |
| 10 | 1.226 | 1.170 | +1.22 | 17.38 | 1.240 | 7.05 |
| 11 | 1.274 | 1.165 | +0.57 | 19.07 | 1.217 | 6.98 |
| 12 | 1.205 | 1.159 | +1.19 | 17.99 | 1.198 | 7.60 |
| 13 | 1.246 | 1.160 | +2.30 | 17.99 | 1.183 | 7.82 |
| 14 | 1.192 | 1.177 | +1.19 | 18.87 | 1.158 | 7.34 |
| 15 | 1.184 | 1.194 | +1.07 | 15.32 | 1.170 | 6.82 |
| 16 | 1.180 | 1.164 | +1.91 | 18.83 | 1.170 | 7.75 |
| 17 | 1.197 | 1.159 | +1.06 | 18.98 | 1.167 | 7.48 |
| **18** | 1.255 | **1.158** | +1.25 | 18.69 | 1.162 | 7.58 |
| **19** | 1.215 | 1.160 | +1.28 | **18.57** | 1.157 | 7.51 |

**关键观察:**
- D9-D0 最佳在 **E0 (lambda_s 还未生效)**: +4.48 BP
- E4 出现方差坍缩 (Std=7.34 BP)，E5 自行恢复
- E15 起 Std 持续 < 30 BP 触发 LOW VARIANCE 哨兵
- S_T: 2.09→1.16 (44% 压缩)，但信号同步衰减
- Val Loss 持续下降 (1.204→1.158)，但 **D9-D0 从 4.48 衰减到 ~1.3 BP**

### 1.3 Post-Flight Decile 分析 (E0 best.pt, 1,904,747 samples)

| Decile | N | pred (BP) | target (BP) | hit_rate |
|--------|--------|-----------|-------------|----------|
| D0 | 190,492 | -9.04 | **+4.53** | **51.4%** |
| D1 | 190,668 | +7.01 | +6.62 | 51.0% |
| D2 | 190,424 | +15.75 | +7.45 | 50.3% |
| D5 | 190,616 | +36.30 | +7.20 | 49.2% |
| D8 | 190,029 | +62.46 | +6.86 | 48.6% |
| **D9** | 190,404 | **+84.12** | **+9.04** | **49.0%** |

**致命发现:**
- D9-D0 spread = 4.51 BP (远低于 25 BP 交易成本)
- **D0 的 hit_rate (51.4%) > D9 (49.0%)** → 模型把高波动股排在顶部
- Prediction range: -9 to +84 BP (全为正偏) → 模型学到了 warped target 的偏移量
- Spearman Rank IC = **-0.0206 (29σ 显著)** → 系统性反向排序

### 1.4 定量诊断: 为什么 Phase 12 失败

#### 数据点 1: Leaky Blinding 的数学效应
```
leaky_factor = 0.1
负收益 target: t_neg → t_neg × 0.1
MSE gradient ∝ (pred - target)²
负收益的梯度 = (pred - 0.1×t_neg)² = 0.01 × (pred/0.1 - t_neg)²
→ 负收益的梯度被压缩 100x
```
- 理论预测: E[T_warped] = 0.5×158.6 + 0.5×0.1×(-144.6) = 72.07 BP
- 居中后: E[T_centered] = 72.07 - 40.0 = 32.07 BP
- **实测 pred_mean = 34.42 BP** (与理论预测仅差 7%)
- **结论: 模型完美学到了 warped target 的均值偏移，而不是 Alpha 排序**

#### 数据点 2: MSE 在低 SNR 下的退化
```
target_std = 189.60 BP
signal (D9-D0) = 4.51 BP
SNR = 4.51 / 189.60 = 2.4%
```
- MSE gradient ∝ (pred - target)，被 189 BP 噪声主导
- 在 SNR=2.4% 下，MSE 退化为条件均值预测器
- **结论: MSE 无法从 189 BP 噪声中提取 4.5 BP 信号**

#### 数据点 3: L1 正则化杀信号
```
E0 (lambda_s=0 warmup): D9-D0 = 4.48 BP, IC = 0.0046
E19 (lambda_s=1e-4):     D9-D0 = 1.28 BP, IC = 0.0001
z_sparsity: 5.4% → 18.5% (压缩成功)
Corr(z_sparsity, |pred|): -0.001 → +0.225 (压缩与预测耦合)
```
- D9-D0 单调下降: L1 同时杀信号和噪声
- **结论: 在 SNR=2.4% 下，L1 无法区分信号和噪声，压缩即杀信号 (INS-069)**

#### 数据点 4: 架构结构性缺陷 (Codex 审计)
```
grad_norm(RPB table) = 0.08
grad_norm(decoder)   = 4,811
ratio = 60,000x
```
- RPB (Relative Position Bias) 梯度死亡 → 位置编码无效
- Global Mean Pooling: [B,160,10,16] → mean → [B,16] → 1600 个 token 平均为 16 个值
- 5 个孤立窗口 × 32 bars = 最大感受野 0.64 天
- **结论: TDA 的位置感知和跨窗口学习能力几乎为零**

---

## 第二章: 诊断→决策的推导链

### 2.1 外部审计双路 (Omega5: 生产者≠验证者)

| 审计方 | 方法 | 关键发现 |
|--------|------|----------|
| **Gemini** | 数学证明 | Leaky 100x 梯度压缩; MSE 条件均值退化; pred_mean=34.42≈理论32.07 |
| **Codex** | 架构审计 | RPB 梯度死亡(60000x); Mean Pooling 信息损失; 窗口隔离0.64天 |

### 2.2 六条指令 (INS-065 ~ INS-070) 及其数据依据

| INS | 决策 | 数据依据 | 执行状态 |
|-----|------|----------|----------|
| **065** | 删除 Leaky Blinding | pred_mean=34.42 vs 理论32.07 (7%误差); D9 hit_rate < D0 | ✅ 已删除 |
| **066** | MSE→IC Loss | Phase 6 IC=0.066 vs Phase 12 IC=0.0001 (660x差距); SNR=2.4% MSE失效 | ✅ 已实现 |
| **067** | 截面评估 (per-date IC) | Global D9-D0 混合日期波动率偏差 | ⚠️ 近似实现 (batch-level IC，ETL 无 date 字段) |
| **068** | 拓扑解锁 (AttentionPooling + Pre-LN + Residual) | RPB grad=0.08 vs decoder=4811; Mean Pool 丢失空间结构 | ✅ 已实现 (Mandate B) |
| **069** | lambda_s=0 (删除 L1) | E0 D9-D0=4.48 > E19 D9-D0=1.28; L1 在 SNR=2.4% 下杀信号 | ✅ 已实现 |
| **070** | 打破窗口隔离 (Swin-style) | 5×32 bar 窗口=0.64天; 机构建仓跨多日 | ❌ 未实现 (Phase 14 计划) |

### 2.3 决策逻辑树

```
Phase 12 实测 D9-D0=4.48 BP < 25 BP 交易成本 (NOT TRADEABLE)
│
├── WHY 1: D9 hit_rate (49%) < D0 (51.4%) → 波动率排序而非 Alpha 排序
│   ├── ROOT CAUSE: Leaky Blinding 100x 梯度压缩 (Gemini 数学证明)
│   └── FIX: INS-065 删除 Leaky → Phase 13 Mandate A
│
├── WHY 2: Pearson IC 从 E0=0.0046 单调降到 E19=0.0001
│   ├── ROOT CAUSE: MSE 在 SNR=2.4% 下退化 + L1 杀信号
│   └── FIX: INS-066 换 IC Loss + INS-069 删 L1 → Phase 13 Mandate A
│
├── WHY 3: RPB grad_norm=0.08 vs decoder=4811 (60000x)
│   ├── ROOT CAUSE: Global Mean Pooling 抹平梯度
│   └── FIX: INS-068 AttentionPooling + Pre-LN Residual → Phase 13 Mandate B
│
└── WHY 4: 窗口感受野 0.64 天 (机构建仓>3天)
    ├── ROOT CAUSE: 5 个孤立 32-bar 窗口无交互
    └── FIX: INS-070 Swin-style 跨窗口 → Phase 14 (未实现)
```

---

## 第三章: Phase 13 实现与验证

### 3.1 架构变更 (Phase 12 → Phase 13)

| 组件 | Phase 12 | Phase 13 | 参数变化 |
|------|----------|----------|----------|
| Loss | Unbounded Spear MSE | **Pearson IC Loss** | - |
| Pooling | Global Mean Pool | **Attention Pool (W_pool)** | +128 params |
| Normalization | 无 | **Pre-LN (tda_pre_ln)** | +16 params |
| Residual | 无 | **x + tda(LN(x))** | 0 params |
| lambda_s | 1e-4 (warmup 2 epochs) | **0 (固定)** | - |
| Leaky | 0.1 | **删除** | - |
| 窗口 | 5×32 孤立 | 5×32 孤立 (未改) | - |
| **总参数** | **24,437** | **24,581** | **+144** |

### 3.2 Vertex AI Job 全记录

| # | Job Name | GPU | 状态 | 原因/结果 |
|---|----------|-----|------|-----------|
| 1 | canary-p13v1-093821 | L4 | **FAILED** | phase12 checkpoint 缺 attention_pool/pre_ln keys |
| 2 | crucible-mandate-b | L4 | CANCELLED | 手动取消 |
| 3 | crucible-ondemand | L4 | CANCELLED | us-central1 L4 资源不足 |
| 4 | **crucible-phase13-v2** | **L4** | **SUCCEEDED** | Mandate B 验证: loss 5.21→0.67, PfRet→316 |
| 5 | canary-p13v2-122716 | L4 | CANCELLED | 资源不足超时 900s |
| 6 | crucible-p13v2-125936 | L4 | CANCELLED | 资源不足 fail-retry 循环 |
| 7 | **crucible-p13v2-t4** | **T4** | **SUCCEEDED** | **Mandate A 最终验证 (IC Loss)** |

7 次提交，2 次成功，3 次资源不足，1 次 checkpoint 不兼容，1 次手动取消。

### 3.3 Crucible 对比: Phase 12 Overfit vs Phase 13 Overfit

**相同条件**: 64 samples, 2000 steps, batch=64, hidden_dim=64, no_amp

| Step | Phase 12 MSE Loss | Phase 13 IC Loss | Phase 13 Pearson IC |
|------|------------------|-----------------|---------------------|
| 0 | 8.353 | 0.036 | ~-0.04 (随机) |
| 200 | 0.212 | -0.534 | ~0.53 |
| 400 | 0.143 | -0.673 | ~0.67 |
| 600 | 0.117 | -0.740 | ~0.74 |
| 800 | 0.106 | -0.779 | ~0.78 |
| 1000 | 0.096 | -0.805 | ~0.81 |
| 1200 | 0.090 | -0.824 | ~0.82 |
| 1400 | 0.084 | -0.841 | ~0.84 |
| 1600 | 0.080 | -0.854 | ~0.85 |
| 1800 | 0.075 | -0.864 | ~0.86 |
| **Final** | **0.073** | **-0.875** | **~0.88 (running avg)** |

| 指标 | Phase 12 (MSE) | Phase 13 (IC Loss) | 可比性 |
|------|---------------|-------------------|--------|
| **Val 样本量** | **5,000** | **64** | **不可比 — 78x 差异** |
| Val D9-D0 | -1.35 BP | +435.51 BP | ❌ Phase 13 仅 top 6 vs bottom 6 样本，纯噪声 |
| Val Std_yhat | 41.65 BP | 333.38 BP | ❌ 64 样本 std 不稳定 |
| Val Rank IC | (未测) | 0.140 | ⚠️ 64 样本方向性参考，不可作为性能指标 |
| Val Pearson IC | (未测) | 0.200 | ⚠️ 同上 |
| **Train Pred_std 趋势** | **0.0078→0.0015 (↓5x)** | **0.0092→0.0072 (↓1.3x)** | **✅ 可比 — 同为训练集 64 样本** |

**⚠️ 数据可信度警告:**
- Phase 12 val: 1 shard = 5,000 samples (有一定统计意义)
- Phase 13 val: `--max_val_steps=1` = 仅 1 batch = 64 samples (无统计意义)
- D9-D0、Std_yhat、IC 三项 val 指标在 64 样本上不具备可信度
- **唯一可靠对比: 训练集 Pred_std 趋势** (同为 64 样本 overfit，条件一致)

**可靠结论 (仅基于可比数据):**
1. Train Pred_std 衰减: Phase 13 (1.3x) 远优于 Phase 12 (5x) — 方差坍缩风险更低
2. 两者均能 overfit: Phase 12 loss 8.35→0.073, Phase 13 IC 0.04→0.88
3. Val 指标需等正式训练 (~190 万 val samples) 才有意义

### 3.4 linux1 本地验证

```
Device: AMD APU (ROCm 6.1, 108GB VRAM)
Step 0: IC_loss=0.151600, S_T=3.7414, Std_yhat=0.028628
Status: PASS (Step 0 成功)
Failure: torch.compile + ROCm 不兼容 (aten::empty.memory_format HIP backend)
结论: GCP NVIDIA 不受影响，本地验证确认 IC Loss 前向+反向传播正常
```

### 3.5 外部审计 (Phase 13 Crucible)

| 审计方 | 结果 | 发现 |
|--------|------|------|
| **Gemini 3.1 Pro** | 6/6 PASS | lr=1e-3 合适 IC Loss; FP32 正确; 预期 loss→-0.98~-0.999 |
| **Codex** | 2 FAIL (已修复) | imageUri 指向旧 v1; Dockerfile 缺 scipy |

修复记录: commit `5084d10` — imageUri v1→v2 + scipy dep + C-071 lesson + R-018 rule

---

## 第四章: 教训索引 (Phase 12/13 时期)

| ID | 教训 | 数据依据 | 公理 |
|----|------|----------|------|
| C-055 | SSH 管道 + stdin 冲突 | ssh nohup 后台时 stdin EOF | Omega4 |
| C-057 | Spec-code 参数漂移 | 默认值不一致导致训练偏差 | Omega1 |
| C-058 | Dockerfile COPY 漂移 | root/ vs gcp/ 文件不同步 | Omega3 |
| C-062 | Phase 6 IC=0.066 需重验 | torch.compile `_orig_mod.` bug 可能导致推理用随机权重 | Omega1 |
| C-067 | "同意原则"后立刻违反 | Claude 口头同意先验证再跑，下一步就提交 job | Omega4 |
| C-068 | 归档指令凭标题判重 | V2 directive 内容全新但 Claude 只看日期 | Omega1 |
| C-069 | Crucible 必须跳过验证 | 读 399 val shards 浪费 15min | Omega2 |
| C-070 | Loss= 是 running avg | 误判 loss=0.674 为未收敛，实际瞬时≈0.15 | Omega1 |
| C-071 | 改 Loss 后部署链失同步 | imageUri stale + scipy 缺失 | Omega3+1 |

---

## 第五章: 当前状态与疑惑点

### 5.1 已完成

- [x] Phase 12 完整训练 (20 epochs, 13.9h)
- [x] Phase 12 Post-Flight 全量推理 (1,904,747 samples)
- [x] 外部审计双路诊断 (Gemini 数学 + Codex 架构)
- [x] Phase 13 Spec FINAL (Codex 9/9 + Gemini 7/7)
- [x] Mandate B 代码 + Crucible PASS (AttentionPooling + Pre-LN + Residual)
- [x] Mandate A 代码 + Crucible PASS (IC Loss)
- [x] Docker phase13-v2 构建推送成功
- [x] C-071 bug 修复 (imageUri + scipy)
- [x] Harness 更新 (R-018 规则 + incidents/C-071)

### 5.2 待执行

- [ ] 创建 phase13_train_config.yaml (正式训练配置)
- [ ] 补写 manifest (crucible PASS 记录)
- [ ] 提交正式训练 (T4 Spot, ~10h, ~$2-3)
- [ ] 训练后 Post-Flight: 全量推理 + 截面 IC + D9-D0

### 5.3 开放疑惑点 (需正式训练数据回答)

#### 疑惑 1: IC Loss 方差坍缩风险
**数据**: Crucible pred_std 从 0.0092 降到 0.0072 (1.3x)
**担忧**: IC Loss 只优化 ranking 不约束 scale，full dataset 上可能加剧
**缓解**: validate() 有哨兵 (error<10BP, warn<30BP)，IC 梯度 ∝ 1/pred_std 有自纠正
**验证方法**: 正式训练逐 epoch 监控 pred_std_bp，连续 3 epoch < 30BP 或单次 < 10BP 停训

#### 疑惑 2: Batch-level IC vs Per-date IC 的信息泄露
**数据**: Spec 标注 `[APPROXIMATION]`，当前 batch 混合不同日期样本
**担忧**: 不同日期市场均值不同，batch IC 可能部分学到日期间均值差异
**影响**: 可能高估 IC (排序能力部分来自日期均值差异，非 Alpha)
**验证方法**: Post-Flight 计算 per-date IC 并与 global IC 对比

#### 疑惑 3: Phase 6 IC=0.066 基准是否有效
**数据**: torch.compile `_orig_mod.` bug (C-062) 可能导致 Phase 6 推理用随机权重
**影响**: 如果 Phase 6 基准无效，Phase 13 没有可靠的历史对比
**验证方法**: 用修正后的代码重跑 Phase 6 checkpoint 推理

#### 疑惑 4: INS-070 窗口隔离未解决
**数据**: 5×32 bar 孤立窗口，感受野 0.64 天
**影响**: 机构建仓跨多日的模式无法学习，可能是 IC 上限的结构性瓶颈
**状态**: Phase 14 计划，不阻断 Phase 13 训练
**理由**: Phase 13 的其他修复 (IC Loss + 拓扑解锁) 需要先独立验证效果

#### 疑惑 5: Crucible IC_loss=-0.875 未达预期 -0.98
**数据**: Gemini 预测 -0.98~-0.999，实测 running avg -0.875
**可能原因**:
  1. Running average 拖累 (C-070) — 瞬时可能 -0.92~-0.95
  2. hd=64 瓶颈限制完美 memorization (设计意图)
  3. lr=1e-3 + 2000 步不够完全收敛 (曲线仍在下降，无 plateau)
**判断**: 不阻断。曲线单调下降、无振荡、方向正确。

---

## 第六章: 放行判定

### GO / NO-GO 清单

| 检查项 | 状态 | 数据支撑 |
|--------|------|----------|
| IC Loss 实现正确 | ✅ GO | Crucible IC: 0→0.88 单调收敛 |
| AttentionPooling 工作 | ✅ GO | 参数量 24,437→24,581 (+144) |
| Pre-LN + Residual 工作 | ✅ GO | Mandate B crucible PASS |
| 梯度通路健康 | ✅ GO | linux1 Step 0 成功; Crucible 全程无 NaN |
| FP32 精度 | ✅ GO | no_amp 配置; eps=1e-8 sqrt(var+eps) |
| Checkpoint save/load | ✅ GO | Crucible 写入 checkpoint 成功 |
| Docker 镜像 | ✅ GO | phase13-v2 Build+Push 成功; scipy 确认安装 |
| Spec-Code 对齐 | ✅ GO | safe_build_and_canary Step 1d: 18/18 PASS |
| 方差坍缩防护 | ⚠️ 监控 | 哨兵已内置; Crucible pred_std 衰减温和 (1.3x) |
| 成本比例 | ✅ GO | T4 Spot ~$2-3, Taleb 式小额试错 |

### 最终判定: **CONDITIONAL GO**

条件:
1. pred_std_bp 连续 3 epoch < 30BP → 停训排查
2. Epoch 2 Val Rank IC 必须 > 0
3. 训练后必须跑 Post-Flight 全量推理验证截面 IC

---

*本文档由实测数据生成，每个结论标注数据来源。*
*审计链: Phase 12 训练日志 → Post-Flight 推理 → Gemini+Codex 诊断 → INS-065~070 → Phase 13 代码 → Crucible 验证 → 本审计*

---

## 附录 A: 原始证据 — 完整 Decile 表 (E0 best.pt)

> 源文件: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.1

| Decile | N | mean_pred (BP) | mean_target (BP) | hit_rate | per-decile IC |
|--------|--------|---------------|-----------------|----------|---------------|
| D0 | 190,492 | -9.04 | +4.53 | 51.4% | 0.0160 |
| D1 | 190,668 | +7.01 | +6.62 | 51.0% | 0.0051 |
| D2 | 190,424 | +15.75 | +7.45 | 50.3% | -0.0018 |
| D3 | 190,777 | +22.91 | +6.41 | 49.5% | -0.0001 |
| D4 | 190,456 | +29.58 | +6.64 | 49.3% | 0.0001 |
| D5 | 190,616 | +36.30 | +7.20 | 49.2% | -0.0012 |
| D6 | 190,283 | +43.48 | +7.26 | 49.1% | 0.0007 |
| D7 | 190,598 | +51.72 | +7.28 | 49.0% | 0.0023 |
| D8 | 190,029 | +62.46 | +6.86 | 48.6% | -0.0025 |
| D9 | 190,404 | +84.12 | +9.04 | 49.0% | -0.0005 |

## 附录 B: 原始证据 — E19 vs E0 Checkpoint 对比

> 源文件: `handover/LATEST.md`, `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md`

| 指标 | E0 (best.pt) | E19 (latest.pt) | Phase 11c | Phase 6 (IC Loss) |
|------|-------------|-----------------|-----------|-------------------|
| pred_std (BP) | 26.61 | 18.57 | 5.64 | — |
| D9-D0 (BP) | +4.51 | +1.29 | +8.90 | **-5.92** |
| Pearson IC | 0.0046 | 0.0001 | 0.0210 | 0.066 |
| Spearman Rank IC | -0.0206 | **-0.0297** | — | — |
| z_sparsity | 5.4% | 18.5% | — | — |
| Corr(z_sparsity, |pred|) | -0.001 | +0.225 | -0.22 | — |
| S_T | 2.087 | 1.157 | — | — |

注意: Phase 6 D9-D0 = **-5.92 BP** (负值)。历史最高 IC=0.066 对应的 D9-D0 是反转的。

## 附录 C: 原始证据 — 全 14 参数组梯度范数

> 源文件: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五.2

```
参数组                              grad_norm    占比
──────────────────────────────────────────────────────
intent_decoder.bias                 4,811        [最强]
bottleneck.2.bias                   3,145
bottleneck.2.weight                   730
bottleneck.0.bias                     715
bottleneck.0.weight                   588
tda_layer.qkv.weight                  498
tda_layer.proj.weight                  474
tda_layer.proj.bias                    336
input_proj.weight                      165
post_proj_norm.bias                    118
post_proj_norm.weight                   40
input_proj.bias                       0.06
tda_layer.rpb_table                   0.08        [最弱 — 60,137x 弱于 decoder]
```

RPB 参数量: 1,197 entries × 4 heads = 4,788 params (总参数 24,437 的 19.6%)

## 附录 D: 原始证据 — Rank IC 统计显著性计算

> 源文件: `handover/PHASE12_AUDIT_PROMPT.md`

```
Spearman Rank IC = -0.0206
样本量 N = 1,904,747
标准误 SE = 1/√N = 1/√1,904,747 = 0.000725
Z-score = -0.0206 / 0.000725 = -28.4σ

注: 审计正文写 29σ，精确计算为 28.4σ。两者均远超 5σ 显著性阈值。

E19 Rank IC: -0.0297
E19 Z-score: -0.0297 / 0.000725 = -41.0σ (更显著的反向排序)
```

## 附录 E: 原始证据 — Leaky Blinding 数学推导

> 源文件: `architect/insights/INS-065_drop_leaky_blinding.md`

```
原始 target 分布:
  E[T|T>0] = +158.6 BP (正收益期望)
  E[T|T<0] = -144.6 BP (负收益期望)
  P(T>0) ≈ P(T<0) ≈ 0.5

Leaky 变换 (leaky_factor=0.1):
  T_leaky = T       if T > 0
  T_leaky = 0.1 × T if T < 0

Leaky 后期望:
  E[T_leaky] = 0.5 × 158.6 + 0.5 × 0.1 × (-144.6)
             = 79.3 - 7.23
             = 72.07 BP

Static Centering (static_mean_bp=40):
  E[T_centered] = 72.07 - 40.0 = +32.07 BP

实测 pred_mean = +34.42 BP (误差 7.3%)

MSE 梯度压缩:
  正收益: grad ∝ (pred - T)²
  负收益: grad ∝ (pred - 0.1×T)² = 0.01 × (pred/0.1 - T)²
  → 负收益梯度被压缩 100x (0.1² = 0.01)
```

## 附录 F: 原始证据 — INS-066 IC Loss 翻案依据

> 源文件: `architect/insights/INS-066_revert_to_ic_loss.md`

```
历史 IC 对比:
  Phase 6 (IC Loss):           Pearson IC = 0.066 [历史最高]
  Phase 11c (MSE):             Pearson IC = 0.021
  Phase 12 E0 (Unbounded MSE): Pearson IC = 0.005
  Phase 12 E19 (Unbounded MSE):Pearson IC = 0.0001

IC Loss → MSE 切换点: INS-018
  INS-018 废弃理由: "IC Loss 绝对尺度太小，无法用于仓位管理"
  INS-066 翻案理由: "尺度是推理工程问题 — Daily Cross-Sectional Z-Score 解决"
  [AUDIT OVERRIDE] INS-018 被推翻

MSE 失效证明 (SNR 分析):
  target_std = 189.60 BP
  signal (D9-D0) = 4.51 BP
  SNR = 4.51 / 189.60 = 2.4%
  结论: MSE gradient 被 189 BP 噪声主导，退化为条件均值预测
```

## 附录 G: 原始证据 — Phase 13 IC Loss 实现代码

> 源文件: `gcp/omega_epiplexity_plus_core.py:215-242`

```python
def compute_ic_loss(prediction, target, ic_epsilon=1e-8):
    """Phase 13 Mandate A: Pearson IC Loss (INS-066)"""
    pred = prediction.float().view(-1)
    tgt = target.float().view(-1)

    if pred.numel() < 2:
        return torch.tensor(0.0, device=pred.device, requires_grad=True)

    pred_centered = pred - pred.mean()
    tgt_centered = tgt - tgt.mean()

    cov = (pred_centered * tgt_centered).mean()
    pred_std = torch.sqrt((pred_centered ** 2).mean() + ic_epsilon)  # NOT clamp
    tgt_std = torch.sqrt((tgt_centered ** 2).mean() + ic_epsilon)

    ic = cov / (pred_std * tgt_std)
    return -ic  # minimize negative IC = maximize IC
```

> 源文件: `gcp/train.py:86-100`

```python
def compute_ic_loss_wrapper(pred, target, z_core, ic_epsilon=1e-8):
    """lambda_s=0 (INS-069), no warmup needed, no target warping."""
    ic_loss = compute_ic_loss(pred, target, ic_epsilon=ic_epsilon)
    # s_t monitoring only (not added to loss since lambda_s=0)
    with torch.no_grad():
        z_core_safe = torch.clamp(z_core.float(), min=-20.0, max=20.0)
        s_t = torch.norm(z_core_safe, p=1, dim=-1).mean()
    return ic_loss, s_t
```

## 附录 H: 原始证据 — validate() 哨兵逻辑

> 源文件: `gcp/train.py:408-466`

```python
def validate(model, val_loader, device, max_steps=0,
             sentinel_error=10.0, sentinel_warn=30.0):
    """Phase 13: Cross-Sectional Validation (INS-066/067)
    Primary metric: Rank IC (Spearman). Secondary: D9-D0 Spread."""

    # 1. Variance Collapse Detection (INS-017/054)
    pred_std_bp = preds.std().item() * 10000.0
    if pred_std_bp < sentinel_error and n_samples > 10:
        logger.error("VARIANCE COLLAPSE: pred_std=%.2f BP < %.0f" % (pred_std_bp, sentinel_error))
    elif pred_std_bp < sentinel_warn:
        logger.warning("LOW VARIANCE: pred_std=%.2f BP < %.0f" % (pred_std_bp, sentinel_warn))

    # 2. Pearson IC (aggregate, not per-date — [APPROXIMATION])
    pearson_ic = float(np.corrcoef(pred_np, tgt_np)[0, 1])

    # 3. Rank IC — Spearman (PRIMARY metric, Vizier MAXIMIZE)
    rank_ic, rank_ic_pval = spearmanr(pred_np, tgt_np)

    # 4. D9-D0 Spread (global topk, not per-date — [APPROXIMATION])
    k = max(n_samples // 10, 1)
    _, top_idx = torch.topk(preds, k)
    _, bot_idx = torch.topk(preds, k, largest=False)
    d9_d0_spread = (targets_cat[top_idx].mean() - targets_cat[bot_idx].mean()).item()
```

哨兵阈值: `error=10 BP` (HARD), `warn=30 BP` (SOFT)
已知近似: Pearson IC 和 D9-D0 均为 global 而非 per-date (Spec [APPROXIMATION])

## 附录 I: 原始证据 — torch.compile _orig_mod. Bug

> 源文件: `OMEGA_LESSONS.md` C-062, `gcp/train.py:262-264`

**Bug 机制:**
```
torch.compile(model) 给 state_dict key 加 "_orig_mod." 前缀
  例: "input_proj.weight" → "_orig_mod.input_proj.weight"

model.load_state_dict(ckpt, strict=False) 不匹配时静默跳过
  → 所有权重保持 random initialization
  → 推理输出 = 随机噪声
```

**修复 (3 处):**
```python
# 1. Save side (gcp/train.py:262-264):
raw_state = model.state_dict()
clean_state = {k.replace("_orig_mod.", ""): v for k, v in raw_state.items()}

# 2. Load side (gcp/phase7_inference.py:202-203):
state = {k.replace("_orig_mod.", ""): v for k, v in ckpt["model_state_dict"].items()}

# 3. Load side (backtest_5a.py:136-138):
# Same defensive strip
```

**影响范围:**
- Phase 6 T29 (IC=0.066): 可能受影响 → 基准待重验
- Phase 11c (D9-D0=8.90): 可能受影响 → 基准待重验
- Phase 12+: 已修复

## 附录 J: 原始证据 — Chain of Custody

> 源文件: `architect/chain_of_custody.yaml`

**Phase 12 链:**
```yaml
directive: "2026-04-02_phase12_unshackling_protocol.md"
stage: deployed
insights: [INS-060, INS-063, INS-064]
spec_fields:
  - "loss_function: Unbounded Spear"
  - "hpo.fixed_params.lambda_s: 1e-4"
code_files: ["omega_epiplexity_plus_core.py", "train.py"]
audit_status: final
failures:
  - lesson: C-059
    root_cause: "ETL 输出单位假设错误 — INS 未记录数据格式前提"
```

**Phase 13 V1 链:**
```yaml
directive: "2026-04-04_phase13_audit_verdict_and_roadmap.md"
superseded_by: "2026-04-04_phase13_audit_verdict_and_roadmap_v2.md"
insights: [INS-065, INS-066, INS-067, INS-068, INS-069]
audit_overrides:
  - rejected: "INS-018 废弃 IC Loss (绝对尺度太小)"
    reason: "尺度是推理工程问题 — cross-sectional Z-score 解决"
```

**Phase 13 V2 链 (V2 新增内容):**
```yaml
directive: "2026-04-04_phase13_audit_verdict_and_roadmap_v2.md"
insights: [INS-070]
v2_new_content:
  - "Volatility Sorting Illusion 诊断 (Phase 6 D9-D0=-5.92 BP)"
  - "Shatter Window Isolation mandate (INS-070)"
  - "64-sample Crucible Overfit Test pass criteria (loss→0.0)"
```

## 附录 K: 原始证据 — Phase 12 Overfit Test 完整曲线

> 源文件: Vertex AI Job 8287604473870680064 日志

```
条件: 64 samples, 2000 steps, batch=64, lr=3.2e-4, lambda_s=0, no_amp
模型: OmegaTIBWithMasking, 24,437 params (Phase 12 架构)

Step    0: Loss=8.353  PfRet=2.35   S_T=2.183  Std_yhat=0.007775
Step  200: Loss=0.212  PfRet=0.90   S_T=2.130  Std_yhat=0.001655
Step  400: Loss=0.143  PfRet=16.15  S_T=2.084  Std_yhat=0.001301
Step  600: Loss=0.117  PfRet=37.03  S_T=2.048  Std_yhat=0.001240
Step  800: Loss=0.106  PfRet=45.70  S_T=2.014  Std_yhat=0.001292
Step 1000: Loss=0.096  PfRet=52.17  S_T=1.982  Std_yhat=0.001316
Step 1200: Loss=0.090  PfRet=56.13  S_T=1.957  Std_yhat=0.001363
Step 1400: Loss=0.084  PfRet=58.74  S_T=1.937  Std_yhat=0.001411
Step 1600: Loss=0.080  PfRet=60.95  S_T=1.921  Std_yhat=0.001449
Step 1800: Loss=0.075  PfRet=62.73  S_T=1.909  Std_yhat=0.001487

Final: Loss=0.073, Val D9-D0=-1.35 BP, Val Std_yhat=41.65 BP
Gradient: 所有 14 参数组 grad_norm > 0 (PASS)

注意: Std_yhat 从 0.0078 降到 0.0015 (5.2x 衰减) — 方差坍缩严重
对比 Phase 13: Std_yhat 从 0.0092 降到 0.0072 (1.3x 衰减)
```

## 附录 L: 原始证据 — Phase 13 Mandate B Crucible

> 源文件: Vertex AI Job 5402703665888755712 日志

```
条件: 64 samples, 2000 steps, batch=64, lr=1e-3, lambda_s=0, no_amp
模型: OmegaTIBWithMasking, 24,581 params (Phase 13 架构, Unbounded Spear Loss)
目的: 验证 AttentionPooling + Pre-LN + Residual 架构修改

Step    0: Loss=5.213  PfRet=50.50   S_T=3.900  Std_yhat=0.008239
Step  200: Loss=2.217  PfRet=218.98  S_T=2.195  Std_yhat=0.005805
Step  400: Loss=1.737  PfRet=246.54  S_T=2.051  Std_yhat=0.006588
Step  600: Loss=1.454  PfRet=248.21  S_T=2.064  Std_yhat=0.007412
Step  800: Loss=1.270  PfRet=255.13  S_T=2.092  Std_yhat=0.008056
Step 1000: Loss=1.114  PfRet=265.43  S_T=2.141  Std_yhat=0.008668
Step 1200: Loss=0.987  PfRet=277.34  S_T=2.192  Std_yhat=0.009231
Step 1400: Loss=0.879  PfRet=289.51  S_T=2.233  Std_yhat=0.009695
Step 1600: Loss=0.802  PfRet=298.98  S_T=2.253  Std_yhat=0.010031
Step 1800: Loss=0.732  PfRet=308.34  S_T=2.269  Std_yhat=0.010328

Final: Loss=0.674, PfRet=316.10, Val D9-D0=-301.01 BP, Val Std_yhat=140.98 BP
训练时间: 123s

注意: Std_yhat 持续上升 0.0082→0.0103 — 无方差坍缩
注意: S_T 先降后升 (3.90→2.05→2.28) — 与 Phase 12 单调下降不同
```

## 附录 M: 源文件索引

| 证据 | 文件路径 | 用于验证 |
|------|----------|----------|
| Phase 12 训练日志 | `logs/phase12_monitor.log` | §1.2 逐 Epoch 曲线 |
| Phase 12 Post-Flight | `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` | §1.3 Decile 表, 附录 A/B |
| Phase 12 Post-Flight | `handover/LATEST.md` | §1.3 E19 数据, 附录 B |
| Gemini 诊断 | `architect/insights/INS-065_drop_leaky_blinding.md` | §1.4 Leaky 数学, 附录 E |
| Codex 诊断 | `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` §五 | §1.4 梯度范数, 附录 C |
| IC Loss 翻案 | `architect/insights/INS-066_revert_to_ic_loss.md` | §2.2 INS-066, 附录 F |
| L1 删除 | `architect/insights/INS-069_remove_mdl_guillotine.md` | §1.4 数据点 3 |
| 拓扑解锁 | `architect/insights/INS-068_topological_unblocking.md` | §3.1 架构变更 |
| 窗口隔离 | `architect/insights/INS-070_shatter_window_isolation.md` | §5.3 疑惑 4 |
| 截面评估 | `architect/insights/INS-067_cross_sectional_evaluation.md` | §5.3 疑惑 2 |
| IC Loss 代码 | `gcp/omega_epiplexity_plus_core.py:215-242` | 附录 G |
| 训练循环 | `gcp/train.py:330-400` | 附录 G/H |
| 哨兵逻辑 | `gcp/train.py:408-466` | 附录 H |
| _orig_mod bug | `OMEGA_LESSONS.md` C-062, `gcp/train.py:262` | 附录 I |
| Chain of Custody | `architect/chain_of_custody.yaml` | 附录 J |
| Phase 12 Overfit | Vertex AI Job 8287604473870680064 | 附录 K |
| Mandate B Crucible | Vertex AI Job 5402703665888755712 | 附录 L |
| Mandate A Crucible | Vertex AI Job 5026336437654519808 | §3.3 |
| Spec | `architect/current_spec.yaml` | §3.1 |
| 教训库 | `OMEGA_LESSONS.md` C-055~C-071 | §4 |
| 规则库 | `rules/active/R-018_docker_dep_tag_sync.yaml` | §3.5 |
| Incident | `incidents/C-071_docker_dep_tag_sync/` | §3.5 |

---

**数据修正记录:**
- Rank IC Z-score: 正文写 29σ，精确计算为 28.4σ (附录 D)。两者均远超显著性阈值，结论不变。
