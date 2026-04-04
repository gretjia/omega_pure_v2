---
id: INS-063
title: Excess BP 输出语义 — 仅居中 Target，封杀路径 B 双居中
category: training
date: 2026-04-02
axiom_impact: NONE
status: active
source_directive: 2026-04-02_audit_override_excess_alpha.md
source_gdoc: null
---

# INS-063: Excess BP 输出语义 — 仅居中 Target，封杀路径 B

## 裁决
模型输出语义正式变更为"纯粹的超额 Alpha (Excess BP)"。Loss 函数中仅对 Target 执行 Static Centering（减去 STATIC_MEAN_BP），pred 保持不居中。路径 B（pred 和 target 同时居中）被永久封杀。

## 理由
数学反证法：路径 B 的 MSE 误差项 `Err_B = (pred_bp - 40) - (target_bp - 40) ≡ pred_bp - target_bp`，两个 -40 在反向传播中完全抵消，静态置零防线形同虚设。优化器第一个 Epoch 就会操控 Decoder Bias 飙升到 +40，继续走私 Beta，拒绝唤醒 z_core。

路径 A 强制模型将 Bias 压制到 0，只能通过激活 z_core 去解释 0 轴两侧的个体方差。

推理端无需加回 40 — Rank IC 和 D9-D0 Spread 对常数平移免疫：Rank(X) ≡ Rank(X+40)。

## 影响文件
- `omega_epiplexity_plus_core.py`: compute_spear_loss_unbounded_audited — pred_bp 不居中
- `tools/phase7_inference.py`: 输出解读为 Excess BP，排序不受影响
- `backtest_5a.py`: 同上
