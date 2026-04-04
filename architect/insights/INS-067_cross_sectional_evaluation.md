---
id: INS-067
title: "Cross-Sectional Evaluation — D9-D0 必须按日期截面排序"
category: metrics
date: 2026-04-04
axiom_impact: UPDATE_REQUIRED
status: active
audit_status: draft
source_directive: "2026-04-04_phase13_audit_verdict_and_roadmap.md"
source_gdoc: null
---

# INS-067: Cross-Sectional Evaluation (CRITICAL)

## 裁决
重构 `validate()` 和 `backtest_5a.py`，D9-D0 和 Rank IC 必须按日期截面排序后聚合。删除全局 `torch.topk` 混合所有日期的做法。

## 理由
当前 `validate()` 对所有 val 样本全局排序。如果策略是每日 rebalance（截面选股），全局排序会将"跨日期的波动率差异"误判为"模型判别力"。Codex 架构审计判定此为 BONUS CRITICAL。-29σ Rank IC 可能部分是全局波动率排序的伪信号。

## 前提假设
- **数据格式**: WebDataset shard 按日期组织，每个 shard 的样本属于同一交易日（或可通过 date_map 恢复日期信息）
- **上游依赖**: 推理管线需要输出 date/symbol 信息（gcp/phase7_inference.py 已有）
- **环境假设**: 训练时 batch 内混合多日期 — validate 需要收集全部 pred/target 后按日期分组

## 被拒绝的替代方案
- **方案 B**: 按 shard 做截面排序 → 拒绝: shard 不一定对应一个日期
- **方案 C**: 只在 post-flight 做截面分析 → 拒绝: 训练时 best.pt 选择也需要正确指标

## 验证协议
1. 验证命令: 用 Phase 12 best.pt predictions parquet，按 date 分组计算 cross-sectional D9-D0，对比全局 D9-D0
2. 预期结果: 如果全局波动率是主因，cross-sectional D9-D0 应该接近 0 或反转
3. 失败回退: 如果 cross-sectional D9-D0 与全局一致，说明波动率伪信号不是主因

## 参数标定来源
- 🎯 **架构师直觉**: 截面排序是量化投资标准做法，**待实测标定**（全局 vs 截面差异大小）

## 影响文件
- `train.py`: `validate()` 函数重构，按日期分组计算 D9-D0
- `backtest_5a.py`: 添加按 date 分组的十分位分析
- `tools/postflight_analysis.py`: 添加 cross-sectional 分析模式
- `architect/current_spec.yaml`: 更新 `hpo.metric` 定义

## spec 参数映射
- `spec.hpo.metric` → "Cross-Sectional D9-D0 Spread (per-date, then average)"
