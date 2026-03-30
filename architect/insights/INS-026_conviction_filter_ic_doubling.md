---
id: INS-026
title: 确信度过滤 — |pred-median|>30 BP 时 IC 翻倍至 0.054
category: architecture
date: 2026-03-30
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-30_phase7_audit_phase8_deep_fat_tail.md
source_gdoc: null
---

# INS-026: 确信度过滤 — |pred-median|>30 BP 时 IC 翻倍至 0.054

## 裁决
Phase 8 模拟器必须实装 Conviction Filter：仅在预测值偏离日内中位数超过阈值 (建议 20-30 BP) 时才开仓。Phase 7 Test #4.8 证实 IC 从 0.028 暴涨至 0.054 (ICIR 0.38→0.47)，每日仍有 864 只候选股票，足够建仓。放弃"每天无脑买满 Top 20%"，宁可空仓也不做低确信度交易。

## 理由
- 14,477 笔交易中大量是信号噪音区的勉强凑数 — 拖累了整体不对称比
- 高确信度信号对应更强的主力建仓拓扑特征，低确信度信号本质是随机噪音
- "Cash is a position" 是 Taleb 反脆弱的核心策略
- 不需要重训模型，纯执行层改进

## 影响文件
- `tools/phase7_simulate.py`: 添加 `--conviction_threshold` 参数，在 Step 2 候选筛选中加入 `pred > daily_median + threshold` 过滤
- `architect/current_spec.yaml`: backtest 节添加 `conviction_filter` 配置
