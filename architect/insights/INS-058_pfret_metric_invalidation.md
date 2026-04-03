---
id: INS-058
title: PfRet 评价失效 — 方差坍缩下等价于等权 Beta 均值
category: metrics
date: 2026-04-02
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-04-02_phase12_unshackling_protocol.md
source_gdoc: null
---

# INS-058: PfRet 评价失效 — 方差坍缩下等价于等权 Beta 均值

## 裁决
随机初始化的 E0 即可获得 PfRet=7.15。方差坍缩导致预测值高度集中，softmax/归一化后权重趋近均匀分布 $w_i \approx 1/N$，组合收益退化为验证集正收益目标的算术平均值（大盘多头 Beta）。PfRet 对横向排序能力（Discriminative Power）完全免疫，必须从代码中彻底删除作为 early-stopping 和 best.pt 保存依据。

## 理由
用一个对模型排序鉴别力免疫的掷骰子指标保存 Best Checkpoint，导致多个 Phase 在伪指标上空耗算力。

## 替代方案
强制切换为 **D9-D0 Spread**（头部 10% 减去尾部 10% 的收益差）或 **Rank IC**。只为真正的排序鉴别力买单。

## 影响文件
- `train.py` / `gcp/train.py`: early-stopping 逻辑、best.pt 保存条件
- `backtest_5a.py`: 评估指标计算
