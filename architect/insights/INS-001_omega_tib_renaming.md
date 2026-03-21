---
id: INS-001
title: Omega-TIB 架构正名
category: nomenclature
date: 2026-03-18
axiom_impact: NONE
status: active
source_directive: 2026-03-18_v3_full_design_audit.md
source_gdoc: id5_mae_vs_intent_prediction.md
---

# INS-001: SpatioTemporal2DMAE → Omega-TIB

## 裁决

废弃 `SpatioTemporal2DMAE` 命名（遗留物，暗示像素级图像重构），正名为 **Omega-TIB** (Topological Information Bottleneck 欧米伽拓扑信息瓶颈)。

## 理由

- "MAE" 暗示 Masked Autoencoder 式的像素重构目标，实际核心是标量意图预测
- Topological: 有限窗口 2D 容量流形特征提取（TDA 算子）
- Information Bottleneck: Two-part MDL 压缩 → 标量前向收益率预测
- 正确命名防止后续开发者误解模型本质

## 影响文件

- `architect/current_spec.yaml`: `training.target_model` → `Omega-TIB`
- `train.py` (待建): 类名和注释使用 Omega-TIB
