---
id: INS-002
title: V_D/σ_D 宏观物理量纲
category: physics
date: 2026-03-18
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-18_v3_full_design_audit.md
source_gdoc: id6_vd_physics_ruling.md
---

# INS-002: V_D 和 σ_D 必须是宏观日均值

## 裁决

SRL 反演公式中的 V_D（成交量）和 σ_D（波动率）**必须**是 20-day Rolling 宏观值，绝不可用微观局部值。

## 理由

1. `bid_v + ask_v` 是静态势能（盘口挂单），不是动态动能（成交流量）— 量纲灾难
2. Volume bar 累计成交量 = vol_threshold（常数）— 分母变死板常量，SRL 退化
3. 标定 c_i 时用的是 daily volume / daily volatility，推理时必须一致（标定-推理对称性）

## 核心变更

特征维度从 7 扩展到 10：

| 通道 | 含义 |
|------|------|
| 0-3 | Bid_P, Bid_V, Ask_P, Ask_V (不变) |
| 4 | Close (不变) |
| 5-6 | Reserved / SRL / Epiplexity |
| **7** | **delta_p** — 微观价格冲击 ΔP |
| **8** | **macro_v_d** — 20-day Rolling ADV |
| **9** | **macro_sigma_d** — 20-day Rolling ATR |

## 影响文件

- `tools/omega_etl_v3_topo_forge.py`: rolling_adv/rolling_sigma 队列 + 通道 7-9 广播
- `omega_webdataset_loader.py`: 10-channel feature 提取
- `omega_epiplexity_plus_core.py`: forward() 从 x_2d 通道 8-9 提取宏观量
- `architect/current_spec.yaml`: shape [B,160,10,7] → [B,160,10,10]
