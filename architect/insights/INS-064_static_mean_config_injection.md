---
id: INS-064
title: Static Mean 全局先验注入 — 严禁 Batch 内动态计算
category: training
date: 2026-04-02
axiom_impact: NONE
status: active
source_directive: 2026-04-02_audit_override_excess_alpha.md
source_gdoc: null
---

# INS-064: Static Mean 全局先验注入 — 严禁 Batch 内动态计算

## 裁决
STATIC_MEAN_BP 必须从 Loss 内部硬编码中抽离为函数传参（默认值 40.0）。该值由 ETL 管道在整个 In-Sample 训练集上做一次性全局统计得出，写入 config.yaml 静态注入。严禁在 Loss 函数内使用 `target.mean()` 等 Batch 内动态统计。

## 理由
Batch 内动态居中触发 INS-049（跨时空 Batch 毒化）：乱序 WebDataset 下同一 Batch 内的股票来自不同日期/板块，动态 mean 产生交叉泄露，毁掉点对点因果性。用"静态物理锚点"代替"动态统计游标"。

## 影响文件
- `omega_epiplexity_plus_core.py`: compute_spear_loss_unbounded_audited — STATIC_MEAN_BP 改为函数参数
- `gcp/phase11e_config.yaml` / train CLI: 注入 static_mean_bp
