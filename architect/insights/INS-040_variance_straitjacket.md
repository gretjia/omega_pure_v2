---
id: INS-040
title: 方差之枷 — 截面 Z-score 锁死 Std_yhat=1.0, 摧毁 Logit Inflation
category: training
date: 2026-03-31
axiom_impact: UPDATE_REQUIRED
status: pending_p0_backtest
source_directive: phase11_asura_protocol + phase11_spear_protocol
source_gdoc: null
---

# INS-040: 方差之枷 (The Variance Straitjacket)

## 裁决
在网络输出进入 Softmax 前，强制实施无参数截面标准化 `locked = (raw - mean) / std`。Std_yhat 永远锁死在 1.0，取代无效的 L2 mean-shift (INS-036 superseded)。

## 理由
Phase 10 Std_pred=4540 BP (22.9x target)。Softmax 平移不变性导致模型通过无限放大 logit 极差(降低隐式 Temperature)来抢夺 Top-1 权重(0.98)。L2 mean-shift 只约束均值，对极差无效。截面 Z-score 是唯一能物理锁死尺度的方法。

## 与 INS-036 的关系
INS-036 提出方差惩罚或 LayerNorm 两种方案。本洞察明确选择截面 Z-score (比 LayerNorm 更强 — 直接锁死到 N(0,1))。INS-036 被 supersede。

## 影响文件
- `omega_epiplexity_plus_core.py`: IntentDecoder 输出后添加截面 Z-score
- `train.py`: 删除 L2 mean-shift penalty (被物理替代)
