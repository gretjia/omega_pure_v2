---
id: INS-036
title: Softmax 尺度失控 — 方差惩罚或 Logits LayerNorm 物理锁
category: training
date: 2026-03-31
axiom_impact: UPDATE_REQUIRED
status: pending_p0_backtest
source_directive: post_phase10_three_campaigns
source_gdoc: null
---

# INS-036: Softmax 尺度失控 — 方差惩罚或 Logits LayerNorm 物理锁

## 裁决

Phase 10 的 L2 mean-shift (`l2_weight * mean(pred)^2`) 必须替换。Softmax 的平移不变性使得均值惩罚无法约束尺度膨胀。需要引入方差惩罚（损失函数级）或 Logits LayerNorm（架构级）来物理锁定预测值的截面离散度。

## 理由

Softmax 函数满足 `softmax(x) = softmax(x + c)`，L2 mean-shift 只能拉回均值但无法约束极差。网络为最大化 PfRet 会无限放大 logits 尺度（隐式降低 Temperature 逼近 One-hot），导致：
1. `Std_yhat` 膨胀至 5055 BP（正常应在 ~100 BP 量级）
2. 实盘中微小噪声被放大，满仓单只股票的集中度灾难
3. OOS/IS Ratio = 1.38 的反常值可能部分源于此

## 两种修复方案

**方案 A: 损失函数级方差惩罚**（最小侵入性）
```python
logits_variance = torch.var(pred, dim=-1)
variance_penalty = l2_weight * torch.mean(F.relu(logits_variance - 10000.0))
```
- 优点：只改 loss，不改网络结构
- 缺点：需要调参（方差阈值 10000 = 100 BP^2）

**方案 B: 架构级 Logits LayerNorm**（架构师推荐）
```python
pred = F.layer_norm(raw_pred, normalized_shape=(1,)) * BASE_SCALE_BP
```
- 优点：无参数，Std 物理锁死在常数级别
- 缺点：可能限制模型表达力

## 影响文件

- `omega_epiplexity_plus_core.py`: 修改 IntentDecoder 输出层 或 loss 计算
- `train.py`: 如选方案 A，修改 loss 计算逻辑
- `architect/current_spec.yaml`: 更新 training.loss 公式

## spec 变更预案

```yaml
# 当前
training.loss: "-sum(softmax(pred/T) * target_cs_z) + l2_weight * mean(pred)^2 + lambda_s * ||z_core||_1"

# 方案 A
training.loss: "-sum(softmax(pred/T) * target_cs_z) + l2_weight * mean(relu(var(pred) - 10000)) + lambda_s * ||z_core||_1"

# 方案 B
model.intent_decoder.output_norm: "layer_norm"
model.intent_decoder.base_scale_bp: <TBD>
training.loss: "-sum(softmax(pred/T) * target_cs_z) + lambda_s * ||z_core||_1"  # L2 项被 LayerNorm 物理替代
```
