# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-05 — **STATUS: Phase 13 训练完成 (JOB_STATE_SUCCEEDED)，ETL v4 双节点并行中，等待 Post-Flight**

## Current State
- **Phase 13 训练完成**: Job `6005517512886714368`, T4 Spot, 15 epochs, 10.5h, 零中断, JOB_STATE_SUCCEEDED
- **最佳 checkpoint**: E9 (Val Rank IC = +0.0292, D9-D0 = +7.00 BP)
- **全部 15 epochs Rank IC 为正** — Phase 12 的倒挂 (-0.0206) 彻底消除
- **训练已收敛，不需要继续**: E10-E14 平台期 (Rank IC ~0.017), 继续训练无提升空间
- **ETL v4 在 linux1 运行中**: tmux session `etl_v4`, 8 workers
- **ETL v4 在 windows1 运行中**: Scheduled Task `ETL_V4_WIN` (SYSTEM)
- **Checkpoints**: `gs://omega-pure-data/checkpoints/phase13_v1/`

## Changes This Session (本 session 为监控 + 分析，无新 commit)
- 监控训练进度，确认 Spot 零中断
- 调查 Std_yhat 异常值 — 确认是 `× 10000` 单位标注问题，非 bug
- 确认训练收敛，不需要继续训练

## Key Decisions
- **Std_yhat 不是 bug**: Val 代码 `preds.std() * 10000` 假设 raw output 是 decimal，但 IC Loss 下 output 是任意尺度 logits。实际 raw std 从 0.117→1.587，健康增长，无方差坍缩
- **不继续训练**: E10-E14 Rank IC 在 0.012-0.021 平台波动，Train IC_loss 稳定 -0.031，已收敛
- **结果按 INS-074 判决矩阵**: Rank IC 0.0292 超过 +0.015 "意外狂喜"阈值，但这是全局指标，需 per-date 截面评估确认

## Phase 13 完整训练结果

| Epoch | Val Rank IC | Val D9-D0 (BP) | Pearson IC |
|---|---|---|---|
| 0 | +0.0074 | -3.25 | -0.0041 |
| 1 | +0.0187 | +5.98 | +0.0083 |
| 2 | +0.0135 | +2.20 | +0.0034 |
| 3 | +0.0121 | +0.84 | +0.0023 |
| 4 | +0.0054 | +6.96 | +0.0099 |
| 5 | +0.0025 | +4.48 | +0.0061 |
| 6 | +0.0175 | +9.04 | +0.0110 |
| 7 | +0.0128 | +3.12 | +0.0056 |
| 8 | +0.0239 | +1.90 | +0.0050 |
| **9** | **+0.0292** | +7.00 | +0.0101 |
| 10 | +0.0209 | +4.81 | +0.0065 |
| 11 | +0.0124 | +9.35 | +0.0118 |
| 12 | +0.0178 | +4.60 | +0.0071 |
| 13 | +0.0172 | +7.76 | +0.0114 |
| 14 | +0.0180 | +8.49 | +0.0122 |

## Next Steps
1. **[P0] 等待 ETL v4 完成**: linux1 + windows1 双节点并行
2. **[P0] ETL v4 完成后**: merge shards → QC → upload GCS
3. **[P1] Post-Flight per-date 截面评估**: 用 E9 best.pt 对全量 val 做推理，按日历日切片计算 per-date Rank IC / D9-D0
4. **[P1] backtest_5a.py 截面化改造**: 加 per-date 分组逻辑
5. **[P2] 按 INS-074 判决矩阵解读结果**: 确认是否真正落入"意外狂喜"区间
6. **[P2] 规划 Phase 14**: Cross-Window Attention (INS-070)

## Warnings
- **全局 Rank IC ≠ per-date Rank IC**: 当前 0.0292 是全局指标（仍有波动率幻觉风险），必须等 ETL v4 + per-date 评估才能确认
- **Std_yhat 单位误导**: Val 日志中的 Std_yhat 是 `logit_std × 10000`，不是真实 BP。Post-Flight 报告中需标注
- **ETL v4 可能还需数十小时**: linux1 I/O 竞争严重 (8 workers 440s/file)
- **best.pt 选择**: 训练脚本按什么标准存 best？需确认是 Rank IC 还是 IC_loss

## Remote Node Status
- **linux1**: ETL v4 tmux session 运行中, 8 workers
- **windows1**: ETL v4 Scheduled Task 运行中

## Architect Insights (本次会话)
本次会话无新架构洞察。纯监控 + 分析。

## Machine-Readable State
```yaml
phase: "13_training_complete"
status: "waiting_etl_v4_for_postflight"
training:
  job_id: "projects/269018079180/locations/us-central1/customJobs/6005517512886714368"
  status: "JOB_STATE_SUCCEEDED"
  duration: "10.5h"
  spot_interruptions: 0
  epochs: 15
  best_epoch: 9
  best_rank_ic: 0.0292
  best_d9d0_bp: 7.00
  convergence: "plateau at E10-E14, Rank IC ~0.017"
  continue_training: "not recommended — converged"
  checkpoints: "gs://omega-pure-data/checkpoints/phase13_v1/"
etl_v4:
  linux1: "running (tmux etl_v4, 8 workers)"
  windows1: "running (Scheduled Task ETL_V4_WIN)"
  blocking: "Post-Flight evaluation"
interpretation:
  ins_074_matrix: "Rank IC 0.0292 > 0.015 threshold → 'Unexpected Triumph' (pending per-date confirmation)"
  caveat: "Global metric, per-date cross-sectional eval needed"
next_milestone: "ETL v4 complete → Post-Flight per-date evaluation"
```
