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

## Phase 11 审计与烟测

| 文件 | 日期 | 内容 | 结论 |
|------|------|------|------|
| [2026-04-01_inference_scale_explosion_fix.md](2026-04-01_inference_scale_explosion_fix.md) | 2026-04-01 | 推理 216x 尺度爆炸修复 | Train-Serve Skew 根因确认 |
| [2026-04-01_phase11c_smoke_test_report.md](2026-04-01_phase11c_smoke_test_report.md) | 2026-04-01 | Phase 11c 烟测 — 216x 仪表盘幻觉揭秘 | pred_std=5.6 BP 脑死亡 |

## Phase 11 全量数据 (项目根 reports/)

| 文件 | 内容 |
|------|------|
| [../phase11/phase11_complete_data_summary.md](../phase11/phase11_complete_data_summary.md) | Phase 11 全阶段数据汇总 (11c + 11d A/B + post-flight) |
| [../phase11/phase11d_training_complete.md](../phase11/phase11d_training_complete.md) | Phase 11d 训练记录 (Config A/B epoch tables + checkpoints) |

## Omega-TIB 模型审计底稿

| 文件 | 日期 | 内容 |
|------|------|------|
| [2026-04-05_omega_tib_audit_workpapers.md](2026-04-05_omega_tib_audit_workpapers.md) | 2026-04-05 | 初版审计底稿 (Phase 3-13, 5-Agent 编制) |
| **[2026-04-06_codex_audit_workpapers.md](2026-04-06_codex_audit_workpapers.md)** | **2026-04-07** | **审计底稿 V2 (1072 行, 自包含) — 含 Phase 15 数据 + Omega Kernel 组件解剖 + 9 个未分离变量** |

## 四方独立审计 (2026-04-06)

| 文件 | 审计方 | 行数 | 核心发现 |
|------|--------|------|---------|
| [2026-04-06_audit_prompt.md](2026-04-06_audit_prompt.md) | — | — | 审计 prompt (Q1-Q15) |
| [2026-04-06_codex_audit_report.md](2026-04-06_codex_audit_report.md) | Codex GPT-5.4 | 814 | "最危险的是把近似指标成功叙述成架构真理" |
| [2026-04-06_gemini_audit_report.md](2026-04-06_gemini_audit_report.md) | Gemini 2.5 Pro | 354 | "手持屠龙之刀，只用来切豆腐" |
| [2026-04-06_claude_audit_report.md](2026-04-06_claude_audit_report.md) | Claude (独立) | 507 | 数据泄漏风险 + 梯度 SNR=0.16 精确计算 |
| **[2026-04-06_three_way_audit_synthesis.md](2026-04-06_three_way_audit_synthesis.md)** | **汇总** | **334** | **6/6 选择题一致 + 3 套 L1 数学证明 + 3 套 Tail-IC Loss 代码** |
| [2026-04-06_four_way_audit_final_conclusion.md](2026-04-06_four_way_audit_final_conclusion.md) | 最终结论 | — | Phase 13 IC=0.029 是管线修复的胜利，不是模型极限 |
| [2026-04-06_omega_tib_comprehensive_audit_datapack.md](2026-04-06_omega_tib_comprehensive_audit_datapack.md) | Claude | — | 初版审计数据包 (被 codex_audit_workpapers 取代) |

## Phase 15 Plan/Code 外部审计

| 文件 | 审计方 | 对象 | 结论 |
|------|--------|------|------|
| [2026-04-06_codex_phase15_audit.md](2026-04-06_codex_phase15_audit.md) | Codex | Plan V1 | 0 PASS, 3 WARNING, 5 FAIL → Plan V2 修正 |
| [2026-04-06_gemini_phase15_audit.md](2026-04-06_gemini_phase15_audit.md) | Gemini | Plan V1 | 1 FAIL (OneCycleLR) → Plan V2 修正 |
| [2026-04-06_codex_phase15_code_audit.md](2026-04-06_codex_phase15_code_audit.md) | Codex | Code V2 | 7 PASS, 1 FAIL (RPB grad) → 已修复 |
| [2026-04-06_gemini_phase15_code_audit.md](2026-04-06_gemini_phase15_code_audit.md) | Gemini | Code V2 | 8/8 PASS |
| [2026-04-06_gemini_vertex_ai_audit.md](2026-04-06_gemini_vertex_ai_audit.md) | Gemini | Vertex AI 适配 | 3 FAIL (staging/SPOT/disk) → 全修复 |

## 综合洞察

| 文件 | 来源 | 内容 |
|------|------|------|
| [omega_core_insights.md](omega_core_insights.md) | GDoc 汇编 | Omega 核心洞察全集 — 物理法则 + 压缩理论 + 市场微观结构 |

---

> **审计入口 (AI Agent)**:
> 1. 最新自包含底稿: [`2026-04-06_codex_audit_workpapers.md`](2026-04-06_codex_audit_workpapers.md) (1072 行, 含全部源码+数据+Phase 15 结果)
> 2. 三方审计汇总: [`2026-04-06_three_way_audit_synthesis.md`](2026-04-06_three_way_audit_synthesis.md)
> 3. Phase 15 结果: [`../../reports/phase15/phase15_summary.md`](../../reports/phase15/phase15_summary.md)
> 4. 决策卡片: [`architect/insights/INDEX.md`](../../architect/insights/INDEX.md) (INS-001~074)
> 5. 架构师指令: [`architect/INDEX.md`](../../architect/INDEX.md)
