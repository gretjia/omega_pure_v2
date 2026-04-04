---
id: INS-066
title: "Revert to IC Loss — MSE 在高方差低 SNR 下退化为条件均值预测"
category: training
date: 2026-04-04
axiom_impact: UPDATE_REQUIRED
status: active
audit_status: draft
source_directive: "2026-04-04_phase13_audit_verdict_and_roadmap.md"
source_gdoc: null
---

# INS-066: Revert to IC Loss (Rank-Based Objective)

## 裁决
废弃 MSE、Static Centering、Leaky Blinding。恢复 IC Loss (Pearson/Spearman) 作为主目标函数，直接优化排序信号。推理端用 Daily Cross-Sectional Z-Score 解决尺度问题。

## 理由
Phase 6 IC Loss → IC=0.066（历史最高），Phase 12 MSE → IC=0.005（13x 退步）。在 target std=189.60 >> signal=4.51 的环境下，MSE 被方差主导，退化为拟合条件均值。IC Loss 天然免疫绝对尺度问题（INS-018 当时的顾虑），因为交易执行完全依赖截面排序。

## 前提假设
- **数据格式**: target 已在 BP，IC Loss 对尺度免疫
- **上游依赖**: INS-065 (删除 leaky blinding) 先行
- **环境假设**: IC Loss 需要 batch 内截面多样性，batch_size=256 足够

## 被拒绝的替代方案
- **方案 B**: 修复 MSE（去掉 leaky + 加 rank 正则）→ 拒绝: MSE 本质优化绝对误差非排序
- **方案 C**: ListMLE / Pairwise Margin → 拒绝: 增加复杂度，先验证 IC Loss 是否恢复 Phase 6 水平
- [AUDIT OVERRIDE] INS-018 废弃 IC Loss 的理由（"绝对尺度太小"）→ 推翻: 尺度是推理工程问题，不是 Loss 问题

## 验证协议
1. 验证命令: Phase 13 smoke test 2 epoch, 检查 val IC 和 cross-sectional D9-D0
2. 预期结果: IC > 0.03 (Phase 6 水平的一半即算恢复)
3. 失败回退: 如果 IC < 0.01，尝试 IC + 小权重 MSE 混合 Loss

## 参数标定来源
- 🔬 **实测标定**: Phase 6 T29 IC=0.066 (历史基准)
- 📐 **理论推导**: IC Loss 梯度 ∝ cov(pred, target)，对尺度免疫

## 影响文件
- `omega_epiplexity_plus_core.py`: 新增 `compute_ic_loss()`, 删除或废弃 MSE 系列
- `train.py`: Loss 函数切换，删除 static_mean_bp/outlier_clamp_bp/mse_scale_factor 参数
- `architect/current_spec.yaml`: 重写 `training.loss` 和 `training.loss_function`

## spec 参数映射
- `spec.training.loss` → "IC Loss (Pearson)" supersedes "Unbounded Spear"
- `spec.training.loss_function` → 完全重写
- `spec.training.static_mean_bp` → 删���
- `spec.training.outlier_clamp_bp` → 删除
- `spec.training.mse_scale_factor` → 删除
- `spec.training.leaky_factor` → 删除 (INS-065)
