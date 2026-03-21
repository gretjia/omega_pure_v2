---
id: INS-007
title: 相对容量时钟 (动态 vol_threshold)
category: architecture
date: 2026-03-18
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-18_v3_spatial_restoration.md
source_gdoc: null
---

# INS-007: vol_threshold = Rolling ADV × 2%，非固定 50000

## 裁决

每只股票的 volume bar 阈值必须动态化：
```
vol_threshold_i = Rolling_ADV_i × ADV_FRACTION (0.02)
```
冷启动默认值 50000，直到首个 rolling window (20 日) 填满。

## 理由

固定绝对阈值导致大盘股一天产出数百个 bar、小盘股不到 10 个 — 几何不等价。容量时钟将所有股票的 bar 密度熨平到可比范围内，使 TDA 算子接收到拓扑等价的输入。

**已记录为 Via Negativa**: "固定绝对容量阈值 → 大小盘不可比"

## 参数

- `etl.adv_fraction`: 0.02
- `etl.rolling_window`: 20 (trading days)
- `etl.vol_threshold_default`: 50000 (cold start)

## 影响文件

- `tools/omega_etl_v3_topo_forge.py`: `OmegaVolumeClockStateMachine.update_daily_macro()`
- `architect/current_spec.yaml`: etl 参数段
