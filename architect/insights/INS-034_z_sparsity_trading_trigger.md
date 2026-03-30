---
id: INS-034
title: z_sparsity 作为交易扳机 — 高压缩率 = 主力控盘铁证
category: architecture
date: 2026-03-30
axiom_impact: NONE
status: pending_implementation
source_directive: 2026-03-30_metric_collapse_softmax_portfolio_loss.md
source_gdoc: null
---

# INS-034: z_sparsity 作为交易扳机 — 高压缩率 = 主力控盘铁证

## 裁决

将 z_core 的稀疏度（hd=64 神经元中接近 0 的比例）导出到推理输出，作为实盘交易的第二过滤器。只有当 Prediction Rank 位于 Top 10% **且** z_sparsity 超过高压缩率阈值时，才执行做多。

## 理由

- **高 Sparsity**（大量神经元静默）: 模型用极短的"代码长度"完美压缩了信号 → 遇到经典低熵主力建仓算法
- **低 Sparsity**（神经元散乱全亮）: 盘口散户乱战，噪音太高无法压缩 → 应回避
- 这是 INS-019（隐式压缩胜利: hd=64 物理瓶颈）和 INS-028（压缩悖论: 建仓低熵可压缩）的实盘兑现
- Phase 7 报告已指出 z_sparsity 未包含在推理输出中，是关键缺失

## 影响文件

- `inference_7.py` / 推理脚本: 导出 z_core sparsity 到输出 parquet
- `omega_epiplexity_plus_core.py`: 可能需要在 forward 中返回 z_core 稀疏度统计
- 回测模拟器: 加入 z_sparsity 过滤条件
