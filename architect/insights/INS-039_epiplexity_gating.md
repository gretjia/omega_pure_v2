---
id: INS-039
title: Epiplexity Gating — z_sparsity 认知门控, 剥夺高熵赌徒资格
category: architecture
date: 2026-03-31
axiom_impact: UPDATE_REQUIRED
status: pending_p0_backtest
source_directive: phase11_asura_protocol + phase11_spear_protocol
source_gdoc: null
---

# INS-039: Epiplexity Gating — z_sparsity 认知门控

## 裁决
在回测模拟器的每日截面选股中，强行剔除 z_sparsity 位于后 50% (低压缩/高熵) 的股票，并过滤 |pred_bp| > 1000 的畸形预测。只有模型"真正完成拓扑压缩"的股票池中才允许排名选股。

## 理由
Phase 10 发现 3 证实: 低压缩 = 负 IC, 高 |pred| 对应低压缩。模型在高熵状态下靠暴力放大预测值盲目下注，而非真正理解市场结构。Epiplexity Gating 从执行层斩断这种作弊。

## 影响文件
- `tools/phase7_simulate.py`: 添加 z_sparsity 过滤逻辑 + |pred_bp| 截断
