# Phase 9 Evidence Package — 非对称 Pearson Loss 全版本训练数据


**Date**: 2026-03-30
**Purpose**: 递交独立审计师评审，判断非对称 Loss 方向是否可行
**Baseline**: Phase 6 T29 对称 Pearson (IC=0.066, Val IC=0.066, OOS/IS=1.00)


---


## 1. 版本总览


| Version | Job ID | 状态 | 关键修改 | 结果 |
|---------|--------|------|---------|------|
| **v1** | 5893905262917451776 | CANCELLED | dampening=0.05 + MSE anchor 也 dampened | 灾难性过拟合 |
| **v2** | 2484363685649186816 | CANCELLED | dampening=0.3 + MSE anchor 对称 (pipe) | 恢复了 v1 污染的 checkpoint |
| **v2b** | 7657873757591044096 | CANCELLED | 同 v2 但全新 output_dir | Spot 抢占，仅完成 Epoch 0 训练 |
| **v3** | 4203190630932807680 | FAILED | g2-standard-24 + Local SSD | 磁盘不足 (L4 quota=1, 需要 2) |
| **v3b** | 710086169953566720 | CANCELLED | g2-standard-24 + 800GB pd-ssd | L4 on-demand quota=1, 需要 2 |
| **v3c** | 8012391490758115328 | CANCELLED | g2-standard-8 + 800GB staging | **3 epoch 完整数据，val IC 持续下降** |
| **v4** | 6638582498177581056 | RUNNING | anchor_weight 0.001→0.01 | 训练中 |


---


## 2. 各版本代码差异


### 共同基础 (所有版本)
```
Model: T29 (hd=64, wt=32, 19.7K params) — 架构锁定
Data: 1593 train shards + 399 val shards (temporal 80/20 split)
Epochs: 20 × 10,000 steps
Batch: 128
lr: 3.2e-4 | lambda_s: 1e-7 | warmup: 2
```


### 版本差异表


| Parameter | v1 | v2/v2b | v3c | v4 (current) |
|-----------|-----|--------|-----|-------------|
| `downside_dampening` | 0.05 | 0.3 | 0.3 | 0.3 |
| MSE anchor dampened? | **YES** (致命) | NO | NO | NO |
| `anchor_weight` | 0.001 | 0.001 | 0.001 | **0.01** |
| Data I/O | pipe | pipe | **local staging** | local staging |
| Hardware | L4 Spot | L4 Spot | L4 On-demand | L4 On-demand |
| Machine | g2-standard-8 | g2-standard-16 | g2-standard-8 | g2-standard-8 |
| `--no_amp` | YES | YES | YES | YES |
| `num_workers` | 4 | 8 | 4 | 4 |


### 代码修改时间线


| Commit | 修改 | 原因 |
|--------|------|------|
| `0b2bf49` | 新增 `asymmetric_pearson_loss()` + `--downside_dampening` | Phase 9 核心 |
| `6157a3d` | 向量化 masking + pin_memory + 显式参数传递 | Gemini 审计 |
| `ea00751` | GCS pipe 模式 + `--no_amp` + L4 job config | GCS 优化 |
| `516e536` | **MSE anchor 恢复对称** + dampening 0.05→0.3 | v1 过拟合修复 |
| `f820d11` | g2-standard-24 + Local SSD + On-demand | Gemini I/O 优化 |
| `075621d` | anchor_weight 0.001→0.01 + 新 output_dir | v3c val IC 下降 |


---


## 3. 训练数据 — v1 (dampening=0.05, anchor dampened)


**Job**: 5893905262917451776 | **结局**: Gemini 判定 STOP — 灾难性过拟合


### Epoch 级指标
| Epoch | Train Loss | Train IC | Val Loss | Val IC | Val Std_yhat | Gap |
|-------|-----------|----------|----------|--------|-------------|-----|
| 0 | 0.855 | — | 1.004 | **-0.001** | 13.70 BP | — |


### Step 级训练指标
| Epoch | Step | Loss | IC | Std_yhat |
|-------|------|------|----|----------|
| 0 | 0 | 1.056 | -0.056 | 0.000700 |
| 0 | 5000 | 0.886 | 0.114 | 0.003006 |
| 0 | 9000 | 0.859 | 0.141 | 0.011933 |
| 1 | 0 | 0.953 | 0.047 | 0.036814 |
| 1 | 5000 | 0.820 | 0.180 | 0.071229 |
| 1 | 9000 | 0.819 | **0.181** | **0.093174** |


### 诊断
- **Train IC 0.181**: 对称版 Phase 6 的 2.7 倍 — 看似极好
- **Val IC -0.001**: 本质为零 — 模型在验证集上毫无预测能力
- **Std_yhat 爆炸**: 0.0007 → 0.093 (133 倍膨胀)
- **Gemini 根因**: MSE anchor 也做了 dampening → 负端预测无约束 → 尺度失控


---


## 4. 训练数据 — v2b (dampening=0.3, anchor 对称, pipe)


**Job**: 7657873757591044096 | **结局**: L4 Spot 抢占于 Epoch 0 验证期间


### Step 级训练指标 (仅有 Epoch 0 部分数据)
| Epoch | Step | Loss | IC | Std_yhat |
|-------|------|------|----|----------|
| 0 | 5000 | 0.922 | 0.079 | 0.003183 |
| 0 | 9000 | 0.909 | 0.092 | 0.012956 |


### 诊断
- IC 收敛速度比 v1 温和 (0.092 vs 0.141 at step 9000) — dampening 0.3 vs 0.05
- Std_yhat 增速也更慢 (0.013 vs 0.012 at step 9000) — 相近
- **未获得 val IC** — Spot 在验证期间被抢占
- 此数据点证实 dampening 0.3 的训练行为与 v3c 一致


---


## 5. 训练数据 — v3c (dampening=0.3, anchor 对称, local staging, anchor_weight=0.001)


**Job**: 8012391490758115328 | **结局**: Val IC 连续 3 epoch 下降，手动停止


### Epoch 级指标 (完整 3 epoch)
| Epoch | Train Loss | Train IC | Val Loss | Val IC | Val Std_yhat | Train-Val Gap |
|-------|-----------|----------|----------|--------|-------------|--------------|
| 0 | 0.909 | 0.091 | 0.987 | **+0.006** | 17.94 BP | 0.085 |
| 1 | 0.896 | 0.105 | 0.990 | **+0.004** | 61.12 BP | 0.101 |
| 2 | 0.885 | 0.118 | 0.989 | **+0.003** | 50.18 BP | 0.115 |


### Step 级训练指标 (全部)
| Epoch | Step | Loss | IC | Std_yhat |
|-------|------|------|----|----------|
| 0 | 0 | 0.971 | 0.030 | 0.000743 |
| 0 | 5000 | 0.929 | 0.072 | 0.003926 |
| 0 | 9000 | 0.910 | 0.091 | 0.016776 |
| 1 | 0 | 1.022 | -0.022 | 0.053059 |
| 1 | 5000 | 0.900 | 0.101 | 0.102542 |
| 1 | 9000 | 0.895 | 0.105 | 0.131331 |
| 2 | 0 | 0.840 | 0.161 | 0.179648 |
| 2 | 5000 | 0.877 | 0.124 | 0.215232 |
| 2 | 9000 | 0.883 | 0.118 | 0.229534 |
| 3 | 0 | 1.016 | -0.015 | 0.150843 |
| 3 | 5000 | 0.882 | 0.119 | 0.231541 |


### 关键趋势分析


**Val IC 趋势: 单调下降**
```
Epoch 0: +0.0056
Epoch 1: +0.0042  (−25%)
Epoch 2: +0.0029  (−31%)
线性外推 Epoch 5: ≈ 0 (归零)
```


**Std_yhat (train) 趋势: 指数增长后放缓**
```
Epoch 0 end: 0.017
Epoch 1 end: 0.131  (7.7×)
Epoch 2 end: 0.230  (1.8×)
Epoch 3 mid: 0.232  (1.0× — 似乎饱和)
```


**Train-Val Gap 趋势: 持续扩大**
```
Epoch 0: 0.085
Epoch 1: 0.101  (+19%)
Epoch 2: 0.115  (+14%)
```


**Train IC 趋势: 继续上升但放缓**
```
Epoch 0: 0.091
Epoch 1: 0.105  (+15%)
Epoch 2: 0.118  (+12%)
```


---


## 6. 对照基线 — Phase 6 T29 对称 Pearson


| Metric | Phase 6 (对称) | v3c Epoch 0 | v3c Epoch 2 |
|--------|---------------|-------------|-------------|
| Train IC | 0.066 | 0.091 | 0.118 |
| Val IC | 0.066 | 0.006 | 0.003 |
| OOS/IS Ratio | **1.00** | 0.066 | 0.025 |
| Std_yhat (val) | — | 17.94 BP | 50.18 BP |
| Loss function | Pearson | Asym Pearson (0.3) | Asym Pearson (0.3) |
| anchor_weight | 0.001 | 0.001 | 0.001 |


---


## 7. 基础设施失败记录


| Version | 失败类型 | 根因 | 教训编号 |
|---------|---------|------|---------|
| v2 | 恢复了 v1 的污染 checkpoint | 同一 output_dir | C-020 |
| v3 | FAILED: disk full | g2-standard-24 Local SSD 需要显式挂载 | C-016 |
| v3b | PENDING 永久 | L4 on-demand quota=1, g2-standard-24 需要 2× L4 | C-016 |
| v2b | Spot 抢占 | 验证期间被回收，无 val IC 数据 | — |


---


## 8. 代码层修复历史


### Fix 1: MSE Anchor 恢复对称 (v1→v2)
```python
# BEFORE (v1 — FATAL):
target_z_anchor = torch.where(target > 0, target_z, target_z * downside_dampening)
anchor_loss = anchor_weight * F.mse_loss(pred, target_z_anchor)


# AFTER (v2+):
target_z = (target - TARGET_MEAN) / TARGET_STD
anchor_loss = anchor_weight * F.mse_loss(pred, target_z)  # Always symmetric
```


### Fix 2: downside_dampening 0.05→0.3 (v1→v2)
```python
# v1: downside_dampening=0.05 (95% upside) → 丢弃 50% 数据 → 过拟合
# v2+: downside_dampening=0.3 (70% upside) → 保留 30% 正则化
```


### Fix 3: anchor_weight 0.001→0.01 (v3c→v4)
```python
# v3c: anchor_weight=0.001 (HPO 对称 Loss 最优) → Std_yhat 仍膨胀
# v4: anchor_weight=0.01 (Phase 3 默认, 10× 更强) → 待验证
```


---


## 9. OMEGA LESSONS 新增条目


| ID | 内容 | 公理 |
|----|------|------|
| C-024 | MSE Anchor dampening → Std_yhat 爆炸 + 过拟合。Anchor 必须对称 | Ω1 |
| C-025 | downside_dampening=0.05 → 丢弃 50% 数据 → 过拟合。最小 0.3 | Ω2 |
| C-026 | pipe 推理最优 (单 pass)，训练是瓶颈 (20 epoch)。训练必须 staging | Ω6 |
| C-027 | HPO 超参只对当时 Loss 有效。换 Loss 后 anchor 需重新标定 | Ω2 |


---


## 10. 待审计师判断的核心问题


1. **非对称 Pearson Loss 方向是否正确？**
   - v3c 证明 Train IC 可以从 0.066 (对称) 提升到 0.118 (非对称)
   - 但 Val IC 从 0.066 (对称) 降至 0.003 (非对称) — 泛化大幅退化
   - 这是 dampening/anchor 参数问题，还是非对称 Loss 本质不可泛化？


2. **anchor_weight=0.01 (v4) 是否足够？**
   - 0.001 太弱 (v3c 3 epoch 证据)
   - 0.01 是 Phase 3 初始默认值
   - 是否需要更高 (0.05, 0.1)？或者需要全新的 anchor 机制？


3. **Std_yhat 膨胀是否可以通过 anchor 完全控制？**
   - Pearson 是尺度不变的 — 模型有激励无限放大预测
   - 对称 MSE anchor 是唯一的尺度约束
   - 如果 anchor 太强 → IC Loss 被淹没 → 回退为纯 MSE
   - 是否需要引入其他尺度约束（如 pred 的 LayerNorm、gradient penalty）？


4. **非对称 Loss 是否需要配合架构修改？**
   - 当前 hd=64 在对称 Loss 下完美泛化 (OOS/IS=1.00)
   - 非对称 Loss 可能需要更大瓶颈 (hd=128) 来容纳更复杂的特征
   - 或者 INS-029 路径 B (双头阿修罗) 是否更适合？


---


## 11. Git 提交记录


```
0b2bf49 feat: Phase 9 — Leaky Asymmetric Pearson Loss (INS-030)
6157a3d perf: Gemini audit fixes — vectorize masking, pin_memory
ea00751 feat: Phase 9 GCS pipe mode + L4 job config + no_amp flag
516e536 fix: Phase 9 v1 catastrophic overfitting — MSE anchor must stay symmetric
f820d11 perf: Phase 9 v3 — Fat Node + Local SSD + On-demand
ab3fa20 docs: C-026 pipe vs staging
075621d fix: Phase 9 v4 — anchor_weight 0.001→0.01
```


---


*Generated 2026-03-30. All training logs sourced from Cloud Logging (Vertex AI ml_job).*
