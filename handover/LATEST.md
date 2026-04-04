# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-04 — **STATUS: Phase 12 post-flight COMPLETE — 信号弱但真实存在。Strategy B 管线验证通过，阻塞新训练直到架构修复。**

## Current State
- **Phase 12 post-flight COMPLETE**: E0 CS D9-D0=5.99 BP (t=2.23 显著), Rank IC=-0.019 (排序反转)
- **Phase 13 spec FINAL**: IC Loss + Cross-Sectional + Topological Unblocking (Codex+Gemini 审计通过)
- **Strategy B 管线验证**: 代码管线确认无 Train-Serve Skew（Codex 审计）。Phase 6 D9-D0=-5.92 是真实模型行为，非代码 bug
- **Pipeline Validation Gate (R-017)**: 新训练被阻塞，直到架构修复完成
- **新教训 C-062~C-067**: torch.compile bug / GCS FUSE / staging 磁盘 / 管线验证优先 / 不用换 Loss 解决管线 bug / AI 口头同意≠执行

## Changes This Session (8 commits)
- `f57861a` 11 轮外部审计 + torch.compile _orig_mod 修复 + 死代码清理 + gcp/ 同步
- `eb940e2` README + handover/README 更新（审计入口 + 文件地图）
- `cade569` Phase 12 审计 prompt（供外部 AI agent 审计）
- `58fcdb2` Phase 13 spec FINAL（IC Loss + Cross-Sectional + Topological Unblocking）
- `64a28a1` Strategy B 管线验证门禁 + C-065/C-066 教训
- `dd7ba30` R-017 推理对齐门禁 + C-067 教训

## Key Decisions
- **Strategy B > Strategy A**: Gemini 裁定"不要用换 Loss 解决管线 bug"。先验证管线，再训练
- **截面排序改善 33% 但不翻转根因**: CS D9-D0=5.99 > 全局 4.51，但仍远 < 25 BP 成本
- **Phase 6 IC=0.066 基准不可信**: post-flight daily IC 只有 0.028，D9-D0=-5.92（负值）
- **MDL 只杀信号**: E0 (lambda_s=0) 全面优于 E19 (lambda_s=1e-4)
- **Leaky Blinding 导致波动率预测**: Gemini 数学证明，pred_mean=34.42 精确匹配变换目标期望 32.07

## Next Steps
1. **[P0] 架构修复 (INS-068)**: 去 Global Mean Pooling → Attention Pooling + 加残差+Pre-LN + RPB 修复
2. **[P0] 用修复后架构跑 overfit test**: 验证 loss 能否归零
3. **[P1] Phase 13 训练**: IC Loss + 修复后架构 + 截面评估
4. **[P2] 历史基准重验**: Phase 6 T29 用修复后代码重跑 post-flight（确认 IC=0.066 是否可信）

## Warnings
- **linux1 SSH 不稳定**: OOM 后 Connection refused，推理已改用 Vertex AI
- **所有新训练被 R-017 + Strategy B 阻塞**: 必须先完成架构修复
- **postflight_analysis.py 已修改但未提交**: 新增 Step 7 截面分析
- **Phase 13 spec 中 RPB 修复方案未最终选定**: "先 debug，不行换 sinusoidal"

## Remote Node Status
- linux1: SSH 不稳定 (OOM 恢复缓慢)，推理改用 Vertex AI
- Vertex AI: T4 GPU 正常，GCS FUSE 模式推理已验证

## Architect Insights (本次会话)
- INS-065: Drop Leaky Blinding (100x 梯度压缩 → 波动率预测)
- INS-066: Revert to IC Loss (MSE 在 2.4% SNR 下退化)
- INS-067: Cross-Sectional Evaluation (全局 D9-D0 有波动率偏差)
- INS-068: Topological Unblocking (残差 + Attention Pooling + RPB)
- INS-069: Remove MDL L1 (杀信号不杀噪声)
- 架构师审计裁决已归档: architect/directives/2026-04-04_phase13_audit_verdict_and_roadmap.md

## Machine-Readable State
```yaml
phase: "13_ic_loss_topological_unblocking"
status: "spec_final_awaiting_architecture_fix"
blocking_gate: "R-017 + Strategy B — no training until architecture fixed"
harness:
  version: "v3_living"
  rules_active: 17  # +R-017
  incidents_total: 67  # +C-062~C-067
  hooks: 10
  skills: 9
docker: "omega-tib:phase12-postflight-v1"
postflight:
  e0_cs_d9d0: 5.99
  e0_cs_pearson_ic: 0.0095
  e0_cs_rank_ic: -0.0193
  e0_cs_positive_days: "229/399 (57.4%)"
  e19_cs_d9d0: 4.55
  verdict: "signal exists but too weak (5.99 < 25 BP cost)"
spec:
  status: "FINAL — Codex 9/9 + Gemini 7/7"
  loss: "Per-Date IC Loss (Pearson)"
  pooling: "AttentionPooling (pending implementation)"
  residual: "Pre-LN (pending implementation)"
  lambda_s: 0
strategy_b:
  step1_rerun_historical: "NOT NEEDED — Codex confirmed no train-serve skew"
  step2_frt_investigation: "NOT NEEDED — old inference also had FRT"
  step3_cross_sectional: "DONE — CS D9-D0=5.99, improves 33% but doesn't flip"
  step4_architecture_fix: "NEXT — INS-068"
  step5_phase13_training: "BLOCKED until step4"
new_lessons: ["C-062", "C-063", "C-064", "C-065", "C-066", "C-067"]
new_insights: ["INS-065", "INS-066", "INS-067", "INS-068", "INS-069"]
new_rules: ["R-017"]
audit_reports:
  - "handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md"
  - "handover/PHASE12_AUDIT_PROMPT.md"
  - "handover/STRATEGY_B_PIPELINE_VALIDATION.md"
```
