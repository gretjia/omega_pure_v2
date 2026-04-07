# Phase 15 Comprehensive Results Summary
**Date**: 2026-04-07
**Purpose**: Pipeline Stabilization + Attribution Baseline
**Source**: Four-way independent audit (Codex + Gemini + Claude ×2)
**Total Cost**: ~$15 (Step 1 $8 + Step 2 $7)

---

## Step 0: Data Integrity Verification ✅

- v3 shards 无 date 字段 (meta.json 只有 symbol + timestamp 序号)
- ETL v3 代码确认按 YYYYMMDD 排序处理 parquet: `all_files.sort(key=lambda p: basename(p)[:8])`
- Sample ID 跨 shard 单调递增: shard_00000 (id=0) → shard_01594 (id=7970000) → shard_01991 (id=9955000)
- **结论**: Shard 时序排序正确。Embargo gap (2 shards/side) 已实现。

---

## Step 1: Training Stabilization 🟠

**Job**: `3385623196454617088` | T4 SPOT | pd-ssd 1000GB staging | 9.5h | ~$8

### Config (vs Phase 13)
| Parameter | Phase 13 | Phase 15 Step 1 |
|-----------|---------|-----------------|
| grad_accum | 1 | **16** (effective batch 4096) |
| steps_per_epoch | 5000 | **4992** (312×16) |
| OneCycleLR total | 75,000 | **4,680** (312×15) |
| EMA | none | **decay=0.999, start E10** |
| LR after EMA | OneCycleLR | **constant 3e-5** |
| embargo_shards | 0 | **2** |
| I/O | pipe (GCS streaming) | **staging (pd-ssd local)** |
| VM | ON_DEMAND | **SPOT** |

### Epoch-by-Epoch Results
| Epoch | Rank IC | D9-D0 (BP) | IC_loss | Std_yhat | EMA |
|-------|---------|-----------|---------|----------|-----|
| 0 | +0.0099 | +2.69 | -0.012 | 443 | |
| 1 | +0.0118 | +5.57 | -0.023 | 461 | |
| 2 | +0.0113 | +4.16 | -0.029 | 624 | |
| 3 | +0.0065 | +1.20 | -0.013 | 784 | |
| 4 | +0.0117 | +5.59 | -0.021 | 608 | |
| 5 | +0.0083 | +5.83 | -0.018 | 495 | |
| 6 | +0.0096 | +3.93 | -0.015 | 776 | |
| 7 | +0.0088 | +4.36 | -0.032 | 615 | |
| 8 | +0.0112 | +4.14 | -0.025 | 719 | |
| 9 | +0.0121 | +4.63 | -0.030 | 778 | |
| 10 | +0.0122 | +4.18 | -0.018 | 767 | ✅ EMA start |
| 11 | +0.0125 | +4.62 | -0.026 | 665 | ✅ |
| **12** | **+0.0134** | +5.42 | -0.022 | 572 | ✅ **best** |
| 13 | +0.0116 | +7.09 | -0.026 | 420 | ✅ |
| 14 | +0.0099 | +6.52 | -0.030 | 404 | ✅ |

### Key Metrics
| Metric | Phase 15 Step 1 | Phase 13 | Delta |
|--------|----------------|----------|-------|
| **IC_ema** | **+0.0122** | N/A (no EMA) | — |
| IC_best | +0.0134 (E12) | +0.0292 (E9) | -0.016 |
| IC_mean (E0-E14) | +0.0104 | +0.0100 | **+0.0004** |
| 震荡振幅 | **0.007** | 0.022 | **3x 更稳定** |
| 全正率 | 15/15 | 15/15 | 同 |

### Step 1 Findings
1. **Phase 13 IC=0.029 确认为选择偏差** — 真实信号 ~0.010-0.013
2. **grad_accum=16 有效减震** — 振幅从 0.022 降到 0.007 (3x)
3. **EMA 效果有限** — IC_ema=0.0122，E12 达峰后下降
4. **训练噪声不是主要瓶颈** — 稳定化后 IC 均值未大幅提升
5. **不延长到 E25** — EMA 阶段 E12→E14 斜率为负

---

## Step 2: MLP Baseline (Attribution) 🔴

**Job**: `6510716717570719744` | T4 SPOT | pd-ssd 1000GB staging | 5.3h | ~$7

### Model
- **MLPBaseline**: LayerNorm(9600) → Linear(9600,512) → GELU → Linear(512,128) → GELU → Linear(128,1)
- **Parameters**: 5,000,705 (vs Omega-TIB 24,581 = 203x)
- **Preserves**: SRL physics + FRT transform (via MLPWithFRT adapter)
- **Removes**: FWT topology attention + information bottleneck + AttentionPooling

### Epoch-by-Epoch Results
| Epoch | Rank IC | D9-D0 (BP) | IC_loss | Std_yhat | Pearson IC |
|-------|---------|-----------|---------|----------|------------|
| 0 | -0.0046 | -4.00 | -0.013 | 32,536 | -0.0043 |
| 1 | **+0.0208** | +11.28 | -0.023 | 38,873 | +0.0129 |
| 2 | +0.0173 | +11.34 | -0.030 | 39,643 | +0.0127 |
| 3 | +0.0177 | +7.80 | -0.027 | 75,354 | +0.0118 |
| 4 | +0.0057 | +7.54 | -0.033 | 50,676 | +0.0100 |
| 5 | +0.0120 | +9.33 | -0.032 | 46,734 | +0.0130 |
| 6 | +0.0046 | +4.66 | -0.029 | 67,305 | +0.0086 |
| 7 | +0.0060 | +5.42 | -0.028 | 57,709 | +0.0071 |
| 8 | +0.0117 | +10.35 | -0.029 | 49,434 | +0.0145 |
| 9 | +0.0042 | +2.76 | -0.032 | 51,504 | +0.0065 |
| 10 | +0.0159 | +10.64 | -0.038 | 52,539 | +0.0154 |
| 11 | **+0.0183** | **+12.42** | -0.036 | 60,615 | +0.0174 |
| 12 | +0.0105 | +8.40 | -0.047 | 41,559 | +0.0145 |
| 13 | +0.0167 | +11.96 | -0.032 | 50,426 | +0.0181 |
| 14 | +0.0147 | +10.62 | -0.040 | 40,821 | +0.0176 |

### Key Metrics
| Metric | MLP | Omega | MLP/Omega |
|--------|-----|-------|-----------|
| **EMA Rank IC** | **+0.0159** | +0.0122 | **130%** |
| **EMA D9-D0** | **+10.63 BP** | +4.19 BP | **254%** |
| Best single | +0.0208 (E1) | +0.0134 (E12) | 155% |
| Mean (E1-E14) | +0.0117 | +0.0104 | 113% |
| Parameters | 5,000,705 | 24,581 | **203x** |
| Std_yhat | 40K-75K | 400-800 | 方差爆炸 |

### Step 2 Findings
1. **MLP 全面碾压 Omega-TIB** — IC 130%, D9-D0 254%
2. **但 203x 参数差距是混淆变量** — 不是公平容量对比
3. **MLP Std_yhat 极高 (40K-75K)** — 方差爆炸但 IC 仍高于 Omega
4. **MLP 保留了 SRL+FRT** — 结论仅适用于 FWT+瓶颈+AttentionPooling 的增量

---

## Phase 15 Decision Tree Outcome

```
Step 1: IC_ema=0.0122 → 🟠 (无明显改善，架构可能是瓶颈)
  ↓
Step 2: MLP/Omega = 130% → 🔴 (拓扑几乎无增量)
  ↓
决策树: "战略转向 — 停架构，转特征/数据"
  ↓
⚠️ 但 203x 参数差异 → 结论待容量匹配实验确认
```

---

## Unresolved Question: Capacity Confound

当前 🔴 结论有一个关键混淆变量：

| | Omega-TIB | MLP Baseline |
|---|-----------|-------------|
| 参数量 | 24,581 | 5,000,705 |
| 架构 | SRL → FWT → 瓶颈 → AttentionPool | SRL → FRT → Flatten → 3层MLP |
| 改变了两个变量 | (1) 架构 | (2) 容量 |

如果 MLP 的优势来自 203x 更多参数而非架构差异，那么 🔴 结论是错误的。

**需要的实验**: 容量匹配 MLP (~25K-100K params)
- 如果容量匹配 MLP ≈ Omega → 拓扑确实无用
- 如果容量匹配 MLP << Omega → 拓扑有用，但 Omega 需要更多参数

---

## Cost Summary

| Item | Cost |
|------|------|
| Step 1: T4 SPOT 9.5h | ~$3.50 |
| Step 1: pd-ssd 1000GB 9.5h | ~$4.50 |
| Step 2: T4 SPOT 5.3h | ~$2.00 |
| Step 2: pd-ssd 1000GB 5.3h | ~$2.50 |
| Failed jobs (v1 disk full, v2 gcloud flag) | ~$2.00 |
| **Total Phase 15** | **~$14.50** |
