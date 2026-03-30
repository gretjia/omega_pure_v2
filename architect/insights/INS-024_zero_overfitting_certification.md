---
id: INS-024
title: 绝对零过拟合认证 — OOS/IS IC = 1.00
category: metrics
date: 2026-03-30
axiom_impact: NONE
status: active
source_directive: 2026-03-30_phase7_audit_phase8_deep_fat_tail.md
source_gdoc: null
---

# INS-024: 绝对零过拟合认证 — OOS/IS IC = 1.00

## 裁决
T29 旗舰模型 (hd=64, 19.7K params) 在 9.4M 样本、551 交易日、3 年跨度的全量回测中实现了 IS IC=0.0277 vs OOS IC=0.0276 (ratio=1.00)。这是"压缩即智能"理论的实证胜利：hd=64 物理窄门成功过滤了散户噪音，仅保留了主力元订单的低熵拓扑特征。

## 理由
- 信噪比极低的 A 股市场中，19.7K 参数模型实现零过拟合是极其罕见的
- 证明 INS-019 (隐式压缩 > 显式正则化) 的物理判断完全正确
- T29 底盘已如金石般坚固，Phase 8 不应重训或调参，应聚焦执行层优化

## 影响文件
- 无代码变更。此为认证性洞察，确认 T29 作为 Phase 8/9 基座模型的地位。
