# Reports 目录索引

## Phase 结果报告 (按 Phase 编号)

| Phase | 目录/文件 | 关键指标 | 状态 |
|-------|---------|---------|------|
| 3 | [`phase3/PHASE3_V15_TRAINING_REPORT.md`](phase3/PHASE3_V15_TRAINING_REPORT.md) | FVU=0.9997 | MDL 杀信号 |
| 6 | `phase6/phase6_results/` (JSON only) | ⚠️ INS-072 已作废全部基线 | 仅供考古 |
| 7 | [`phase7/PHASE7_REPORT.md`](phase7/PHASE7_REPORT.md) | ⚠️ daily IC=0.028, 不对称比=1.20 | 基于已作废 Phase 6 checkpoint |
| 8 | [`phase8/PHASE8_REPORT.md`](phase8/PHASE8_REPORT.md) | Sharpe=0.66, 不对称比=1.21 | 同上 |
| 9 | [`phase9/PHASE9_EVIDENCE.md`](phase9/PHASE9_EVIDENCE.md) | 7 job 全败 | 奖励劫持 |
| 10 | [`phase10/Phase_10_Vanguard_V5_Report.md`](phase10/Phase_10_Vanguard_V5_Report.md) | PfRet=0.210, Beta 走私 | FAIL |
| 11 | [`phase11/phase11_complete_data_summary.md`](phase11/phase11_complete_data_summary.md) | 全阶段汇总 | 散在根目录 |
| 11d | [`phase11/phase11d_training_complete.md`](phase11/phase11d_training_complete.md) | Rank IC=-0.026 | FAIL |
| 13 | [`postflight/phase13_v1_global_results.json`](postflight/phase13_v1_global_results.json) | **Rank IC=+0.029** | ✅ 首次正向 (Phase 15 证实为选择偏差, 真实均值 ~0.010) |
| 14 | [`phase14/phase14_step0_step1.json`](phase14/phase14_step0_step1.json) | Phase 6 T29 复测: Rank IC=0.0023 | Phase 6 信号死亡 |
| **15** | **[`phase15/phase15_summary.md`](phase15/phase15_summary.md)** | **Omega IC_ema=0.012, MLP IC_ema=0.016** | **🔴 MLP > Omega (203x 容量混淆)** |

## 审计报告

→ [`audits_and_insights/INDEX.md`](audits_and_insights/INDEX.md) (四方独立审计 + Phase 15 外审 + Vertex AI 审计)

## 其他

| 文件 | 内容 |
|------|------|
| [`general/Epiplexity.md`](general/Epiplexity.md) | Epiplexity 理论文档 |
| `predictions.parquet` | 推理输出 (raw) |
| `phase10_predictions.parquet` | Phase 10 推理输出 |
| [`phase11/phase11_engineer_analysis_for_architect.md`](phase11/phase11_engineer_analysis_for_architect.md) | Phase 11 工程分析给架构师 |
