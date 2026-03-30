---
id: INS-027
title: 宏观气候雷达 — 熊市 IC≈0 时强制减仓
category: architecture
date: 2026-03-30
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-30_phase7_audit_phase8_deep_fat_tail.md
source_gdoc: null
---

# INS-027: 宏观气候雷达 — 熊市 IC≈0 时强制减仓

## 裁决
Phase 8 模拟器必须加盖宏观风控层：当市场处于系统性崩盘期 (2023Q3 IC=0.002)，强制降低仓位上限或提高 Conviction 阈值。微观主力信号在泥沙俱下的恐慌中完全失效，此时暴露等于自杀。

## 理由
- Phase 7 Test #4.5: 2023Q3 IC=0.002 (ICIR=0.04)，信号与随机无异
- 全年 -20.09% 回撤主要来自 2023 年熊市暴露
- 主力在系统性崩盘中自身被套，元订单惯性不复存在
- 候选实现方式：沪深300 20日动量 / 全A涨跌停比 / 外生市场状态因子
- 不需要重训模型，纯执行层改进

## 影响文件
- `tools/phase7_simulate.py`: 添加 `--regime_filter` 参数和市场状态判断逻辑
- `architect/current_spec.yaml`: backtest 节添加 `regime_conditioning` 配置
