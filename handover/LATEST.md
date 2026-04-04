# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-04 — **STATUS: Phase 13 Crucible PASS (IC Loss + AttentionPooling)，全链审计文档完成，待正式训练提交 (T4 Spot)**

## Current State
- **Phase 13 Crucible PASS**: IC_loss 0.036→-0.875 (2000 steps, 64 samples, T4)
- **Docker phase13-v2**: Build+Push 成功，Crucible 验证通过
- **全链审计文档**: `handover/PHASE13_FULL_CHAIN_AUDIT.md` (698 行, 13 个证据附录)
- **README 已更新**: 模型架构图 + 审计入口 + Phase 13 状态
- **Codex 审计**: 进程死亡 (1h33m 后挂起)，中间发现已人工补完
- **us-central1 L4 资源不足**: 今天全天紧张，Crucible 和正式训练改用 T4

## Changes This Session (7 commits)
- `248de67` chore: sync rule stats + enforcement log + session artifacts
- `795cec7` docs: Phase 12→13 full-chain audit — data→diagnosis→decision→status
- `288dc67` docs: append 13 evidence annexes (A-M) to Phase 13 full-chain audit
- `f671947` fix: add val sample count caveat to crucible comparison (5000 vs 64)
- `ea827f3` docs: add Volume Clock vs Per-date IC paradigm conflict to audit
- `783e779` docs: update README + handover/README for Phase 13 status

## Key Decisions
- **T4 替代 L4**: us-central1 L4 全天资源不足 (PENDING 45min+)，Crucible 和训练均用 T4。小模型 (24K params) 下差异仅几分钟，成本更低。已存入 memory。
- **Val 样本量 caveat**: Phase 13 Crucible val 仅 64 samples (--max_val_steps=1)，D9-D0=435BP/Std=333BP 无统计意义，审计文档已标注。
- **Volume Clock vs Per-date IC 范式矛盾**: ETL 实测确认 shard 无 date 字段。更深层问题是 per-date IC 可能违反 Volume Clock 设计原则，交审计师裁决。
- **Codex 审计未完成但关键发现已获取**: "Phase 12 diagnosis only partly grounded; Phase 13 PASS/GO claims lean on Vertex evidence not in source set"，人工补完了 13 个证据附录。

## Next Steps
1. **[P0] 创建 phase13_train_config.yaml**: T4 Spot 正式训练配置
2. **[P0] 补写 manifest**: Crucible PASS 记录 (safe_build_and_canary Step 4 被跳过)
3. **[P0] 提交正式训练**: `safe_submit.sh 13 2` (T4 Spot, ~10h, ~$2-3)
4. **[P1] 训练后 Post-Flight**: 全量推理 + 截面 IC + D9-D0 (~190万 val samples)
5. **[P2] Volume Clock vs Per-date IC 范式决策**: 需架构师裁决
6. **[P2] ETL V4 加 date 字段**: 如架构师决定需要 per-date IC

## Warnings
- **正式训练 config 未创建**: 需要 `phase13_train_config.yaml` (参考 phase11e_config.yaml，改 T4 + IC Loss 参数)
- **manifest 缺 Crucible 记录**: safe_submit.sh 会检查 manifest 最后一条是否 canary PASS
- **Crucible val 指标不可信**: 64 样本，仅 train pred_std 趋势可靠
- **3 个僵尸轮询进程已清理**: gcloud polling loop 因 stderr 混入 STATE 变量导致 case 不退出，已 kill
- **Codex audit job 进程死亡**: task-mnkfd7p0-61fp9f，companion 仍报 running，实际 PID 不存在

## Remote Node Status
- **linux1**: llama-server (Qwen3.5-9B) 占 10.4GB RAM + ~8.4GB VRAM, sweep_v4.py 在跑。RAM 38GB free, VRAM ~56GB free。SSH via linux1-back (反向隧道，linux1-lx ProxyJump 今天不通)
- windows1: 未检查

## Architect Insights (本次会话)
本次会话无新架构洞察。发现 Volume Clock vs Per-date IC 范式矛盾，已写入审计文档待架构师裁决。

## Machine-Readable State
```yaml
phase: "13_crucible_pass"
status: "pending_full_training"
blocking_gate: "phase13_train_config.yaml + manifest entry + safe_submit.sh"
docker: "omega-tib:phase13-v2 (CURRENT, Crucible PASS on T4)"
crucible:
  job_id: "5026336437654519808"
  gpu: "T4 (n1-standard-8)"
  result: "IC_loss=-0.875, RankIC=0.140 (64 val samples)"
  duration: "214s"
training_plan:
  gpu: "T4 Spot"
  estimated_time: "~10h"
  estimated_cost: "$2-3"
  config: "PENDING creation"
audit:
  doc: "handover/PHASE13_FULL_CHAIN_AUDIT.md"
  annexes: 13
  lines: 698
  verdict: "CONDITIONAL GO"
  open_questions:
    - "pred_std variance collapse risk"
    - "Volume Clock vs Per-date IC paradigm conflict"
    - "Phase 6 IC=0.066 baseline validity (C-062 torch.compile bug)"
harness:
  lessons: 71
  rules: 18
  incidents: 71
spec:
  status: "FINAL + 2 APPROXIMATION (batch-level IC, global D9-D0)"
new_commits: ["248de67", "795cec7", "288dc67", "f671947", "ea827f3", "783e779"]
ssh_route: "linux1-back (反向隧道), linux1-lx 今天不通"
```
