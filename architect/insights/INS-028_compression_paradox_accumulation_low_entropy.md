---
id: INS-028
title: 压缩悖论 — 建仓=低熵可压缩，派发=高熵不可压缩
category: physics
date: 2026-03-30
axiom_impact: NONE
status: pending_phase9
source_directive: 2026-03-30_compression_paradox_asymmetric_evolution.md
source_gdoc: null
---

# INS-028: 压缩悖论 — 建仓=低熵可压缩，派发=高熵不可压缩

## 裁决
主力建仓 (Accumulation) 和派发 (Distribution) 是两种热力学方向相反的物理过程，不应被同一 Epiplexity 瓶颈同时压缩。建仓行为（TWAP/VWAP 冰山单）高度规律、低熵，极度可被 MDL 压缩；派发行为（Spoofing、FOMO 制造）混沌、高熵，强制压缩会污染瓶颈神经元。"压缩即智能"的正确应用是：只压缩属于同一数据生成机制的信息。

## 理由
- Phase 7 Test #4.9: Long alpha (+13.34 BP) 是 Short alpha (+4.74 BP) 的 3x — 模型已隐式证明建仓拓扑更可压缩
- Phase 7 Test #4.12: 上下尾部捕获率对称 (2.01x vs 1.84x) — hd=64 被迫同时编码两种正交信号，退化为波动率雷达
- Kolmogorov Complexity 论证：强制压缩不可压缩的高熵信号 = 降低整体压缩率
- 此洞察不违背"压缩即智能"，反而是其终极纯化

## 影响文件
- Phase 9 范畴。Phase 8 不应触碰模型层。
- `train.py`: Phase 9 路径 A (asymmetric target masking) 或路径 B (two-headed Asura)
- `omega_epiplexity_plus_core.py`: Phase 9 路径 B 需分叉 EpiplexityBottleneck
