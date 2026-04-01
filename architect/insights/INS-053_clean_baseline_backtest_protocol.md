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
Phase 11c 训练完成后（E20），必须执行三步净网验证：(1) pred_bp std 断言 ~300-400 BP，(2) 无门控纯 BP 回测 → Asymmetry Ratio 目标 1.5+，(3) 十分位 Alpha 分解验证 Epiplexity 公理（高压缩=高 Alpha=适度 |pred|）。

## 理由
* 去除 216x 放大镜后，首次可在真实物理标尺下验证 Phase 11c 模型的交易能力
* 非对称 Target 遮蔽（clamp≥0）下，模型应丧失大跌预测倾向，专攻右尾主升浪
* 如果十分位分解证明"低 S_T = 高 Alpha"，则 From Entropy to Epiplexity 理论在 A 股获证，可重启 Epiplexity Gating（INS-039 FAILED 的根因已排除）

## 影响文件
* `tools/phase7_inference.py` — 生成新 predictions.parquet
* `backtest_5a.py` — 无门控纯 BP 回测
* 需新建十分位分解分析脚本（类似 P0 证据包）
