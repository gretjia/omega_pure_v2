---
id: INS-016
title: cg 微观结构保护 — Volume-Clock 不可二次粗粒化
category: physics
date: 2026-03-26
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-26_bayesian_recon_and_cg_microstructure.md
source_gdoc: null
---

# INS-016: cg 微观结构保护 — Volume-Clock 不可二次粗粒化

## 裁决
coarse_graining_factor 搜索空间从 [1,4,16,64] 改为 [1,2,4,8]。移除 cg=16/64，因其摧毁 Volume-Clock 的自适应信息熵结构，且与 payoff_horizon=20 bars (~6h) 存在香农-奈奎斯特采样倒挂。

## 理由
三大物理悖论：
1. **Volume-Clock 双重降维**: Volume-Clock 已是自适应粗粒化，再 avg_pool = 摧毁变速齿轮
2. **采样倒挂**: cg=64 每步=1.3 天，预测 6h 收益 = 因果倒挂
3. **宏观意图需微观探针**: 主力建仓通过每日微观执行实现，需高分辨率检测重复模式

未来扩展长期视野的正确方式：增大 macro_window (如 320/500)，非增大 cg。

## 影响文件
- `gcp/phase4_hpo_standard.yaml`: cg values 更新
- `architect/current_spec.yaml`: hpo.search_space.coarse_graining_factor 更新
