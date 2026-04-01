---
id: INS-054
title: 方差坍缩 — Huber δ=50 削峰 + λ_s=1e-3 断头台导致特征脑死亡
category: training
date: 2026-04-01
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-04-01_phase11d_resuscitation_protocol.md
source_gdoc: null
---

# INS-054: 方差坍缩 — Huber δ=50 削峰 + λ_s=1e-3 断头台导致特征脑死亡

## 裁决
Phase 11c 的 Huber δ=50 + λ_s=1e-3 组合导致模型选择"关闭 z_core + 输出均值常数"作为全局最优策略。δ=50 将 17.5% 高价值肥尾样本的梯度削到线性（削掉 70%），而 λ_s=1e-3 在特征层施加了远超梯度奖励的结构税。模型理性地选择了"免税脑死亡"。

## 理由
* 烟测实测：pred_std=5.64 BP（模型输出 ~30 BP 常数），z_sparsity=0.44%（z_core 几乎全关）
* 训练仪表盘 15 个 Epoch 的 Std_yhat 全部是 216x 幻觉（Docker 旧代码残留 * TARGET_STD）
* 真实 E7 "382 BP" = 1.77 BP — 模型在向常数坍缩，而非在"精炼"
* Huber δ=50：200 BP 目标梯度被削到 50（3.3x 衰减）；δ=200 时梯度为 167
* Epiplexity 公理未通过：z_core 死亡时 z_sparsity 波动仅为浮点噪音，无法测量智商

## 影响文件
* `train.py` / `gcp/train.py` — compute_spear_loss 需开放 huber_delta 参数 + 方差哨兵
* `architect/current_spec.yaml` — lambda_s: 1e-3→1e-4, huber_delta: 50→200
* `gcp/phase11d_*.yaml` — 新训练配置（双轨 A/B）
