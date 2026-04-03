---
id: INS-060
title: Phase 12 无界之矛(审计版) — Scaled MSE + Static Centering + Leaky Blinding + Outlier Clipping
category: training
date: 2026-04-02
axiom_impact: UPDATE_REQUIRED
status: pending_deployment
source_directive: 2026-04-02_phase12_unshackling_protocol.md
source_gdoc: null
---

# INS-060: Phase 12 无界之矛 (审计版)

## 裁决
废弃 Huber Loss，采用经过三重工程防护的无界 MSE：
1. **Leaky Blinding**: `torch.where(tgt > 0, tgt, tgt * 0.1)` — 替代硬 clamp(min=0)，保留负收益 10% 信号
2. **BP 空间投影**: pred/target 统一乘 10000 转为 BP 空间
3. **Static Global Centering**: 减去 STATIC_MEAN_BP=40.0，摧毁 Beta 走私（常量偏置不能再被模型搭便车）
4. **Physical Outlier Clipping**: clamp(±500 BP)，切断微观结构噪声毛刺
5. **Scaled MSE**: 除以 SCALE_FACTOR=10000，压缩 MSE 量级至 0.1~1.0，确保 λ_s 不被碾压

## 理由
- 有界梯度 (Huber/Log-Cosh) = "平庸之恶"，对 +460 BP 主升浪只给线性梯度，无法点亮 z_core
- 但裸 MSE 有三个工程致命缺陷：量纲溢出(NaN)、噪声放大(毛刺炸权重)、λ_s 碾压(Sparsity 失效)
- 审计版通过 BP 投影 + 缩放 + 钳制，在释放极端奖赏的同时加装物理安全护手

## 关键参数
- `STATIC_MEAN_BP = 40.0` (A 股验证集截面正收益均值的粗估)
- `SCALE_FACTOR = 10000.0` (100 BP 的平方，对齐 λ_s 博弈天平)
- `Outlier Clamp = ±500 BP` (A 股天地板范围)
- `Leaky factor = 0.1` (负收益衰减因子)

## 影响文件
- `omega_epiplexity_plus_core.py`: compute_spear_loss → compute_spear_loss_unbounded_audited
- `train.py` / `gcp/train.py`: Loss 调用处
