# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-04 — **STATUS: Phase 13 Mandate A COMPLETE — IC Loss 替换 MSE, Rank IC 为主指标。待 Docker rebuild + Crucible overfit test 验证。**

## Current State
- **Phase 13 Mandate A DONE**: IC Loss 替换 Unbounded Spear MSE, Rank IC 替换 D9-D0 为 best.pt/Vizier 主指标
- **Phase 13 Mandate B DONE**: AttentionPooling + Pre-LN Residual (上一 session)
- **Mandate B Crucible PASS**: 瞬时 loss≈0.15, pred_std 非零 (Phase 13 架构验证)
- **Mandate A Crucible 待做**: 需 Docker rebuild (phase13-v2) + 新 Crucible test
- **gcp/ 已同步**: 3 文件 + crucible config 已更新
- **Spec [FINAL] + 2 APPROXIMATION**: batch-level IC + global Spearman (date 不在 shard 中)

## Changes This Session (3 commits)
- `df2db3a` feat: Phase 13 Mandate A — IC Loss + Cross-Sectional Evaluation (5 files)
- `d8d402a` merge: Phase 13 Mandate A (feature branch → main)
- `1c11bbe` sync: gcp/ mirror + crucible config update

## Key Decisions
- **Batch-level IC (非 per-date)**: ETL shard meta.json 无日期字段。Codex 审计标记 FAIL (spec 要求 per-date)，用户接受近似。Spec 标注 [APPROXIMATION]。
- **sqrt(var+eps) 非 clamp(std,eps)**: Gemini 二轮审计发现 torch.std() backward 在 var=0 时 NaN。clamp 只修 forward，sqrt(var+eps) forward+backward 都安全。
- **Rank IC 替换 D9-D0**: Spec primary_metric = Cross-Sectional Rank IC (Vizier MAXIMIZE)
- **Pipeline Gate 豁免**: Strategy B Step 1 未执行，但外部审计已裁定所有历史基准作废 (strict=False + GMP + Leaky Blinding)

## Next Steps
1. **[P0] Docker rebuild**: `bash gcp/safe_build_and_canary.sh 13 2` — 必须先构建 phase13-v2 镜像
2. **[P0] Crucible overfit test**: IC Loss 应收敛到 loss→-1.0 (IC=1.0), pred_std 非零
3. **[P1] Phase 13 全面训练**: Vizier HPO, Rank IC 为主指标, A100 Spot
4. **[P2] ETL V4 加 date**: 升级 batch-level IC → per-date IC (消除 APPROXIMATION)
5. **[P2] Mandate B.3 — Window Isolation**: 跨窗注意力 (INS-070, deferred)

## Warnings
- **Docker 镜像过期**: phase13-v1 仅含 Mandate B，不含 IC Loss。必须 rebuild phase13-v2
- **APPROXIMATION 标注**: Spec 中 loss_function 和 primary_metric 两处标注 batch-level 近似
- **Stale CLI params**: train.py 保留 leaky_factor/static_mean_bp/mse_scale_factor 参数 (YAML backward-compat)，但不在活跃代码路径中
- **Early stopping 阈值**: --early_stop_fvu 现在对比 Rank IC (非 D9-D0 BP)，阈值含义改变

## Remote Node Status
本次会话未涉及远程节点。所有工作在 omega-vm 控制节点完成。

## Architect Insights (本次会话)
本次会话无新架构洞察。实施已有 INS-066 (IC Loss) + INS-067 (Rank IC 主指标)。

## Machine-Readable State
```yaml
phase: "13_mandate_a_done"
status: "ic_loss_implemented_pending_crucible"
blocking_gate: "Docker rebuild phase13-v2 + Crucible overfit test"
harness:
  version: "v3_living"
  rules_active: 17
  incidents_total: 70
  hooks: 10
  skills: 9
docker: "omega-tib:phase13-v1 (STALE — needs rebuild to phase13-v2)"
crucible:
  mandate_b:
    job_id: "5402703665888755712"
    instantaneous_loss_final: 0.15
    verdict: "PASS"
  mandate_a:
    status: "PENDING — Docker rebuild required"
    expected_loss: "-1.0 (IC=1.0 perfect overfit)"
spec:
  status: "FINAL + 2 APPROXIMATION annotations"
  loss: "Pearson IC Loss — IMPLEMENTED (sqrt(var+eps) guard)"
  pooling: "AttentionPooling — IMPLEMENTED (phase13-v1)"
  residual: "Pre-LN — IMPLEMENTED (phase13-v1)"
  lambda_s: 0
  approximations:
    - "batch-level IC (no date in shard, pending ETL V4)"
    - "global Spearman Rank IC (pending per-date average)"
  window_isolation: "INS-070 — DEFERRED to P2"
external_audits:
  plan_audit: "Codex FAIL (per-date, user accepted batch-level), Gemini CONDITIONAL PASS"
  code_audit: "Codex 7/8 PASS (stale CLI params intentional), Gemini 2-round PASS (sqrt fix)"
new_commits: ["df2db3a", "d8d402a", "1c11bbe"]
```
