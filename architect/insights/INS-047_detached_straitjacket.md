---
id: INS-047
title: Detached Straitjacket — detach(std) 斩断仿射黑洞
category: training
date: 2026-04-01
axiom_impact: UPDATE_REQUIRED
status: pending_phase11b
source_directive: phase11b_reforged_spear
source_gdoc: null
---

# INS-047: Detached Straitjacket

## 裁决
Z-score 的 std 必须 detach 且 clamp(min=1.0)。detach 打破尺度不变性，使梯度不再与权重正交，产生向内压缩引力。clamp(min=1.0) 防止 std→0 时 1/σ 梯度爆炸。

## 与 INS-040 的关系
INS-040 (方差之枷) 提出截面 Z-score，但未考虑梯度的仿射不变性陷阱。本洞察是 INS-040 的修正版: 保留 Z-score 的归一化效果，但通过 detach 阻断其梯度中的尺度漂移。

## 代码要点
```python
safe_std = torch.clamp(logit_std, min=1.0).detach()
locked_logits = (raw_logits - logit_mean) / safe_std
```
- detach: 反传时 safe_std 视为常数 → ∂locked/∂raw = 1/safe_std (常数) → 无 1/σ 放大
- clamp(min=1.0): 即使 raw std < 1，除数仍为 1.0 → 梯度不放大

## 影响文件
- `train.py`: compute_spear_loss 中的 Z-score 改为 detached
