---
id: INS-046
title: 勾股漂移 — Z-score 仿射不变性导致权重 L2 范数单调膨胀
category: physics
date: 2026-04-01
axiom_impact: NONE
status: active
source_directive: phase11b_reforged_spear
source_gdoc: null
---

# INS-046: 勾股漂移 (Pythagorean Drift)

## 裁决
Z-score 标准化是绝对尺度不变的 (zscore(ar+b) = zscore(r))。根据欧拉齐次函数定理，梯度与权重正交 → W_new² = W_old² + Grad² → L2 范数单调膨胀。Phase 11a 中 S_T 从 4.3 指数爆炸到 Inf 正是此效应。

## 理由
- T=0.1 将梯度放大 10x → 漂移速度 100x
- λ_s=1e-7 对 Loss≈10 的 Softmax 无约束力 (惩罚占 0.14%)
- 多层反传共振加速 z_core 爆炸
- FP16 天花板 65504 在 S_T≈200K 时被击穿

## 影响文件
无直接影响 — 理论基础，指导 INS-047 (Detached Straitjacket) 设计
