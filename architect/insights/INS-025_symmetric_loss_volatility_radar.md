---
id: INS-025
title: 对称 Loss 的数学诅咒 — 模型退化为波动率雷达
category: training
date: 2026-03-30
axiom_impact: NONE
status: active
source_directive: 2026-03-30_phase7_audit_phase8_deep_fat_tail.md
source_gdoc: null
---

# INS-025: 对称 Loss 的数学诅咒 — 模型退化为波动率雷达

## 裁决
Pearson IC Loss 是对称的：把第一名排对和把倒数第一名排对获得相同梯度奖励。在 target_std=198 BP、IC=0.028 的框架下，不对称赔率理论上限约 1.2。模型捕获 Top 1% 尾部 (2.01x lift) 与 Bottom 1% 尾部 (1.84x lift) 几乎等同 — 它识别的是"高波动拓扑"而非"方向性优势"。Asymmetry 3.0 在当前 Loss 函数下数学上不可达。

## 理由
- Phase 7 Test #4.12: 尾部捕获率上下对称 (2.01x vs 1.84x)
- Phase 7 Test #4.13: 需要 5x+ lift 才能达到 asymmetry 3.0，当前 2x
- 根因：Pearson correlation 对上下偏差等权惩罚，64 维瓶颈被迫同时编码建仓和出货的拓扑，退化为波动率探测器
- 解决路径：Phase 9 引入非对称 Loss (Quantile Pinball / Asymmetric MSE)，或双头架构解耦多空信号

## 影响文件
- `train.py`: Phase 9 时需替换 loss function (不在 Phase 8 范围内)
- `architect/current_spec.yaml`: Phase 9 时需更新 training.loss 字段
