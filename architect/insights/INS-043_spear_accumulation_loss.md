---
id: INS-043
title: 建仓 Epiplexity Loss — 交叉熵 + 右尾归一化目标 + MDL
category: training
date: 2026-03-31
axiom_impact: UPDATE_REQUIRED
status: pending_p0_backtest
source_directive: phase11_spear_protocol
source_gdoc: null
---

# INS-043: 建仓 Epiplexity Loss (Spear Accumulation Loss)

## 裁决
训练损失从 Softmax Portfolio Loss (INS-033) 演进为 Spear Accumulation Loss:
```
target_prob = clamp(target, min=0) / (sum(clamp(target, min=0)) + eps)
pred_prob = softmax(locked_logits / T, dim=cross_section)
loss = -sum(target_prob * log(pred_prob)) + lambda_s * ||z_core||_1
```

## 与 Phase 10 Loss 的关键差异
| 维度 | Phase 10 | Phase 11 Spear |
|------|----------|----------------|
| Target | raw return (正负都有) | **clamp(min=0)** 只保留正收益 |
| Logits | raw (Std=4540 BP) | **Z-scored** (Std=1.0) |
| Loss 类型 | weighted sum | **交叉熵** (target 归一化为概率) |
| 熊市行为 | 强行拟合噪音 | **MDL 主导, 自动静默** |
| Temperature | 1.0 (被 logit inflation 架空) | 1.0 (由 Z-score 保护) |

## 理由
1. 交叉熵天然度量 pred 与 target 分布的 KL 散度
2. Right-tail-only target 归一化后成为合法概率分布
3. 熊市 (全跌) 时 target_prob→均匀分布, loss 梯度趋零, MDL 接管 → 安全静默

## 影响文件
- `train.py`: 完整替换 loss 计算逻辑
- `omega_epiplexity_plus_core.py`: 无变更
