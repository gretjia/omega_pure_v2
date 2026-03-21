---
id: INS-008
title: FVU 为 HPO 最高准则
category: metrics
date: 2026-03-18
axiom_impact: NONE
status: pending_train_py
source_directive: 2026-03-18_v3_full_design_audit.md
source_gdoc: id5_mae_vs_intent_prediction.md
---

# INS-008: FVU (Fraction of Variance Unexplained) 为 HPO 唯一成功标准

## 裁决

```
FVU = MSE / Var(target)
```

- FVU ≈ 1.0: 模型等同瞎猜均值（输出 ≈ E[Y]）
- FVU < 0.95 且出现 sharp minimum: 发现了"黄金拓扑窗口"
- FVU 是尺度无关 (scale-invariant) 的：不受不同股票/周期波动率畸变影响

## 理由

纯 MSE 在跨股票、跨时期比较时受波动率缩放影响。FVU 归一化后：
- 不同 payoff_horizon 的结果可直接比较
- 不同市场状态（牛市 vs 震荡）的结果可直接比较
- Bayesian HPO 搜索 (Google Vizier) 可以用单一标量 FVU 做收敛判断

## 影响文件

- `train.py` (待建): `compute_fvu()` 函数
- `architect/current_spec.yaml`: `training.hpo_success_criterion`
