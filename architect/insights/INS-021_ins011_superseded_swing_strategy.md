---
id: INS-021
title: INS-011 废弃 — 日内约束→中长期波段（Swing Trading）
category: architecture
date: 2026-03-29
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirm
source_directive: 2026-03-29_compression_is_intelligence_phase7_golive.md
source_gdoc: null
supersedes: INS-011
---

# INS-021: INS-011 废弃 — 日内约束→中长期波段（Swing Trading）

## 裁决
INS-011（严格日内，禁止隔夜）基于错误假设"信号是秒到分钟级 LOB 微观 Alpha"。实际核心论点是检测数月级主力行为（建仓/拉升/派发），强制日内平仓等于在主力建仓期截断肥尾。正式废弃 INS-011，转向中长期波段策略。

## 理由

### 核心冲突
- INS-011 假设：LOB Alpha 半衰期 = 秒到分钟 → 日内必须平仓
- 实际论点：主力行为周期 = 数周到数月 → 持仓必须跨日
- Volume-Clock 物理：20 bars = 40% ADV = 数天到数周（取决于流动性）

### 新回测约束
- `overnight_exposure: true` — 主力行为必然跨日
- `holding_horizon: 20 volume bars` — 自然到期（非强制日内平仓）
- `exit_strategy: volume_clocked_natural_horizon + trailing_stop`
- `trailing_stop: -10%` — 防止单笔灾难（洗盘保护）
- `cost_model.round_trip_bp: 25` — 含冲击成本（从 11 BP 上调）
- `success_criterion: asymmetry_payoff_ratio > 3.0 AND profit_factor > 1.5`

### Taleb 反脆弱对齐
- 低胜率可接受（>35%），关键是肥尾收益
- Sortino > 1.5（只惩罚下行，不惩罚上行爆发）
- 盈亏平衡成本 > 40 BP（安全边际）

## 影响文件
- `architect/current_spec.yaml` (lines 149-153): 重写 backtest 节
- `architect/insights/INS-011_intraday_only_backtest.md`: status→SUPERSEDED
- `CLAUDE.md`: 添加"主力行为检测"核心论点段落
- `tools/phase7_simulate.py`: 新建，滚动组合模拟器
