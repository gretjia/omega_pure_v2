---
id: INS-004
title: Block-wise 因果输入遮蔽
category: training
date: 2026-03-18
axiom_impact: NONE
status: pending_train_py
source_directive: 2026-03-18_v3_full_design_audit.md
source_gdoc: id5_mae_vs_intent_prediction.md
---

# INS-004: On-the-fly Volume Block Input Masking

## 裁决

- 遮蔽发生在 `train.py` GPU DataLoader 中，**绝不在 ETL 阶段**（保持磁盘数据纯净）
- 随机移除 10-30 根连续 volume bars（Block-wise，非逐 bar 随机）
- 触发概率：50% per batch
- 保留最后 5 根 bar 不遮蔽（模型必须看到"触警现状"）
- 仅在 `model.train()` 模式生效

## 理由

- 防止模型通过局部线性插值作弊（逐 bar 随机遮蔽太容易猜中）
- 连续 block 遮蔽强制跨时间因果推理
- 保留尾部 5 bars 确保模型有足够信息判断"当前市场状态"

## 实现规格

```python
class VolumeBlockInputMasking:
    min_mask_bars: 10
    max_mask_bars: 30
    mask_prob: 0.5
    preserve_tail: 5  # 最后 5 根 bar 不遮蔽
```

串联位置：`input_proj` 之后、`tda_layer` 之前

## 影响文件

- `train.py` (待建): VolumeBlockInputMasking 实现
