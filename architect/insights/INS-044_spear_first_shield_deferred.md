---
id: INS-044
title: Spear-First 策略 — 单头建仓优先, Shield 推迟到 Phase 12
category: architecture
date: 2026-03-31
axiom_impact: NONE
status: active
source_directive: phase11_spear_protocol
source_gdoc: null
---

# INS-044: Spear-First 策略 — Shield 推迟

## 裁决
Phase 11 只实现单头 Spear (建仓检测)，不实现 Shield (崩盘检测)。INS-038 (双头阿修罗 V2) 推迟到 Phase 12。

## 理由
架构师裁决: "试图用一个微小认知瓶颈(hd=64)同时压缩'贪婪'与'恐惧'必然导致任务坍塌。" 先集中所有认知资源专攻右尾建仓信号，等 Spear 验证有效后再增加 Shield。

复杂系统工程智慧: 先用非对称数学杠杆强行撬开"主力建仓"这一扇门。

## INS-038 状态变更
INS-038 (双头阿修罗 V2) 状态: `pending_p0_backtest` → `deferred_to_phase12`

## 影响文件
- Phase 11: 沿用现有单头 OmegaMathematicalCompressor 架构 (不改架构)
- Phase 12: 撕裂为 Spear + Shield 双头
