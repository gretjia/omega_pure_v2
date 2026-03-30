---
id: INS-031
title: Phase 9 Vanguard V3 Protocol — 锁死底盘换发引擎
category: training
date: 2026-03-30
axiom_impact: NONE
status: pending_phase9
source_directive: 2026-03-30_phase9_asymmetric_evolution_leaky_pearson.md
source_gdoc: null
---

# INS-031: Phase 9 Vanguard V3 Protocol — 锁死底盘换发引擎

## 裁决
Phase 9 训练必须完全锁定 T29 超参序列 (hd=64, wt=32, lr=3.2e-4, lambda_s=1e-7, wu=2, bs=128, cg=1)，仅替换 loss function。不跑 HPO。先做单次 10-20 epoch 定标训练，生成新 predictions.parquet，用 Phase 8 锁定的 c0_r0_b1 simulate 配置判决。

## 理由
- T29 底盘已被 Phase 6 HPO (70 trials) 和 Phase 7/8 回测验证为最优物理结构
- 同时改 loss + 超参 → 无法归因 (Phase 8 教训)
- 判决指标：Tail Capture Lift (目标 Top1% 从 2x→3x+) 和 Asymmetry Payoff Ratio (目标 >1.5)
- simulate 配置锁定 c0_r0_b1 (board_loss_cap=on, conviction=0, regime=off)

## 影响文件
- `train.py`: loss function 替换 (唯一变更)
- 不修改模型架构、ETL、simulate
