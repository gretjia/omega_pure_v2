---
id: INS-017
title: 先锋定标战役 — T16 全量收敛 + Std(ŷ) 截面监控
category: training
date: 2026-03-27
axiom_impact: NONE
status: pending_execution
source_directive: 2026-03-27_vanguard_convergence_protocol.md
source_gdoc: null
---

# INS-017: 先锋定标战役 — T16 全量收敛 + Std(ŷ) 截面监控

## 裁决
用 T16 最优超参做 20 epoch 全量训练（vs RECON 的 8 epoch），监控 Std(ŷ) 截面方差扩展。结果决定是继续 HPO exploitation（PASS）还是架构级改造 Loss/Target（FAIL）。

## 理由
Phase 5a 显示欠训练模型(40K steps, 0.6 passes)无截面区分度。所有 decile 的 mean return 无差异。这可能是：
1. 训练不足（火候不够）→ 全量训练可解决
2. Loss 函数本质缺陷（MSE 均值回归）→ 需架构改造

单次全量训练（~$10）可在一天内区分这两种可能性，避免在错误方向上浪费 $500+ HPO 预算。

## 影响文件
- `train.py`: 添加 Std(ŷ) 监控到训练日志
- `backtest_5a.py`: 无变更（用新模型重跑）
- `gcp/`: 新建 Vanguard 训练配置
