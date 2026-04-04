---
id: INS-062
title: MSE 量纲碾压与噪声过拟合防线 — BP 投影 + SCALE_FACTOR + ±500 BP 熔断
category: training
date: 2026-04-02
axiom_impact: NONE
status: active
source_directive: 2026-04-02_phase12_unshackling_protocol.md
source_gdoc: null
---

# INS-062: MSE 量纲碾压与噪声过拟合防线

## 裁决
无界 MSE 有两个工程致命缺陷，必须同时加装防护：

### 1. 量纲碾压 (The Scaling Bomb)
Target 在 WebDataset 管道中是原始小数 (0.0040 = 40 BP)。如果不转换到 BP 空间：
- 50 BP 误差的 MSE = (50)² = 2500，而 λ_s = 1e-3，L1 惩罚微乎其微
- MSE 狂暴引力彻底碾碎 Sparsity 约束，模型抛弃所有结构先验
- **修正**: pred/target 乘 10000 转 BP 空间，再除以 SCALE_FACTOR=10000 将 MSE 压回 0.1~1.0

### 2. 微观噪声放大 (The Noise Trap)
A 股 L1 盘口有大量微观结构噪音（异常大单、洗盘撤单、交易所数据毛刺）：
- 1000 BP 跳价毛刺 → MSE 误差 1,000,000 + 梯度 2000（核弹级）
- 两三个毛刺即可炸毁数千次迭代积累的微弱拓扑权重
- **修正**: 强制 clamp(±500 BP)，允许真 Alpha 区间内无界重赏但斩断离谱毛刺

## 理由
这是 C-056 (MSE量纲碾压与噪声过拟合风险) 的工程实现。在释放无界梯度前必须确保：(1) MSE 与 λ_s 处于公平博弈天平 (2) 极端毛刺不会单步摧毁模型权重。

## 影响文件
- `omega_epiplexity_plus_core.py`: compute_spear_loss_unbounded_audited 中的 BP 投影、SCALE_FACTOR、clamp
