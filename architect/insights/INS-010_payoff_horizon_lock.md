---
id: INS-010
title: payoff_horizon 从 HPO 搜索空间移除 — 禁止算法选择目标
category: metrics
date: 2026-03-24
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirm
source_directive: 2026-03-24_mean_collapse_diagnosis_and_phase4_6_audit.md
source_gdoc: null
---

# INS-010: payoff_horizon 锁定 — 禁止 HPO 搜索任务目标

## 裁决
payoff_horizon 定义的是预测任务本身（目标变量），不同 horizon 的 Var(target) 不可比。将其放入 HPO 搜索空间会导致"目标劫持"——Vizier 会选天然波动最小的 horizon 而非最强的模型拓扑。必须由人类架构师锁定 payoff_horizon=20。

## 理由
- FVU = MSE / Var(target)，不同 horizon 的 Var(target) 完全不同
- Vizier 的贝叶斯优化会把算力倒向最容易的 horizon，而非最有信号的
- 正确的做法：锁定 horizon 后纯粹搜索网络超参 (macro_window, window_size, lr)

## 影响文件
- `architect/current_spec.yaml`: hpo.search_space 移除 payoff_horizon
- `plan/v3_pipeline_plan.md`: Phase 4 HPO 描述更新
