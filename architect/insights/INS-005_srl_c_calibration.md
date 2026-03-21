---
id: INS-005
title: SRL c 摩擦系数特异性标定
category: physics/axiom
date: 2026-03-18
axiom_impact: LAYER1_TO_LAYER2_DOWNGRADE
status: active
source_directive: 2026-03-18_v3_full_design_audit.md
source_gdoc: id4_srl_friction_calibration.md
---

# INS-005: c 从 Layer 1 永恒常数 → Layer 2 Per-Stock 标定值

## 裁决

**公理降级**：SRL 前置系数 c 不再是全局不变常数 (0.842 from TSE)，而是 per-stock 动态标定值。

- δ = 0.5: 仍为宇宙拓扑常数（Layer 1，不可修改）
- c: 降级为生态摩擦系数（Layer 2，因市场/股票而异）
  - 大盘银行股: c_i ≈ 0.3-0.8（盘口厚如城墙）
  - 微盘妖股: c_i > 1.5（盘口薄如蝉翼）
  - c_default = 0.842 仅为 TSE 回退值

## 标定方法

OLS 无截距回归，同向游程 (Directional Runs) 切分代理母单：
```
c_i = Σ(X_k × Y_k) / Σ(X_k²)
X = √(Q/V_D)    (无量纲化成交量冲击)
Y = ΔP/σ_D      (无量纲化价格冲击)
```

## 影响文件

- `tools/omega_srl_friction_calibrator.py`: 全市场标定脚本
- `omega_epiplexity_plus_core.py`: `AxiomaticSRLInverter` 接受 `c_friction` 张量输入
- `tools/omega_etl_v3_topo_forge.py`: 写入 c_friction 到 shard
- `omega_webdataset_loader.py`: 传递 c_friction 到模型
- `CLAUDE.md`: 规则 #2, #11 更新
- `architect/current_spec.yaml`: `physics.c_tse` → `physics.c_default`
- `a_share_c_registry.json`: 全市场 c_i 输出
