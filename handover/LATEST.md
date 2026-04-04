# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-04 — **STATUS: Phase 13 Mandate B COMPLETE — AttentionPooling + Pre-LN 残差已实现并通过 Crucible overfit test。下一步: Mandate A (IC Loss)。**

## Current State
- **Phase 13 Mandate B DONE**: AttentionPooling 替换 GMP + Pre-LN 残差 + RPB 梯度解锁
- **Crucible overfit test PASS**: 瞬时 loss≈0.15 (R²=0.96), pred_std 非零, 单调递减
- **Docker phase13-v1 已构建**: canary 正确拒绝旧 checkpoint (Phase 13 key guard 工作)
- **Phase 13 spec FINAL**: IC Loss + Cross-Sectional + Topological Unblocking (Codex+Gemini 审计通过)
- **Mandate A (IC Loss) 待实施**: Loss 函数仍是 Phase 12 Unbounded Spear MSE

## Changes This Session (3 commits)
- `481870b` feat: Phase 13 Mandate B — AttentionPooling + Pre-LN Residual (8 文件, +144 params)
- `3018cb0` fix: lambda_s 0→0 spec 对齐 + gcp/ 完全同步 + q_metaorder clamp
- `3a5a249` docs: C-068~C-070 + Ω2 进化 + harness 硬化

## Key Decisions
- **Pipeline Gate Override for Mandate B**: 架构修复不是"换 Loss"，Crucible test 替代 Strategy B Step 1
- **Pre-LN > Post-LN**: V2 directive 说 Post-LN, Gemini 审计选 Pre-LN (防方差爆炸), 保持 spec [FINAL]
- **B.3 窗口隔离推迟**: 先验证 B.1+B.2，跨窗注意力推迟到 Phase 13 P2 (INS-070)
- **Ω2 进化**: "du -sh/df -h" → "资源承诺必须与任务目的成比例" (meta 原则, 非补窟窿)
- **einsum 替换 broadcast-multiply-sum**: Gemini 建议 /sqrt(D) 缩放 + simplify 建议 einsum

## Next Steps
1. **[P0] Mandate A — IC Loss + Cross-Sectional Evaluation**: 替换 MSE → Per-Date IC Loss, 重构 validate() 和 backtest_5a.py 的截面评估
2. **[P1] Phase 13 全面训练**: IC Loss + 修复后架构, Vizier HPO, Cross-Sectional Rank IC 为主指标
3. **[P2] Mandate B.3 — Window Isolation**: 如 P0+P1 效果不够, 实施跨窗注意力 (INS-070)

## Warnings
- **Loss 函数仍是 Phase 12 MSE**: Mandate A 尚未实施, 当前训练无意义
- **Crucible loss=0.674 是 running average**: 实际瞬时 loss≈0.15 (C-070 教训, 必须增量分析)
- **lambda_s default 已改为 0**: 旧 YAML 如果不指定 lambda_s, 现在会用 0 (Phase 13 正确行为)
- **gcp/ 镜像已完全同步**: 但结构性债务仍在 (5 文件手动 cp)

## Remote Node Status
本次会话未涉及远程节点。Crucible test 在 Vertex AI L4 ON_DEMAND 完成。

## Architect Insights (本次会话)
- INS-070: Shatter Window Isolation — 跨窗注意力打破 0.64 天感受野 (deferred to P2)
- V2 directive 已归档: architect/directives/2026-04-04_phase13_audit_verdict_and_roadmap_v2.md

## Machine-Readable State
```yaml
phase: "13_mandate_b_done_mandate_a_next"
status: "mandate_b_complete_crucible_pass"
blocking_gate: "Mandate A (IC Loss) 未实施 — MSE 仍在代码中"
harness:
  version: "v3_living"
  rules_active: 17
  incidents_total: 70  # +C-068~C-070
  hooks: 10
  skills: 9
  omega2_evolved: "proportionality principle (not just du/df)"
docker: "omega-tib:phase13-v1"
crucible:
  job_id: "5402703665888755712"
  instantaneous_loss_final: 0.15
  running_avg_loss: 0.674
  r_squared: 0.96
  pred_std: 0.010
  verdict: "PASS — architecture learns, gradients flow, model not collapsed"
spec:
  status: "FINAL — Codex 9/9 + Gemini 7/7"
  loss: "Per-Date IC Loss (Pearson) — NOT YET IMPLEMENTED"
  pooling: "AttentionPooling — IMPLEMENTED (phase13-v1)"
  residual: "Pre-LN — IMPLEMENTED (phase13-v1)"
  lambda_s: 0
  window_isolation: "INS-070 — DEFERRED to P2"
new_lessons: ["C-068", "C-069", "C-070"]
new_insights: ["INS-070"]
new_harness_rules: ["15b external audit mandatory", "15c pre-audit quality", "24b Spot only >2h", "25/25a two-layer error tracking"]
external_audits:
  plan_audit: "Codex 6/4→fixed, Gemini 6/1"
  code_audit: "Codex 7/8 (1 deferred=Mandate A), Gemini 7/7"
  gcp_audit: "Gemini 6/6 PASS"
```
