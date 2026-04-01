---
id: INS-050
title: L1 脑死亡陷阱 — z_sparsity 语义翻转修正
category: physics
date: 2026-04-01
axiom_impact: NONE
status: active
source_directive: 2026-04-01_phase11c_pointwise_spear.md
source_gdoc: null
---

# INS-050: L1 脑死亡陷阱 — z_sparsity 语义翻转修正

## 裁决
**纠正全项目对 z_sparsity (L1 范数) 的认知翻转**：L1≈0 不代表"最高压缩"，而是"特征脑死亡 (Brain Death)"——模型关闭所有 z_core 特征通道来逃避 λ_s 惩罚，仅靠最后一层 Bias 盲赌宏观 Beta。非零的适度 L1 值才代表模型点亮了特定神经元去描绘主力建仓的 2D 拓扑，即"真智能涌现"。

## 理由
Phase 10 十分位拆解(Decile Breakdown)实证：
- Z-D0 (S_T≈0): IC 为负（方向全错），|pred| 极大（6956 BP），= 高熵赌徒/脑死亡
- Z-D9 (S_T≈0.011): IC 为正（看懂了），pred 克制（2000 BP），= 真智能涌现
- 旧 Gating 逻辑（过滤高 S_T）= 处决 Z-D9 真智能 + 满仓 Z-D0 脑死亡 → -34% 收益蒸发

**心智重标记**: z_sparsity → z_complexity。未来 Gating 回测必须**保留高 L1，剔除低 L1**。这直接废弃 INS-034 和 INS-039 的 Gating 方向。

## 影响文件
- `OMEGA_LESSONS.md`: 写入 C-046 案例
- 回测脚本: 未来 Gating 逻辑必须反转方向
- INS-034 (z_sparsity 作为交易扳机): **语义方向反转** — 高 L1 = 真控盘，低 L1 = 赌徒
- INS-039 (Epiplexity Gating FAILED): 根因确认 — Gating 方向完全搞反
