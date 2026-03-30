---
id: INS-035
title: Phase 9 非对称 Pearson Loss 终极验尸 — 7 jobs 全败，死路确认
category: training
date: 2026-03-30
axiom_impact: NONE
status: active
source_directive: 2026-03-30_metric_collapse_softmax_portfolio_loss.md
source_gdoc: null
---

# INS-035: Phase 9 非对称 Pearson Loss 终极验尸 — 7 jobs 全败，死路确认

## 裁决

Phase 9 的 7 个 Vertex AI job（v1→v4）构成了一次完美的控制实验，最终证明非对称 Pearson Loss 是结构性死路而非参数调优问题。所有尝试的失败模式收敛到同一根因：Pearson 尺度免疫 + dampening = Reward Hacking。

## 理由

实验证据链：
- v1 (dampening=0.05, 不对称 anchor): 灾难性过拟合 (Train IC=0.18, Val IC=-0.001)
- v2b (dampening=0.3, 对称 anchor, anchor_wt=0.001): Spot 抢占（数据不完整）
- v3c (dampening=0.3, 对称 anchor, anchor_wt=0.001): Val IC 单调下降 0.006→0.004→0.003
- v4 (dampening=0.3, 对称 anchor, anchor_wt=0.01): 未完成（架构师判死刑）

失败模式分类：
1. anchor 太弱 → Std(ŷ) 爆炸 → Reward Hacking（v1, v3c）
2. anchor 够强 → MSE 主导 → 退化回对称预测器（v4 预期结局）
3. 不存在"恰好"的平衡点 → 结构性矛盾

**教训**: 统计度量（Pearson IC）的尺度不变性与非对称 dampening 的组合，在数学上不可能实现"压缩即智能"。必须转向直接优化交易目标（Softmax Portfolio Loss）。

## 影响文件

- `OMEGA_LESSONS.md`: 需追加 C-028 (Pearson + dampening = Reward Hacking 死路)
- `handover/LATEST.md`: Phase 9 状态从 "paused" 更新为 "postmortem_complete"
