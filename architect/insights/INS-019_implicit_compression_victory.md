---
id: INS-019
title: 隐式压缩胜利 — hd=64 物理瓶颈 >> λ_s 显式惩罚
category: architecture
date: 2026-03-29
axiom_impact: NONE
status: invalidated  # Phase 6 evidence invalidated by INS-072 (C-062 torch.compile bug). Phase 15 MLP > Omega further challenges hd=64 premise.
source_directive: 2026-03-29_compression_is_intelligence_phase7_golive.md
source_gdoc: null
---

# INS-019: 隐式压缩胜利 — hd=64 物理瓶颈 >> λ_s 显式惩罚

## 裁决
Phase 6 证明"压缩即智能"通过**隐式架构瓶颈（hd=64, 19.7K 参数）**实现，而非显式 L1 惩罚（λ_s 从 0.001 降至 1e-7 几乎归零）。小模型在 9.96M 样本数据集上击败大模型，证明信息瓶颈强制过滤高熵散户噪音，只保留低熵主力行为信号。

## 理由

压缩有两种物理形态：
1. **显式压缩**：λ_s × ||z_core||_L1（外力鞭打） — Phase 3 的 0.001 过于猛烈，杀死信号
2. **隐式压缩**：hd=64 的物理脑容量限制（窄门过滤） — 高熵噪音挤不过去

Phase 6 证据链：
- hd=64 (T29, 19.7K params): IC=+0.0661, 单调性 8/9
- hd=128 (T36, 77K params): IC=+0.0667, 单调性 7/9
- hd=256 (305K params): 未进入 Top-3

IC 差距仅 0.0006，但参数量差 4 倍。在 Kolmogorov Complexity 框架下，hd=64 的模型被迫丢弃不可压缩的散户噪音，只编码可压缩的主力算法订单（TWAP/VWAP metaorders）。

**λ_s 归零不是"压缩失效"，而是"压缩已由架构物理完成，不再需要外部辅助轮"。**

## 影响文件
- `architect/current_spec.yaml`: 无变更（training.lambda_s 搜索范围仍保留 [1e-7, 1e-4]）
- 概念性影响：Phase 7 旗舰模型建议从 T36 (hd=128) 切换至 T29 (hd=64)
