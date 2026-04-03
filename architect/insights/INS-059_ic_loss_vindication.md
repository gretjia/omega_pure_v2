---
id: INS-059
title: IC Loss 历史翻案 — Phase 6 IC=0.066 为真信号，INS-018 废弃 IC Loss 为误判
category: training
date: 2026-04-02
axiom_impact: NONE
status: active
source_directive: 2026-04-02_phase12_unshackling_protocol.md
source_gdoc: null
---

# INS-059: IC Loss 历史翻案 — Phase 6 IC=0.066 为真信号

## 裁决
Phase 6 使用 IC Loss (Pearson/Spearman) 获得 IC=0.066 是真实信号（前提：验证集天数足够）。IC Loss 是尺度免疫(Scale Invariant)和位置免疫(Location Invariant)的，只惩罚"排序错误"，完美避开了方差坍缩陷阱。先前 INS-018 因模型预测绝对尺度极小而废弃 IC Loss，诊断正确但药方错误——为修正绝对尺度引入 Huber，连最宝贵的"排序能力"一起杀死了。

## 理由
这是一个典型的"治感冒切额叶"误判。IC Loss 的缺陷是不产生绝对尺度（影响资金分配计算），但这应通过解耦机制修复（如两阶段训练、小权重 MSE 锚定尺度），而非整体替换为点对点 Loss。

## 历史上下文
- INS-018: 废弃 IC Loss → 引入 Huber → 方差坍缩 → 多个 Phase 全败
- Phase 12 Action 4: 重新引入 Rank-based Loss 主导特征提取

## 影响文件
- `omega_epiplexity_plus_core.py`: Loss 函数设计
