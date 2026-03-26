---
id: INS-015
title: 贝叶斯火力侦察 30+70 — 算力凯利公式
category: training
date: 2026-03-26
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-26_bayesian_recon_and_cg_microstructure.md
source_gdoc: null
---

# INS-015: 贝叶斯火力侦察 30+70 — 算力凯利公式

## 裁决
Phase 4 HPO 从一次性 100 trials ($222) 改为分阶段 30+70。前 30 trials 作为火力侦察（$67），若无 FVU<1.0 则止损。Vizier Study 有状态，可无缝追加。

## 理由
- 6 维搜索空间前 30 trials 为准随机探索，足够建立损失曲面
- 30 trials 全荒漠 → 证伪特征/目标互信息 → 止损优于盲投
- parallel_trial_count=8 确保贝叶斯世代迭代（太高退化为随机搜索）
- Taleb 反脆弱：小额试错 + 尾部暴利

## 影响文件
- `gcp/phase4_hpo_standard.yaml`: max_trial_count 100→30, parallel 5→8
- `architect/current_spec.yaml`: hpo 节更新
