---
id: INS-055
title: Phase 11d 双轨复苏 — λ_s 降 10-100x + Huber δ 放宽 4x
category: training
date: 2026-04-01
axiom_impact: UPDATE_REQUIRED
status: pending_deployment
source_directive: 2026-04-01_phase11d_resuscitation_protocol.md
source_gdoc: null
---

# INS-055: Phase 11d 双轨复苏 — λ_s 降 10-100x + Huber δ 放宽 4x

## 裁决
执行双轨对照实验重标定 Phase 11c 量纲剧变后的正则化参数：
- Config A: λ_s=1e-4, δ=200（平衡）
- Config B: λ_s=1e-5, δ=200（激进）
不做全量 HPO，两组足以区分：参数校准问题 / λ_s 历史伤害 / 架构性缺陷。

## 理由
* δ=200 覆盖 97.6% 样本为 MSE 二次方梯度，仅极端 2.4% 线性保护
* δ 和 λ_s 存在交互：δ 控制奖励天花板，λ_s 控制成本地板，需同时调整
* 成功判据：pred_std>30 BP / z_sparsity>5% / D9-D0 spread>30 BP
* 若两组均失败 → 问题是架构性的（SRL 物理捷径），需结构重构

## 影响文件
* `train.py` / `gcp/train.py` — compute_spear_loss 参数化 huber_delta
* `gcp/phase11d_config_A.yaml` / `gcp/phase11d_config_B.yaml` — 新训练配置
* Docker 镜像需重建（phase11d-v1）
