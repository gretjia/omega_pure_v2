---
id: INS-033
title: Softmax Portfolio Loss — 从统计相关性到交易逻辑的范式跃迁
category: training
date: 2026-03-30
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirm
source_directive: 2026-03-30_metric_collapse_softmax_portfolio_loss.md
source_gdoc: null
---

# INS-033: Softmax Portfolio Loss — 从统计相关性到交易逻辑的范式跃迁

## 裁决

彻底抛弃 Pearson IC Loss，换上 Softmax Portfolio Loss（Learning to Rank 范式）。直接将"只做多、赢家通吃"的真实交易逻辑写进 Loss 函数，用 Softmax 归一化的虚拟资金权重 × 真实 target 收益作为训练目标。

## 理由

- Softmax 是指数级"赢家通吃"：预测排名后 50% 的股票权重趋近 0 → 反向传播梯度为 0 → **自动切断对高熵派发噪音的学习**
- 免疫尺度爆炸：Softmax 归一化到概率分布，天然约束在 [0,1]
- 无梯度冲突：单一目标（组合收益），不需要 Pearson vs MSE anchor 的多头博弈
- 与 INS-028（压缩悖论）完美对接：hd=64 的全部容量 100% 用于压缩低熵建仓拓扑
- Target 保持纯对称（不篡改物理真相），非对称性内生于 Softmax 指数结构

## 关键参数

- `temperature`: 1.0（控制 Softmax 锐度，越低越接近 argmax）
- `l2_weight`: 1e-4（极微弱 L2，取代 MSE anchor）
- `lambda_s`: 1e-7（保留 MDL 稀疏约束，与 INS-019 隐式压缩一致）

## 影响文件

- `train.py` / `gcp/train.py`: 移除 Pearson/MSE anchor/dampening，植入 softmax_portfolio_loss
- `architect/current_spec.yaml`: training section 全面重构
- `hpo` section: metric 从 "1-IC" 变为组合收益相关
