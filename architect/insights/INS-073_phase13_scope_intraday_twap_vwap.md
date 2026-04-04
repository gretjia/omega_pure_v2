---
id: INS-073
title: "Phase 13 Scope Downgrade — Intraday TWAP/VWAP Friction"
category: architecture
date: 2026-04-04
axiom_impact: NONE
status: active
audit_status: final
source_directive: "2026-04-04_phase13_recursive_audit_and_joint_arbitration.md"
source_gdoc: null
---

# INS-073: Phase 13 范围降级 — 日内 TWAP/VWAP 拆单摩擦

## 裁决
Phase 13 的目标正式降级为"捕获机构日内微观执行 (TWAP/VWAP 拆单) 的订单簿摩擦与冲击"。0.64 天感受野足以看清日内结构。跨窗口注意力（打破时间孤岛）推迟到 Phase 14 作为独立核心任务。

## 理由
- **控制变量法**: Phase 13 已同时改了 5 个变量（Loss/Target/Pooling/Residual/Regularization），再加窗口拓扑=第6个变量，归因灾难
- **0.64 天已足够**: 32 volume bars × 2% ADV / ~50 bars/天 ≈ 0.64 交易日，足以捕获日内 TWAP/VWAP 执行的微观冲击模式
- **Phase 13 成功标准降级**: 只要跑出"稳定单调正向截面 Rank IC"，引擎即点火成功
- **多日建仓检测**: 机构 3+ 天建仓周期需要跨窗口信息流，这是 Phase 14 (INS-070) 的专属任务

## 前提假设
- **物理假设**: 日内 TWAP/VWAP 拆单在 0.64 天窗口内可观测（合理——单日拆单是常见执行策略）
- **上游依赖**: INS-070（跨窗口注意力）已就绪等待 Phase 14 实施
- **隐含假设**: 日内微观信号虽弱于多日建仓信号，但应该是非零的、可测量的

## 被拒绝的替代方案
- **方案 B**: Phase 13 直接实现跨窗口注意力 → 拒绝原因: 6 个同时变量导致归因灾难
- **方案 C**: 扩大 window_size_t 到 64 或 128 → 拒绝原因: 仍在隔离窗口内，只是单窗变大，attention 计算量 O(n²) 增长，且不解决跨窗信息流问题

## 验证协议
1. Phase 13 Post-Flight: per-date Rank IC > 0 证明日内信号存在
2. Phase 14 对比: 加入跨窗口注意力后 Rank IC 增量量化多日建仓信号贡献
3. 失败回退: 如 Phase 13 Rank IC ≤ 0，可能日内信号不存在，需重新审视整体策略

## 参数标定来源
- 📐 **理论推导**: 0.64 天 = 32 bars × 2% ADV / 50 bars/day（INS-022 时空换算）
- 🎯 **架构师直觉**: "日内 TWAP/VWAP 拆单摩擦可捕获" — **待 Phase 13 实测验证**

## 影响文件
- `architect/current_spec.yaml`: INS-070 DRAFT 标签需标注 "Phase 14"
- 无代码变更（Phase 13 代码已冻结）

## spec 参数映射
- `spec.model_architecture.layer_2_topology` → INS-070 cross-window attention 标注为 Phase 14
