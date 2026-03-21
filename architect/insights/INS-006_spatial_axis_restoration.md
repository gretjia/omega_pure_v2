---
id: INS-006
title: 空间轴恢复 [T,S,F] 四维结构
category: architecture
date: 2026-03-18
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-18_v3_spatial_restoration.md
source_gdoc: null
---

# INS-006: 张量从 [160,7] → [160,10,F] — 恢复 LOB 空间维度

## 裁决

拒绝 V2 的拍扁形状 `[160, 7]`，V3 恢复四维结构 `[B, T=160, S=10, F]`。

- S=10: 5 档买盘 + 5 档卖盘
- 每个时间步保留完整的订单簿深度拓扑

## 理由

`FiniteWindowTopologicalAttention` 是原生 2D 算子，需要空间维度提取阻力墙结构、盘口厚度梯度等拓扑特征。拍扁空间轴 = 退化为 1D 序列模型 = 丧失 TDA 的核心价值。

**已记录为 Via Negativa**: "拍扁空间轴 [160,7] → 维度坍缩"

## 影响文件

- `architect/current_spec.yaml`: `tensor.shape`
- `tools/omega_etl_v3_topo_forge.py`: LOB snapshot 提取为 [S, 4]
- `omega_webdataset_loader.py`: 4D 张量加载
- `omega_axioms.py`: shape 验证
