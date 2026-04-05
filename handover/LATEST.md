# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-05 — **STATUS: ETL v4 双节点并行运行中（linux1 tmux + windows1 Scheduled Task）**

## Current State
- **ETL v4 在 linux1 运行中**: tmux session `etl_v4`, 8 workers, 743 files, 22 shards 产出, ~440s/file (I/O 竞争较重)
- **ETL v4 在 windows1 运行中**: Scheduled Task `ETL_V4_WIN` (SYSTEM, PowerShell API 注册), 16 workers, 372 files, symbol discovery 中
- **Phase 13 训练**: Job 6005517512886714368 (T4 Spot), 状态需检查
- **Spec [FINAL]**: V3 Joint Arbitration 完成, Codex+Gemini 审计通过
- **Docker phase13-v2**: Crucible PASS (IC=0.88)

## Changes This Session (2 code commits + harness 大量更新)
- `1f416e9` feat: ETL v4 — add date field to shard meta.json for per-date IC eval
- `5bb0440` docs: architect-ingest V4 — Bag-of-Windows diagnosis + No-Retreat Decision Matrix (INS-074)
- **未提交**: OMEGA_LESSONS C-072~C-076 (5 条新教训), R-019~R-022 (4 条新规则), 3 个 incident traces, upload_v4_shards_to_gcs.py (merge 门禁修复)

## Key Decisions
- **ETL v4 代码改动极小**: date_buffer 平行于 bar_buffer/vwap_buffer, ~35 行改动, Codex 审计 PASS
- **linux1 8-worker vs 单 worker**: 440s/file vs 235s/file — 多 worker 因 I/O 竞争反而慢 (VIA_NEGATIVA #6 确认)
- **Windows Scheduled Task 正确模式**: PowerShell API + 落地 wrapper (CRLF!) + SYSTEM 账户, 不要用裸 schtasks /tr
- **SYSTEM 可以访问本地 USB SSD (D:)**: 不是网络映射盘就没问题

## Next Steps
1. **[P0] 等待 ETL v4 完成**: linux1 ~87h ETA (8 workers), windows1 待 workers 启动后看速度
2. **[P0] 对比双机速度后决策**: 如果 windows1 16-worker 速度合理, 可能只用 windows1; 否则 linux1 切单 worker (~50h)
3. **[P1] ETL 完成后**: merge shards → QC (date/shape/size) → upload GCS → per-date IC post-flight
4. **[P1] 检查 Phase 13 训练状态**: job 可能已完成或被 Spot 抢占
5. **[P2] 修复 linux1 BIOS**: 64/64 CPU/GPU 分配不合理 (ETL 不用 GPU), 改为 96/32 或 112/16 可大幅提升 ETL 速度

## Warnings
- **linux1 8-worker 比单 worker 慢 2x**: VIA_NEGATIVA #6 在 linux1 上确认复现, 如需最快完成应切单 worker
- **windows1 ETL 密码未解决**: schtasks /ru jiazi /rp 密码不匹配, 当前用 SYSTEM 账户绕过
- **windows1 discovery 较慢**: SYSTEM I/O 优先级可能低于用户会话
- **merge_worker_shards 已加门禁 (R-022)**: 必须验证所有 worker 完成才允许 merge
- **scp .cmd 文件必须转 CRLF**: 否则 cmd.exe 静默失败 (C-076)

## Remote Node Status
- **linux1**: 14 python processes (1 parent + 8 workers + monitoring), /omega_pool 2.4TB free, 33GB RAM available, tmux session `etl_v4`, llama-server 已停
- **windows1**: 2 python processes (parent + discovery subprocess), D: 1.1TB free, Scheduled Task `ETL_V4_WIN` (SYSTEM)

## Architect Insights (本次会话)
- **INS-074**: Bag-of-Windows 诊断 + No-Retreat Decision Matrix → `architect/directives/2026-04-04_...`

## New Lessons This Session
| # | 教训 | 规则 |
|---|---|---|
| C-072 | SSH 前台 = 定时炸弹 | R-019 |
| C-073 | Monitor 不可用 SSH 连通性判断 | R-020 |
| C-074 | 写规则后立刻违反 = 没规则 | R-021 |
| C-075 | merge 摧毁 checkpoint 续作能力 | R-022 |
| C-076 | Windows schtask 正确模式: PS API + CRLF wrapper | — |

## Machine-Readable State
```yaml
phase: "13_training_submitted + etl_v4_parallel"
etl_v4:
  linux1:
    method: "tmux session etl_v4"
    workers: 8
    files: 743
    speed: "~440s/file (I/O contention)"
    shards_produced: 22
    eta: "~87h"
  windows1:
    method: "Scheduled Task ETL_V4_WIN (SYSTEM, PowerShell API)"
    workers: 16
    files: 372
    status: "symbol discovery"
    shards_produced: 0
    eta: "TBD (workers not yet started)"
training:
  job_id: "projects/269018079180/locations/us-central1/customJobs/6005517512886714368"
  status: "check needed"
new_lessons: [C-072, C-073, C-074, C-075, C-076]
new_rules: [R-019, R-020, R-021, R-022]
new_commits: ["1f416e9", "5bb0440"]
harness:
  lessons: 76
  rules: 22
  incidents: 76
ssh_route: "linux1-lx (WireGuard), windows1-w1 (WireGuard)"
```
