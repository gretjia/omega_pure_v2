---
id: INS-057
title: 突破脑死亡 — Leaky Blinding + Log-Cosh + 低特征税 (λ_s=1e-5) 成功拉开 30BP 真实价差
category: training
date: 2026-04-02
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: Autoresearch Iteration 3
source_gdoc: null
---

# INS-057: 突破脑死亡 — Leaky Blinding + Log-Cosh + 低特征税 (λ_s=1e-5) 成功拉开 30BP 真实价差

## 裁决
在拥有真实数据的本地 Windows1 (115GB VRAM) 节点上，Autoresearch 沙盒通过连续 3 次进化，成功找到了一套能突破 "25BP" 真实物理成本线的新代数公式拓扑。
最终确定的核心变异公式如下：
1. **Leaky Target Blinding (泄漏致盲):** `target_acc = torch.where(target > 0, target, target * 0.1)`，保留了做空/噪音区域 10% 的惩罚梯度，成功阻止了神经元在死区中陷入“躺平输出常数”的局面。
2. **Pointwise Log-Cosh Loss:** 彻底废除了拥有刚性截断点 (delta) 的 Huber Loss。Log-Cosh 提供了二阶导数连续的平滑优化曲面，让模型更从容地跨越局部最优。
3. **Config B 完胜:** 只有在低特征税 (`lambda_s=1e-5`) 下，此公式才能发力。Config A (`lambda_s=1e-4`) 依然因为收税过重而被压制在负收益。

## 理由
*   **物理实测:** D9-D0 Spread 达到了惊人的 **30.30 BP** (最高前10%分位点 -40.57 BP，最低后10%分位点 -70.88 BP)，说明在市场暴跌周期中，模型精准找出了最抗跌的主力护盘品种，两者的真空收益差完全覆盖了 25 BP 摩擦成本。
*   **北极星验证:** FINAL_REWARD 从基线的 `-41.5`，经由 Iteration 1 的 `-31.3`，爆发式增长到最终的 **`+30.30`**！

## 影响文件
*   `train.py` 中的 `compute_spear_loss` 已经固化此逻辑，无需使用动态变异。
*   Phase 11d 后续的 GCP 实盘任务，必须采用 Config B (`lambda_s=1e-5`) 的配合才能发挥药效。