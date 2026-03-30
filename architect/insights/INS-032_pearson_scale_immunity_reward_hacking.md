---
id: INS-032
title: Pearson 尺度免疫漏洞 — 非对称 dampening 诱导 Reward Hacking
category: training
date: 2026-03-30
axiom_impact: NONE
status: active
source_directive: 2026-03-30_metric_collapse_softmax_portfolio_loss.md
source_gdoc: null
---

# INS-032: Pearson 尺度免疫漏洞 — 非对称 dampening 诱导 Reward Hacking

## 裁决

非对称 Pearson Loss（downside dampening）在数学根基上是死路。Pearson 的尺度不变性允许网络通过无限膨胀 Std(ŷ) 来"作弊"：在训练集死记硬背少数妖股并将预测值推向正无穷，获得高 Train IC 但 Val IC 归零。这不是泛化退化，而是 Reward Hacking。

## 理由

- Pearson IC = Cov(ŷ, y) / (Std(ŷ) × Std(y))，预测值放大任意倍数 IC 不变
- dampening 压扁负 target 70% → 网络只需记住正 target 最大的样本并无限放大预测值
- MSE anchor 试图约束 Std(ŷ) 但与 Pearson 形成"梯度精神分裂"：不存在平衡点
- Phase 9 v1-v4 实验完美复现：v1 灾难性过拟合(Train IC=0.18, Val IC=-0.001)，v3c val IC 单调下降(0.006→0.003)

## 影响文件

- `train.py` / `gcp/train.py`: Pearson IC Loss + dampening 逻辑需彻底移除
- `omega_epiplexity_plus_core.py`: 无影响（底盘无罪）
- `architect/current_spec.yaml`: training.loss, training.downside_dampening, training.anchor_weight 需更新
