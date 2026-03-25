---
id: INS-013
title: Phase 4 HPO 搜索空间 — 六维拓扑共振搜索
category: training
date: 2026-03-25
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirmation
source_directive: 2026-03-25_phase4_hpo_authorization.md
source_gdoc: null
---

# INS-013: Phase 4 HPO 搜索空间 — 六维拓扑共振搜索

## 裁决
Phase 4 HPO 搜索空间从 Phase 2 的"宏观窗口+粗粒化"转向"MDL 压缩力度+模型容量+时空注意力尺度"三大维度。这是 Phase 3 v15 数据驱动的决策，非理论推导。

## 理由
Phase 3 证明：
1. 架构无 bug（v14 单 batch Train FVU=0.43）
2. 信号存在（v15 Val FVU=0.9997 < 1.0）
3. 死因是 MDL 过强（S_T 从 10.82 → 0.51 时信号丢失）

因此搜索空间需聚焦于：
- P0: MDL 降压 (lambda_s: 1e-6 ~ 1e-4, warmup: 3~5 epochs)
- P1: 模型扩容 (hidden_dim: 128~384) + 注意力尺度 (window_size_t: 8~64)
- P2: 优化器动力学 (lr: 1e-4 ~ 1e-3)

同时锁定：
- macro_window=160, coarse_graining=1（Phase 3 已验证）
- mask_prob=0.0（先确认 Alpha，防过拟合是 Phase 5）
- payoff_horizon=20（INS-010: 禁止目标劫持）

## 影响文件
- `architect/current_spec.yaml`: hpo.search_space 全面更新
- `gcp/phase4_hpo_config.yaml`: 新建 Vertex AI HPO 配置
- `gcp/submit_phase4_hpo.sh`: 新建 HPO 提交脚本
- `train.py`: 添加 hypertune 指标上报 + early stopping
