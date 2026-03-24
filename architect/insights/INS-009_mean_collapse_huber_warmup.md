---
id: INS-009
title: 均值坍缩修复 — Huber Loss + Target 归一化 + MDL Warmup
category: training
date: 2026-03-24
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirm
source_directive: 2026-03-24_mean_collapse_diagnosis_and_phase4_6_audit.md
source_gdoc: null
---

# INS-009: 均值坍缩修复 — Huber + Target Norm + MDL Warmup

## 裁决
Phase 3 训练 FVU≡1.0 的根因是：(1) 未归一化的 raw BP target 在 MSE 下产生平坦梯度景观，(2) 肥尾离群点 (-2932 BP) 的平方级惩罚迫使模型收缩到均值，(3) MDL 正则化在模型学习前就过早施加。修复：H_T 从 MSE 切换为 Huber(delta=1.0)，target 做 Z-score + 5σ 截断，lambda_s 前 2 epoch 设为 0。

## 理由
- FVU=1.0005 精确对应 pred=0, target_mean=-5: FVU = (Var+25)/Var = 46681/46656 = 1.00053
- Epoch 4 FVU=1.2041 是肥尾 outlier 冲击的直接证据
- S_T 从 280→450 但 H_T 不降 = MDL 惩罚在模型未学习时已生效

## 影响文件
- `train.py`: 新增 `compute_robust_loss()` 替代 `compute_epiplexity_mdl_loss()`
- `architect/current_spec.yaml`: training.loss 描述更新
