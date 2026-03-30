---
id: INS-030
title: Leaky Asymmetric Pearson Loss — downside_dampening=0.05
category: training
date: 2026-03-30
axiom_impact: UPDATE_REQUIRED
status: pending_phase9
source_directive: 2026-03-30_phase9_asymmetric_evolution_leaky_pearson.md
source_gdoc: null
---

# INS-030: Leaky Asymmetric Pearson Loss — downside_dampening=0.05

## 裁决
Phase 9 将 IC Loss 从对称 Pearson 替换为 Leaky Asymmetric Pearson：target_cs_z < 0 的样本目标值乘以 0.05（保留 5% 梯度防止 NaN，但 95% 的协方差权重由暴涨股主导）。这不是硬截断 clamp(min=0)（有除零风险），而是 Leaky 版本。

## 理由
- Phase 8 证明 asymmetry 1.20 在对称 IC Loss 下数学不可达（12-run sweep，所有配置 asym ∈ [1.18, 1.21]）
- INS-025: 对称 Loss 让模型退化为"波动率雷达"，上下尾部捕获率对称 (2.01x vs 1.84x)
- INS-028: 建仓=低熵可压缩，派发=高熵不可压缩。对称 Loss 浪费 50% 瓶颈容量在高熵噪音上
- 架构师安全警告：硬 clamp 可能导致 batch 内全负时 std=0 → NaN。Leaky 版本保留微弱梯度避免此问题
- 物理意义：hd=64 的全部容量用于压缩"主力建仓拉升的低熵拓扑"

## 影响文件
- `train.py`: 替换 loss function (pearson_correlation_loss → asymmetric_pearson_loss)
- `architect/current_spec.yaml`: training.loss 字段更新
- 不修改模型架构 (T29 hd=64 锁定)
- 不修改超参 (lr/lambda_s/wu/bs 全部复用 Phase 6 HPO 最优)

## 具体代码
```python
def asymmetric_pearson_loss(pred, target_cs_z, downside_dampening=0.05, eps=1e-8):
    target_asymmetric = torch.where(
        target_cs_z > 0,
        target_cs_z,
        target_cs_z * downside_dampening
    )
    pred_flat = pred.view(-1)
    target_flat = target_asymmetric.view(-1)
    pred_centered = pred_flat - pred_flat.mean()
    target_centered = target_flat - target_flat.mean()
    cov = torch.sum(pred_centered * target_centered)
    pred_std = torch.sqrt(torch.sum(pred_centered**2) + eps)
    target_std = torch.sqrt(torch.sum(target_centered**2) + eps)
    corr = cov / (pred_std * target_std)
    return 1.0 - corr
```
