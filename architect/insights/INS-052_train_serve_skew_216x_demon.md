---
id: INS-052
title: Train-Serve Skew — 216x 尺度放大镜幽灵
category: physics
date: 2026-04-01
axiom_impact: NONE
status: active
source_directive: 2026-04-01_train_serve_skew_resolution.md
source_gdoc: null
---

# INS-052: Train-Serve Skew — 216x 尺度放大镜幽灵

## 裁决
当训练范式从 Z-score 归一化切换到绝对 BP 输出时（Phase 11c Pointwise Spear），推理和回测脚本**必须同步更新**。遗留的 `* TARGET_STD + TARGET_MEAN` 逆向缩放在绝对 BP 模型上造成 216 倍尺度爆炸，是 Phase 10 回测中 `|pred|` 高达 4000~6000 BP 的根因。

## 理由
* Phase 11c 废除所有跨 Batch 归一化（INS-049/051），模型原生输出绝对 BP（如 20 BP）
* 旧推理脚本假设 Z-score 输出，执行 `pred * 216.24 + mean` → 20 BP 变 4324 BP
* 同时 `.squeeze()` 在 Batch=1 尾部数据上触发 C-008 维度坍缩
* 修复：移除逆向缩放 + `.squeeze()` → `.view(-1)`

## 影响文件
* `tools/phase7_inference.py` / `gcp/phase7_inference.py` — 移除 TARGET_STD/MEAN 缩放
* `backtest_5a.py` / `gcp/backtest_5a.py` — 同上
* `train.py` / `gcp/train.py` — 验证日志 pred_std 去缩放 + .view(-1)
