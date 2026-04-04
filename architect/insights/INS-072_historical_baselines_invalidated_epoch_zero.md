---
id: INS-072
title: "Historical Baselines Invalidated — Phase 13 = Epoch 0"
category: metrics
date: 2026-04-04
axiom_impact: UPDATE_REQUIRED
status: active
audit_status: final
source_directive: "2026-04-04_phase13_recursive_audit_and_joint_arbitration.md"
source_gdoc: null
---

# INS-072: 历史基线彻底作废 — Phase 13 = Epoch 0

## 裁决
Phase 6 及之前的所有基线数据正式作废。Phase 13 是 OMEGA v3 的 Ground Zero（归零），一切优化以 Phase 13 Post-Flight 实测截面表现为唯一锚点。原 "IC Loss 比 MSE 好 13 倍" 的定量结论作废（定性结论仍成立）。

## 理由
- **Phase 6 IC=0.066 不可信**: C-062 记录了 `torch.compile` 的 `_orig_mod.` 前缀 bug，可能导致推理时使用随机权重
- **Phase 6 D9-D0=-5.92 BP**: 深度负值证明即使 IC 看似高，实际截面排序完全失败
- **全局排序污染**: 历史所有 Phase 的评估都使用 Global Top-K，与截面排序能力脱节
- **架构师原话**: "沙地上的建筑没有参考价值"

## 前提假设
- **上游依赖**: C-062 torch.compile bug 确实影响了 Phase 6 推理（高置信度，但未做完整复现）
- **隐含假设**: Phase 13 的架构改进（IC Loss + AttentionPooling + Residual）足以产生可测量的正向截面信号

## 被拒绝的替代方案
- **方案 B**: 保留 Phase 6 作为"参考基准" → 拒绝原因: torch.compile bug + 全局排序伪影使数据不可靠，保留会误导后续决策
- **方案 C**: 重跑 Phase 6 修复 bug 后重新建基线 → 拒绝原因: Phase 6 架构（Mean Pooling + 无残差）已被证伪，重跑无价值

## 验证协议
1. Phase 13 Post-Flight 将建立新的基线：per-date Rank IC 和 per-date D9-D0
2. 成功标准：稳定单调的正向截面 Rank IC（具体阈值待 Phase 13 数据确定）
3. 失败回退：如 Phase 13 Rank IC ≤ 0，需重新审视架构假设

## 参数标定来源
- 🔬 **实测标定**: Phase 13 Post-Flight 将提供新的标定锚点
- 🎯 **架构师直觉**: "稳定单调正向截面 Rank IC" — **待实测标定具体阈值**

## 影响文件
- `architect/current_spec.yaml`: `hpo.success_criterion` 需移除 Phase 6 引用
- `handover/PHASE13_FULL_CHAIN_AUDIT.md`: 已标注 Phase 6 基线不可靠

## spec 参数映射
- `spec.hpo.success_criterion` → 当前引用 "Phase 6 IC=0.066 的一半"，需更新为 Phase 13 Post-Flight 锚点
