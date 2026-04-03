---
id: INS-061
title: 空间深度恢复强制令 — ws=4 为 OOM 脏补丁，必须恢复 ws=10
category: architecture
date: 2026-04-02
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-04-02_phase12_unshackling_protocol.md
source_gdoc: null
---

# INS-061: 空间深度恢复强制令

## 裁决
`train.py:504` 和 `gcp/train.py:504` 的 `--window_size_s` 默认值为 4，违反 spec 固定值 10 和公理 8（空间轴不可拍扁）。这是早期为防 OOM 遗留的脏补丁，砍掉了 60% 的 LOB 深水区（L5-L10 档），等于挖去 Topology Attention 的双眼。真正的机构挂单流形沉淀在 L5-L10 档，`z_core` 无特征可编码是直接后果。

## 理由
公理 8 明确 LOB 是二维空间拓扑。L1-L4 档充斥最高频虚假流动性（Spoofing）和噪声。空间轴必须保持完整 10 档。

## 代码确认
- `train.py:504`: `parser.add_argument("--window_size_s", type=_int, default=4)` ← BUG
- `gcp/train.py:504`: 同上
- `phase7_inference.py:157`: `default=10` ← 正确
- `backtest_5a.py:117`: `default=10` ← 正确
- `current_spec.yaml:140`: `window_size_s: 10` ← 权威值

## 影响文件
- `train.py:504`: default 4 → 10
- `gcp/train.py:504`: default 4 → 10
