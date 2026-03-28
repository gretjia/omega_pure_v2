---
id: INS-018
title: 横截面相对论 — MSE→IC Loss + 绝对收益→截面Z-score
category: training
date: 2026-03-28
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirmation
source_directive: 2026-03-28_cross_sectional_relativity.md
source_gdoc: null
---

# INS-018: 横截面相对论 — MSE→IC Loss + 绝对收益→截面Z-score

## 裁决
Huber/MSE Loss 在 A 股极低信噪比环境下失效。负 Spread (-1.67BP) 证明模型特征有效但方向被 Loss 逼反。需要双重手术：Target 换为截面 Z-score（剥离 Beta），Loss 换为 Pearson Correlation (IC Loss)（直接优化排序）。

## 理由
1. MSE 优化绝对值，天然向均值回归，不关心截面排序
2. 绝对收益包含 90% 大盘 Beta 噪音，模型在 Alpha 和 Beta 之间精神分裂
3. 截面 Z-score 物理湮灭 Beta，让模型专注 "谁比谁强"
4. IC Loss 直接优化相关性，奖励正确排序而非正确数值
5. $325 的实验排除了架构/特征问题，精准定位到 Loss/Target

## 影响文件
- `train.py`: 替换 compute_robust_loss → pearson_correlation_loss + anchor
- `train.py`: 废弃 FVU 监控，新增 Rank IC 监控
- `backtest_5a.py`: 更新评估逻辑
- ETL/Dataset: 需要预计算截面 Z-score Target（离线，非训练时）
- `architect/current_spec.yaml`: loss, metric 字段更新
