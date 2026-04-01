# 审计与洞察索引

外部审计报告 + 架构师 GDoc 精选文档。与 `architect/insights/` (INS-xxx 决策卡片) 互补，本目录存放完整审计原文和深度分析。

---

## Gemini 外部审计

| 文件 | 日期 | 审计对象 | 结论 |
|------|------|---------|------|
| [gemini_bitter_lessons.md](gemini_bitter_lessons.md) | 2026-03-18 | Gemini CLI 48h 灾难复盘 | 8 条经验教训 (Ω5 教训源) |
| [2026-03-30_gemini_softmax_portfolio_loss_audit.md](2026-03-30_gemini_softmax_portfolio_loss_audit.md) | 2026-03-30 | Softmax Portfolio Loss 数学验证 | 3 轮通过 → INS-033 |
| [2026-03-30_gemini_gcs_io_optimization_audit.md](2026-03-30_gemini_gcs_io_optimization_audit.md) | 2026-03-30 | GCS I/O FUSE v2 方案审计 | 通过 |

## 架构师 GDoc 数学验证 (id1-id6 精选)

| 文件 | 源 GDoc | 主题 | 关联 INS |
|------|---------|------|---------|
| [id1_math_verification.md](id1_math_verification.md) | id1 | SRL Inverter 数学推导验证 | INS-005 |
| [id2_engineering_audit.md](id2_engineering_audit.md) | id2 | 工程架构全面审计 (63KB) | INS-001~008 |
| [id3_fix_recommendations.md](id3_fix_recommendations.md) | id3 | 审计修复建议清单 | INS-001~008 |
| [id4_srl_friction_calibration.md](id4_srl_friction_calibration.md) | id4 | SRL 摩擦系数 c 校准 | INS-005 |
| [id5_mae_vs_intent_prediction.md](id5_mae_vs_intent_prediction.md) | id5 | MAE vs Intent Prediction 裁决 | INS-003, INS-008 |
| [id6_vd_physics_ruling.md](id6_vd_physics_ruling.md) | id6 | V_D 物理规律判定 | INS-002 |

## 综合洞察

| 文件 | 来源 | 内容 |
|------|------|------|
| [omega_core_insights.md](omega_core_insights.md) | GDoc 汇编 | Omega 核心洞察全集 (63KB) — 物理法则 + 压缩理论 + 市场微观结构 |

---

> **导航提示**: 结构化决策卡片 (INS-001~048) 在 [`architect/insights/INDEX.md`](../../architect/insights/INDEX.md)；架构师原始指令在 [`architect/INDEX.md`](../../architect/INDEX.md)
