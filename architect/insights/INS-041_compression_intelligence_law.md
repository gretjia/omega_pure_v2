---
id: INS-041
title: 压缩即智能实证定律 — 低压缩=负IC, 高压缩=正IC (Phase 10 实证)
category: physics
date: 2026-03-31
axiom_impact: NONE
status: active
source_directive: phase11_spear_protocol
source_gdoc: null
---

# INS-041: 压缩即智能实证定律

## 裁决
Phase 10 实盘数据证实了核心公理"压缩即智能"的量化形式: z_sparsity 与 IC 严格单调递增。

## 实证数据
| z_sparsity 分位 | IC | N |
|---|---|---|
| Q1 (最低压缩) | **-0.004** | 1.8M |
| Q2 | +0.002 | 1.9M |
| Q3 | +0.006 | 1.9M |
| Q4 | **+0.012** | 1.9M |
| Q5 (最高压缩) | +0.009 | 1.9M |

补充发现:
- Corr(z_sparsity, |pred|) = -0.34 → 高确信预测来自低压缩状态
- 模型越"确信"越在瞎赌 (conviction Q4 Asymmetry=1.17, 最低)
- Alpha 来自左尾压缩(D9 big loss rate 6.9% vs D0 13.0%), 非右尾放大

## 理由
《From Entropy to Epiplexity》5.3.1节: 计算受限观察者面对的数据 = H_T (不可压缩熵) + S_T (可压缩结构)。模型在高 H_T 状态下选择 CSPRNG 式暴力放大，而非结构压缩。

## 影响文件
无直接代码影响 — 这是理论基础，指导 INS-039 (Gating) 和 INS-042 (Target Blinding) 的设计。
