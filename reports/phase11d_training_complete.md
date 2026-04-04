# Phase 11d Training Complete Record

**Date**: 2026-04-02
**Duration**: ~22h wall clock (含 Spot 抢占 + On-Demand 切换)
**Docker**: omega-tib:phase11d-v1

---

## Config A (λ_s=1e-4, δ=200) — SUCCEEDED ✅ 20/20 epochs

best.pt: E17 (PfRet=7.31, saved 13:12 UTC) — Note: Spot resume 后 best 追踪重置
best.pt 实际保存时间: gs timestamp 2026-04-02T13:12:06Z

| Epoch | Val Loss | Trn Loss | PfRet | Std_yhat (BP) | S_T | Notes |
|-------|----------|----------|-------|---------------|-----|-------|
| E0 | 5283 | 5729 | 7.15 | 8.22 | 176 | warmup |
| E1 | 5236 | 5665 | 7.20 | 14.23 | 222 | warmup |
| E2 | 5227 | 5150 | 7.27 | 16.17 | 224 | λ_s kicks in |
| E3 | 5230 | 5346 | 7.22 | 15.21 | 227 | Spot恢复 |
| E4 | 5303 | 5327 | 7.14 | 13.76 | 227 | |
| E5 | 5219 | 5555 | 7.34 | 15.09 | 229 | Spot恢复 |
| E6 | 5220 | 5503 | 7.27 | 17.34 | 227 | |
| E7 | 5229 | 5521 | 7.30 | 17.77 | 231 | |
| E8 | 5287 | 5459 | 7.30 | 19.93 | 228 | |
| E9 | 5262 | 5500 | 7.30 | 14.79 | 231 | |
| E10 | 5228 | 5683 | 7.32 | 14.79 | 225 | |
| E11 | 5308 | (Spot) | 7.44 | 22.23 | — | Spot恢复, PfRet peak |
| E12 | 5244 | 5438 | 7.30 | 17.28 | 230 | |
| E13 | 5243 | 5291 | 7.30 | 18.04 | 229 | |
| E14 | 5212 | 5641 | 7.36 | 18.59 | 232 | |
| E15 | 5209 | 5117 | 7.25 | 16.63 | 228 | On-Demand开始, 退火 |
| E16 | 5208 | 4991 | 7.21 | 16.13 | 229 | 退火 |
| E17 | 5209 | 5552 | 7.31 | 17.39 | 234 | best.pt saved |
| E18 | 5208 | 5840 | 7.29 | 17.28 | 235 | |
| E19 | 5207★ | 5386 | 7.28 | 17.20 | 234 | 最终, Val Loss最低 |

**Summary A:**
- Best Val Loss: 5207 (E19, 最终 epoch)
- Best PfRet: 7.44 (E11, Spot恢复 partial epoch)
- Peak Std_yhat: 22.23 (E11)
- Stable Std_yhat: 16-18 BP (E12-E19)
- Stable S_T: 225-235
- best.pt GCS timestamp: 2026-04-02T13:12:06Z

---

## Config B (λ_s=1e-5, δ=200) — E18完成, E19 step 4500崩溃 (exit 1)

best.pt: E16 (PfRet=7.31, saved 12:43 UTC)
best.pt 实际保存时间: gs timestamp 2026-04-02T12:43:11Z

| Epoch | Val Loss | Trn Loss | PfRet | Std_yhat (BP) | S_T | Notes |
|-------|----------|----------|-------|---------------|-----|-------|
| E0 | 5329 | 5742 | 7.07 | 8.72 | 179 | warmup |
| E1 | 5253 | 5519 | 7.35 | 16.23 | 221 | warmup |
| E2 | 5220 | 5501 | 7.11 | 13.90 | 229 | λ_s kicks in |
| E3 | 5232 | 5242 | 7.24 | 13.16 | 231 | |
| E4 | 5253 | 5453 | 7.41 | 22.52 | 235 | Std peak |
| E5 | 5219 | 5524 | 7.42 | 18.34 | 233 | PfRet peak (pre-Spot) |
| E6 | 5216 | 5446 | 7.25 | 17.01 | 229 | Spot恢复 |
| E7 | 5231 | (Spot) | 7.22 | 19.31 | — | Spot恢复 |
| E8 | 5242 | 5276 | 7.06 | 11.55 | 230 | Std dip |
| E9 | 5233 | 5339 | 7.30 | 16.14 | 234 | |
| E10 | 5216 | (Spot) | 7.24 | 16.68 | — | Spot恢复 |
| E11 | 5218 | (Spot) | 7.24 | 17.79 | — | Spot恢复 |
| E12-14 | — | — | — | — | — | Spot跳过 |
| E15 | 5215 | (Spot) | 7.18 | 15.51 | — | On-Demand resume |
| E16 | 5206 | 5942 | 7.31 | 17.65 | 238 | best.pt saved |
| E17 | 5212 | 5447 | 7.21 | 16.18 | 233 | |
| E18 | 5205★ | 5144 | 7.29 | 16.86 | 231 | Val Loss最低 |
| E19 | — | crashed at step 4500/5000 | | | | exit code 1 |

**Summary B:**
- Best Val Loss: 5205 (E18)
- Best PfRet: 7.42 (E5, pre-Spot)
- Peak Std_yhat: 22.52 (E4)
- Stable Std_yhat: 15-18 BP (E6-E18)
- Stable S_T: 229-238
- best.pt GCS timestamp: 2026-04-02T12:43:11Z
- ⚠️ best.pt 被 Spot resume 多次重置 (11次 "New best" events)，实际对应 E16

---

## 最终对比

|                    | Config A (λ_s=1e-4) | Config B (λ_s=1e-5) |
|--------------------|---------------------|---------------------|
| 完成状态           | SUCCEEDED 20/20     | FAILED E19 (数据E18完整) |
| Best Val Loss      | 5207 (E19)          | 5205★ (E18)         |
| Best PfRet         | 7.44 (E11)          | 7.42 (E5)           |
| best.pt PfRet      | 7.31 (E17)          | 7.31 (E16)          |
| Peak Std_yhat      | 22.23 (E11)         | 22.52 (E4)          |
| Stable Std_yhat    | 16-18 BP            | 15-18 BP            |
| Stable S_T         | 225-235             | 229-238             |
| Spot 抢占次数      | 3                   | 4+                  |
| best.pt 可靠性     | ⚠️ resume重置1次    | ⚠️ resume重置多次   |

**结论: 两者极其接近，差异在统计噪声范围内。**

---

## Phase 11c → 11d 改善对比

|                    | Phase 11c (δ=50, λ=1e-3) | Phase 11d (δ=200, λ=1e-4/5) |
|--------------------|--------------------------|------------------------------|
| pred_std (真实)    | 1.3-5.7 BP (脑死亡)      | 15-22 BP (3-4x 改善) ✅      |
| z_core (S_T)       | 116-157 (半死)            | 225-238 (活跃) ✅             |
| PfRet              | 6.89-7.23                | 7.07-7.44                    |
| Val Loss           | 2354-2413 (δ=50量纲)     | 5205-5329 (δ=200量纲)        |
| 模型行为           | 输出常数 ~30 BP           | 有区分度的个股预测            |

---

## Checkpoints on GCS

```
gs://omega-pure-data/checkpoints/phase11d_A_v1/best.pt  (397.94 KiB, 2026-04-02T13:12:06Z)
gs://omega-pure-data/checkpoints/phase11d_A_v1/latest.pt
gs://omega-pure-data/checkpoints/phase11d_A_v1/train.log

gs://omega-pure-data/checkpoints/phase11d_B_v1/best.pt  (397.94 KiB, 2026-04-02T12:43:11Z)
gs://omega-pure-data/checkpoints/phase11d_B_v1/latest.pt
gs://omega-pure-data/checkpoints/phase11d_B_v1/train.log
```

## Next: Post-Flight Plan
→ architect/directives/2026-04-01_phase11d_post_flight_plan.md
