---
id: INS-057
title: SRL 捷径学习确认 — z_core 被架构旁路饿死，必须物理切断
category: architecture
date: 2026-04-02
axiom_impact: UPDATE_REQUIRED
status: pending_ablation
source_directive: 2026-04-02_phase12_unshackling_protocol.md
source_gdoc: null
---

# INS-057: SRL 捷径学习确认 — z_core 被架构旁路饿死

## 裁决
SRL 层提取的高信噪比元订单流通过残差/直通旁路线性透传给 Decoder，优化器走"阻力最小路径"，主动将 z_core 权重压至接近 0（z_sparsity = 0.12%）以规避 L1 惩罚。z_core 不是学不到特征，而是被架构直通车"饿死"了。确信度 99%。

## 理由
深度学习中最致命的 Shortcut Learning。优化器面临：(A) 费力优化 Topology Attention + Epiplexity 瓶颈 + L1 惩罚 vs (B) 直接透传 SRL 物理信号。梯度永远"水往低处流"。

## 执行动作
1. **Naked Ablation [P0]**: 在 forward 中硬冻结 `z_core = z_core.detach() * 0`，仅跑 SRL→Decoder，验证 IC 是否仍在 0.009
2. **物理切断 [P0]**: 实锤后，必须在算子上掐断所有跨过 z_core 的 Skip Connection，逼迫梯度必须流经 Epiplexity 瓶颈

## 影响文件
- `omega_epiplexity_plus_core.py`: forward 方法中的残差/旁路连接
- `train.py` / `gcp/train.py`: 消融测试入口
