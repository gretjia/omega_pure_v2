---
id: INS-014
title: 时间膨胀器回归 — coarse_graining_factor 作为 P0 搜索参数
category: architecture
date: 2026-03-25
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirmation
source_directive: 2026-03-25_phase4_ashare_swing_tracker.md
source_gdoc: null
---

# INS-014: 时间膨胀器回归 — coarse_graining_factor 作为 P0 搜索参数

## 裁决
coarse_graining_factor 从"固定=1"恢复为 HPO 搜索参数 [1, 4, 16, 64]。这是 A 股 T+1 制度下捕捉机构长周期建仓足迹的物理必需。

## 理由
T=160 volume-clocked 步仅覆盖约 8 分钟的微观历史。要预测 5-20 交易日的主力行为，模型必须能"缩小"时间尺度：
- cg=1: 160 步 (~8 min) — 微观结构
- cg=4: 40 步 (~30 min) — 短线
- cg=16: 10 步 (~2h) — 日内
- cg=64: 2-3 步 (~1.3 天) — 跨日

不同 cg 值探索不同的"时空共振频率"，让 Vizier 找到机构足迹最清晰的尺度。

## 影响文件
- `gcp/phase4_study_spec.yaml`: 添加 coarse_graining_factor 参数
- `architect/current_spec.yaml`: hpo.search_space 更新
- `train.py`: 已支持 --coarse_graining_factor 参数，无需代码变更
