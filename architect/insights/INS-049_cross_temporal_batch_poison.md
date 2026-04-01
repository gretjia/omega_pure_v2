---
id: INS-049
title: 跨期 Batch 毒药 — 乱序 WebDataset 封杀 Batch 维度归一化
category: training
date: 2026-04-01
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-04-01_phase11c_pointwise_spear.md
source_gdoc: null
---

# INS-049: 跨期 Batch 毒药 — 乱序 WebDataset 封杀 Batch 维度归一化

## 裁决
在时序随机 Shard 的 WebDataset DataLoader 中，**绝对禁止使用任何 Batch 维度的归一化算子**（包括 Softmax(dim=0)、Batch Z-score、Pearson IC），否则将引发严重的宏观时间泄露（Macro Beta Smuggling）。

## 理由
188 个 Tar 碎片随机流式加载 → 一个 Batch 中 256 个样本跨越 3 年不同日期、不同股票。Softmax(dim=0) 在这个"时空缝合怪"上建立零和博弈，模型发现识别宏观牛/熊市远比提取微观 Alpha 拓扑简单，于是利用 Softmax 指数放大将牛市样本预测值膨胀至 6956 BP，退化为"宏观 Beta 剥削器"。这解释了 Phase 10/11a/11b 中 44% 虚假年化收益和 IC 为负但绝对值极大的现象。

## 影响文件
- `train.py`: 替换 `compute_spear_loss` 中的 `F.log_softmax(locked_logits / temperature, dim=0)` 和 Batch Z-score
- `omega_epiplexity_plus_core.py`: `compute_epiplexity_mdl_loss` 中的 MSE 已是 pointwise，无需改动
- `current_spec.yaml`: 删除 temperature、variance_lock 字段，更新 loss 描述
