---
id: INS-003
title: N+1 VWAP 延迟执行目标
category: physics/etl
date: 2026-03-18
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-18_v3_full_design_audit.md
source_gdoc: id5_mae_vs_intent_prediction.md
---

# INS-003: Target = Forward VWAP Return (BP)

## 裁决

训练目标严格定义为基于延迟执行的未来宏观容量累计收益率：

```
Entry = VWAP of bar N+1      (信号在 bar N 产生，强制延迟 1 bar)
Exit  = VWAP of bar N+1+H    (H = payoff_horizon, 默认 20 bars)
Y     = (VWAP_{exit} - VWAP_{entry}) / VWAP_{entry} × 10000  (BP)
```

## 理由

- N+1 延迟执行编码了真实市场摩擦（不可能在信号产生的同一 bar 执行）
- VWAP 而非 close/open 消除了极端 tick 噪音
- BP 单位使得跨股票、跨时期的 target 可比
- payoff_horizon=20 bars ≈ 半天~1天的持仓周期

## ETL 三步实现

1. Tick 流 → Volume Bars 序列（含每根 bar 的 VWAP）
2. 在 1D bar 序列上 shift 计算 forward target
3. Sliding window (160, stride=20) 截取 2D 矩阵，绑定最后一根 bar 的 target

## 影响文件

- `tools/omega_etl_v3_topo_forge.py`: `add_bar_and_try_emit()` 计算 forward return
- `architect/current_spec.yaml`: `training.payoff_horizon: 20`
