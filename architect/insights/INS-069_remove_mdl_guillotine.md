---
id: INS-069
title: "Remove MDL Guillotine — L1 正则化在 2.4% SNR 下杀信号"
category: training
date: 2026-04-04
axiom_impact: UPDATE_REQUIRED
status: active
audit_status: draft
source_directive: "2026-04-04_phase13_audit_verdict_and_roadmap.md"
source_gdoc: null
---

# INS-069: Remove MDL L1 Regularization (Guillotine)

## 裁决
移除 z_core 上的 L1 正则化（lambda_s=0）。在 2.4% SNR 环境下，L1 不分青红皂白地摧毁弱判别信号。

## 理由
Phase 12 实证：D9-D0 从 E0 (lambda_s=0) 的 4.51 BP 单调下降到 E19 (lambda_s=1e-4) 的 1.29 BP。MDL 压缩在"杀信号"而非"压噪声"。模型的 z_core 激活在 E0 时 sparsity=5.4%（活跃但无信息），L1 将其压到 18.5% 但 IC 从 0.005 降到 0.0001。

## 前提假设
- **数据格式**: z_core shape [B, 160, 10, 16]
- **上游依赖**: 与 IC Loss (INS-066) 联合后，z_core 的角色可能改变。如果 IC Loss 下 z_core 变得有信息，可以后续重新引入 L1
- **环境假设**: 24.4K 参数模型本身就是物理瓶颈（hidden//4=16），显式压缩不必要

## 被拒绝的替代方案
- **方案 B**: 降低 lambda_s 到 1e-6 → 拒绝: E0 (lambda_s=0) 已经是最优，加任何 L1 都在退步
- **方案 C**: 改用 L2 正则 → 拒绝: 先验证 IC Loss 下是否还需要显式正则化

## 验证协议
1. 验证命令: Phase 13 训练设 lambda_s=0，对比有/无 L1 的 IC 差异
2. 预期结果: lambda_s=0 的 IC 不低于有 L1 版本
3. 失败回退: 如果过拟合严重，用 L2 weight decay 替代 L1

## 参数标定来源
- 🔬 **实测标定**: Phase 12 E0 vs E19 单调下降证据

## 影响文件
- `train.py`: `compute_spear_loss` 中 lambda_s 相关逻辑（或整个 Loss 重写为 IC Loss）
- `architect/current_spec.yaml`: `training.lambda_s` → 0 或删除

## spec 参数映射
- `spec.training.lambda_s` → 0 (Phase 13 baseline) 或移入 HPO 搜索含 0
