---
id: INS-053
title: 净网回测协议 — 绝对 BP 标尺验证 + Epiplexity 扭转验证
category: metrics
date: 2026-04-01
axiom_impact: NONE
status: pending_e20_completion
source_directive: 2026-04-01_train_serve_skew_resolution.md
source_gdoc: null
---

# INS-053: 净网回测协议 — 绝对 BP 标尺验证 + Epiplexity 扭转验证

## 裁决
Phase 11c E20 完成后执行三步净网验证：(1) pred_bp std 断言 ~300-400 BP，(2) 无门控纯 BP 回测 → Asymmetry Ratio 目标 1.5+，(3) 十分位 Alpha 分解验证 Epiplexity 公理。

## 理由
* 去除 216x 放大镜后首次在真实物理标尺下验证模型交易能力
* 如果十分位分解证明"低 S_T = 高 Alpha"，则 Epiplexity 理论在 A 股获证，可重启 Gating

## 影响文件
* `tools/phase7_inference.py` — 生成 predictions.parquet
* `backtest_5a.py` — 无门控回测
* `tools/phase7_simulate.py` — Asymmetry/Profit Factor
