# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-04 — **STATUS: Phase 13 训练已提交 (T4 Spot, Job 6005517512886714368)，ETL v4 在 windows1 并行执行中**

## Current State
- **Phase 13 训练 RUNNING**: Job `6005517512886714368`, T4 Spot, pipe mode, 15 epochs × 5000 steps, ~10h
- **ETL v4 在 windows1 并行**: Session `add-date-field-shard-meta` (f5a109a7), 添加 date 字段到 shard
- **Spec [FINAL]**: V3 Joint Arbitration 完成, 3×[DRAFT]→[FINAL], Codex+Gemini 审计通过
- **Docker phase13-v2**: Crucible PASS (IC=0.88), 正式训练用同一镜像

## Changes This Session (5 commits)
- `42ec896` docs: handover — architect rulings complete, Phase 13 GREEN LIGHT
- `c896ce1` docs: architect-ingest V3 — joint arbitration rulings + spec DRAFT→FINAL (INS-071/072/073)
- `9a70c37` feat: Phase 13 train config (T4 Spot, pipe mode) + Crucible manifest entry
- `1f416e9` feat: ETL v4 — add date field to shard meta.json (代码改动，windows1 执行)
- `7d67ba3` feat: submit Phase 13 training — job 6005517512886714368

## Key Decisions
- **架构师 V3 联合裁决**: 5 项悬案全部裁决 — Q1 波动率伪影(撤回信号), Q2 双轨制, Q3 Crucible PASS, Q4 基线作废, Q5 窗口隔离 Phase 14
- **Spec 3×[DRAFT]→[FINAL]**: Pre-LN Residual + AttentionPooling + λ_s=0 升级为 FINAL (Crucible PASS + Architect GREEN LIGHT)
- **Phase 6 基线作废 (INS-072)**: success_criterion 改为 "TBD from Phase 13 Post-Flight"
- **双轨制范式 (INS-071)**: Volume Clock 训练 + Calendar 评估，ETL v4 补 date 字段
- **Pipe mode 替代 staging**: pd-standard 100GB + GCS streaming，避免 1300GB pd-ssd
- **pd-balanced 不合法**: Vertex AI 只接受 pd-ssd/pd-standard/hyperdisk-balanced，已修为 pd-standard
- **Gemini 审计 7/8 PASS**: seed 参数已有默认值 42 (non-issue)
- **Codex 审计**: 读完所有文件无 FAIL 信号，最终报告因超时未输出

## Next Steps
1. **[P0] 监控训练**: `gcloud ai custom-jobs stream-logs projects/269018079180/locations/us-central1/customJobs/6005517512886714368`
2. **[P0] 检查 ETL v4**: windows1 session `add-date-field-shard-meta` 完成后上传到 GCS
3. **[P1] Post-Flight**: 训练完成后用 v4 shards 做 per-date cross-sectional D9-D0 / Rank IC
4. **[P1] backtest_5a.py 截面化**: 加 per-date 分组逻辑（依赖 v4 shards date 字段）
5. **[P2] Codex 审计补完**: 如 Codex 后续返回 FAIL 需处理

## Warnings
- **Spot preemption 风险**: T4 Spot 可能被抢占，--resume + ckpt_every=1000 步保护
- **Pipe mode I/O**: 首次用 pipe mode 做全量训练，如果 GPU 饥饿可考虑切回 staging
- **ETL v4 输出目标**: 确认 windows1 上传到 `gs://omega-pure-data/wds_shards_v4/`
- **Phase 13 成功阈值未定**: "稳定单调正向 Rank IC" 无具体数字，训练后看数据定
- **RPB 梯度未直接验证**: 建议在训练日志中检查 per-param grad_norm

## Remote Node Status
- **linux1**: 上次检查: llama-server 占 10.4GB RAM + ~8.4GB VRAM, sweep_v4.py 在跑。SSH via linux1-back。
- **windows1**: ETL v4 session 运行中 (add-date-field-shard-meta)。128GB RAM, 8TB 外置 SSD。

## Architect Insights (本次会话)
- **INS-071**: Dual-Paradigm — Volume Clock 训练 + Calendar 评估 → `architect/insights/INS-071_dual_paradigm_volume_clock_train_calendar_eval.md`
- **INS-072**: Historical Baselines Invalidated — Phase 13 = Epoch 0 → `architect/insights/INS-072_historical_baselines_invalidated_epoch_zero.md`
- **INS-073**: Phase 13 Scope Downgrade — 日内 TWAP/VWAP 拆单摩擦 → `architect/insights/INS-073_phase13_scope_intraday_twap_vwap.md`

## Machine-Readable State
```yaml
phase: "13_training_submitted"
status: "training_running + etl_v4_parallel"
training:
  job_id: "projects/269018079180/locations/us-central1/customJobs/6005517512886714368"
  display_name: "phase13-train-v1"
  gpu: "T4 Spot (n1-standard-8)"
  io_mode: "pipe (streaming from GCS)"
  config: "gcp/phase13_train_config.yaml"
  epochs: 15
  steps_per_epoch: 5000
  lr: 3e-4
  estimated_time: "~10h"
  estimated_cost: "$2-3"
  monitor: "gcloud ai custom-jobs stream-logs projects/269018079180/locations/us-central1/customJobs/6005517512886714368"
docker: "omega-tib:phase13-v2"
etl_v4:
  node: "windows1"
  session: "add-date-field-shard-meta (f5a109a7)"
  status: "running"
  output_dest: "gs://omega-pure-data/wds_shards_v4/"
audit:
  gemini: "7/8 PASS (seed non-issue)"
  codex: "thorough review, no FAIL signals, final report timeout"
  spec_status: "FINAL (3x DRAFT upgraded)"
architect_rulings:
  q1: "Volatility artifact — signal claim withdrawn"
  q2: "Dual-track paradigm (INS-071)"
  q3: "Crucible PASS (IC=0.88)"
  q4: "Phase 6 invalidated — Epoch 0 (INS-072)"
  q5: "Window isolation Phase 14 (INS-073)"
new_insights: [INS-071, INS-072, INS-073]
new_commits: ["42ec896", "c896ce1", "9a70c37", "1f416e9", "7d67ba3"]
harness:
  lessons: 71
  rules: 18
  incidents: 71
ssh_route: "linux1-back (反向隧道), windows1-w1 (WireGuard)"
```
