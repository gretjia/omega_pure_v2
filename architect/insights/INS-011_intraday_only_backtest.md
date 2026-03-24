---
id: INS-011
title: 回测改为严格日内 — LOB 微观 Alpha 不可扛隔夜
category: architecture
date: 2026-03-24
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirm
source_directive: 2026-03-24_mean_collapse_diagnosis_and_phase4_6_audit.md
source_gdoc: null
---

# INS-011: 严格日内回测 — 禁止 T+1 隔夜暴露

## 裁决
LOB 微观结构信号的 Alpha 记忆半衰期只有秒到分钟级，T+1 隔夜跳空由宏观新闻决定，LOB 对此致盲。强制 T+1 隔夜风险暴露会让微观 Alpha 被宏观噪音碾碎。改为严格日内（收盘前强制平仓）。同时 asymmetry_payoff_ratio > 3.0 必须叠加 Expectancy > Slippage + Fee。

## 理由
- 物理学时空撕裂：微观 LOB（秒级）vs 隔夜跳空（宏观）
- 不对称比率 3.0 不保证盈利：极低胜率 + 高赔率仍可能破产
- 量化金融第一性原理：信号半衰期必须匹配持仓周期

## 影响文件
- `architect/current_spec.yaml`: backtest.t_plus_1_exposure, backtest.success_criterion
