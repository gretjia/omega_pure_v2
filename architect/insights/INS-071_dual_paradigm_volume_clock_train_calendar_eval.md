---
id: INS-071
title: "Dual-Paradigm — Volume Clock Training + Calendar Evaluation"
category: architecture
date: 2026-04-04
axiom_impact: NONE
status: active
audit_status: final
source_directive: "2026-04-04_phase13_recursive_audit_and_joint_arbitration.md"
source_gdoc: null
---

# INS-071: Dual-Paradigm — Volume Clock 训练 + Calendar 严格评估

## 裁决
训练和评估采用不同的时间范式：训练期用 Volume Clock 下的 Batch-Level IC（保持流动性均质化），评估期用日历日截面（匹配真实交易结算）。严禁在评估中使用 Global Top-K。

## 理由
- **训练期**: 强行在 Loss 层面按日历日分组会粉碎 Volume Clock 预设的"等流动性信息熵"假设，导致梯度被高流动性股票主导（高流动性股 ~50 samples/天 vs 低流动性股 ~5 samples/天）
- **评估期**: 真实世界交易按日历日结算，资金每日截面分配。全局排序混合了"跨日期波动率差异"和"模型判别力"（Phase 6 Post-Flight D9-D0=-5.92 BP 的根因）
- **Batch IC 合理性**: Dataloader 全局 Shuffle 下，一个 Batch(256) 构成混合流动性的"微观随机伪截面"，足以教导网络学习相对强弱关系

## 前提假设
- **数据格式**: Batch 包含来自不同日期、不同股票的混合 volume bars — 验证方法: `grep -n "shuffle" omega_webdataset_loader.py`
- **上游依赖**: ETL v4 添加 date 字段后，评估期才能实现真正的 per-date 截面。当前为 [APPROXIMATION]
- **环境假设**: ETL v3 shard meta.json 无 date 字段（实测确认 2026-04-04）

## 被拒绝的替代方案
- **方案 B**: 训练期也按日历日分组 IC → 拒绝原因: 粉碎 Volume Clock 等流动性假设，高流动性股主导梯度
- **方案 C**: 全局 Batch IC 评估 → 拒绝原因: 全局排序混合日期间市场均值漂移，产生波动率幻觉（Phase 6/12 实证）

## 验证协议
1. Phase 13 Post-Flight 使用 ETL v4 shards（含 date 字段）执行 per-date D9-D0 和 Rank IC
2. 对比 global vs per-date 指标差异：若全局 D9-D0 >> per-date D9-D0，确认波动率幻觉存在
3. 预期：per-date Rank IC 应为正值（如果模型确实学到了截面排序能力）

## 参数标定来源
- 🔬 **实测标定**: Batch-level IC 的有效性待 Phase 13 训练实测验证
- 📐 **理论推导**: Shuffle 构成伪截面 — 来自大数定律 + 随机抽样理论

## 影响文件
- `backtest_5a.py`: 必须改为 per-date 分组评估（依赖 ETL v4 date 字段）
- `tools/postflight_analysis.py`: 添加 per-date 截面指标
- `omega_webdataset_loader.py`: ETL v4 后需提取 date 字段

## spec 参数映射
- `spec.training.loss_function` → 已标记 [APPROXIMATION: batch-level IC]
- `spec.hpo.primary_metric` → 已标记 [APPROXIMATION: global Spearman]
- `spec.inference.scaling` → `daily_cross_sectional_zscore`（已实现）
