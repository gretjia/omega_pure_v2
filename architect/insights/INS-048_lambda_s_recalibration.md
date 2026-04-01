---
id: INS-048
title: λ_s 动态引力重构 — 1e-7→2e-5 匹配 Softmax 量纲
category: training
date: 2026-04-01
axiom_impact: UPDATE_REQUIRED
status: pending_phase11b
source_directive: phase11b_reforged_spear
source_gdoc: null
---

# INS-048: λ_s 动态引力重构

## 裁决
lambda_s 从 1e-7 提升到 2e-5 (200x)。匹配 Softmax Loss (~8-10) 相对于 IC Loss (~0.05) 的 160-200x 量纲差异。

## 量化依据 (Codex 验证)
- Phase 11a Epoch 4: S_T=143K, λ_s×S_T = 1e-7×143K = 0.014 → 占 Loss 0.14%
- 数值平衡需: λ_s ≈ Loss/S_T = 10/143K ≈ 7e-5
- 架构师选 2e-5: 低于数值平衡点，避免"MDL 断头台"风险
- Codex 推荐 1e-3 但警告断头台风险 → 架构师选更保守值

## 与 INS-012/019 的关系
- INS-012: λ_s=0.001 绞杀微弱 Alpha (Phase 4 教训)
- INS-019: 隐式压缩 (hd=64 瓶颈) >> 显式压缩 (λ_s)
- 本洞察: λ_s 不是越大越好，但必须与 Loss 量纲匹配

## 影响文件
- `train.py`: lambda_s default 1e-7 → 2e-5
- `architect/current_spec.yaml`: training.lambda_s
