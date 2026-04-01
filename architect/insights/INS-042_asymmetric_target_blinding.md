---
id: INS-042
title: 非对称目标遮蔽 — clamp(target, min=0) 遮蔽左尾, 纯建仓检测
category: training
date: 2026-03-31
axiom_impact: UPDATE_REQUIRED
status: pending_p0_backtest
source_directive: phase11_spear_protocol
source_gdoc: null
---

# INS-042: 非对称目标遮蔽 (Asymmetric Target Blinding)

## 裁决
训练目标从 `forward_vwap_return` (双向) 改为 `torch.clamp(target, min=0.0)` (单向右尾)。所有下跌/崩盘/无波动统统归零。模型唯一的生存方式是从 5000 只股票中找到真正会拉升的牛股。

## 理由
Phase 10 证实单头网络发生"任务坍塌" — 把所有算力用于识别左尾(避险)而放弃右尾(选股)。遮蔽左尾后:
1. 避开大跌不再有梯度奖励 → 逼迫模型专注建仓信号
2. 熊市时 target_accumulation.sum()≈0 → 梯度仅来自 MDL L1 惩罚 → 模型自动静默(关闭神经元)，不强行拟合噪音
3. 与 INS-029 Path A (非对称目标截断) 的精神一致，但实现更极端(完全遮蔽 vs 衰减)

## 与 Phase 9 的关系
Phase 9 的非对称 Pearson (INS-030, downside_dampening=0.05) 失败，因为 Pearson 的尺度免疫性允许 Reward Hacking (INS-032)。本方案在 Softmax 框架内实现非对称，不受 Pearson 尺度免疫漏洞影响。

## 影响文件
- `train.py`: target 预处理添加 clamp(min=0)
- `omega_epiplexity_plus_core.py`: 无变更 (目标处理在训练循环中)
