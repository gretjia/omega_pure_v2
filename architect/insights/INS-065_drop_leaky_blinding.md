---
id: INS-065
title: "Drop Leaky Blinding — 负收益梯度 100x 压缩导致波动率预测"
category: training
date: 2026-04-04
axiom_impact: UPDATE_REQUIRED
status: active
audit_status: draft
source_directive: "2026-04-04_phase13_audit_verdict_and_roadmap.md"
source_gdoc: null
---

# INS-065: Drop Leaky Blinding

## 裁决
立即删除 Leaky Blinding（负收益×0.1）。长空约束属于投资组合执行层，不属于 Loss 函数的 target 空间。

## 理由
Gemini 数学证明：leaky_factor=0.1 将负收益 MSE 梯度压缩 0.1²=**100 倍**。模型被数学激励忽略负收益，退化为波动率预测器。D9 hit_rate (49%) < D0 hit_rate (51.4%) 是铁证——模型选高波动股，不是高收益股。pred_mean=34.42 精确匹配变换目标期望 32.07 BP。

## 前提假设
- **数据格式**: target 已在 BP (ETL: `omega_etl_v3_topo_forge.py:176` 做 ×10000)
- **上游依赖**: 无，直接删除 leaky blinding 即可
- **环境假设**: 与 IC Loss 回归联合执行（INS-066）

## 被拒绝的替代方案
- **方案 B**: 降低 leaky_factor 到 0.5 → 拒绝: 仍 4x 梯度不对称，治标不治本
- **方案 C**: 对称 clamp ±500 BP → 拒绝: 不解决 MSE 的条件均值退化问题

## 验证协议
1. 验证命令: 删除后训练 2 epoch smoke test，检查 D9 hit_rate > D0 hit_rate
2. 预期结果: D9 和 D0 的 hit_rate 差距缩小或反转
3. 失败回退: 如果模型发散，先用对称 clamp ±500 再排查

## 参数标定来源
- 🔬 **实测标定**: Gemini 数学推导 E[T_leaky]=72.07 BP, 实测 pred_mean=34.42 BP 确认

## 影响文件
- `omega_epiplexity_plus_core.py`: ���除 `compute_spear_loss_unbounded` 中的 leaky blinding 逻辑
- `train.py`: 删除 `--leaky_factor` ��数
- `architect/current_spec.yaml`: 删除 `training.leaky_factor`

## spec 参数映射
- `spec.training.leaky_factor` → 删除
- `spec.training.loss_function` → 删除 leaky blinding 步骤
