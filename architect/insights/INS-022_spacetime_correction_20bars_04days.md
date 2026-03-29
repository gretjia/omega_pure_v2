---
id: INS-022
title: 时空换算修正 — 20 bars = 0.4 天，非"数天到数周"
category: physics
date: 2026-03-29
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirm
source_directive: 2026-03-29_spacetime_correction_phase7_golive_v2.md
source_gdoc: null
corrects: INS-021 (holding_horizon 时间尺度推算错误)
---

# INS-022: 时空换算修正 — 20 bars = 0.4 天，非"数天到数周"

## 裁决
Volume-Clock 下 1 bar = 2% ADV。任何股票在平均交易日生成 100%/2% = 50 bars。因此 20 bars = 20/50 = **0.4 个交易日**（约半天），绝非"数天到数周"。之前 INS-021 和 Phase 7 计划中的时间尺度推算是数学错误。

## 理由

### 数学证明
- ADV = 日均成交量（Average Daily Volume）
- 1 bar = 2% × ADV（etl.adv_fraction = 0.02）
- 1 天 = 100% ADV = 50 bars
- **与股票流动性无关**：大盘股和微盘股每天都流逝 50 bars（Volume-Clock 的本质就是消除大小盘异质性）

### 模型物理尺度还原
| 参数 | Volume Bars | 日历时间 |
|------|------------|---------|
| macro_window=160 | 160 bars | ~3.2 天（与 spec 注释"~3天宏观建仓周期"吻合）|
| window_size_t=32 | 32 bars | ~0.64 天（注意力窗口 ≈ 半天）|
| payoff_horizon=20 | 20 bars | ~0.4 天（预测未来 ≈ 半天）|

### 正确的策略定位
OMEGA 是 **T+1 隔夜波段模型**：
- 用 3 天盘口历史（160 bars），通过 SRL 反演照出今天的元订单方向
- 预测接下来半天（20 bars）的价格走势
- A股 T+1 强制隔夜 → 第二天早盘享受建仓惯性溢价
- 核心定义：**捕捉主力长线建仓中的微观执行切片**

### INS-021 修正
INS-021 的结论（废弃 INS-011、overnight_exposure=true）仍然正确，但理由不同：
- 旧理由（错误）：持仓数天到数周，隔夜是自愿选择
- 新理由（正确）：持仓 0.4 天，但 T+1 强制锁过夜，隔夜是物理约束

## 影响文件
- `architect/current_spec.yaml`: backtest.holding_horizon 描述修正
- `CLAUDE.md`: 时间尺度叙述从"数月级策略"修正为"T+1 隔夜波段"
- `tools/phase7_simulate.py`: 持仓逻辑从"自然到期 20 bars"改为"T+1 锁 + 到期退出"
- Phase 7 计划文件: 修正所有"数天到数周"的表述
