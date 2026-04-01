# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-01 — **STATUS: Phase 11b Reforged Spear 训练中 (n1+T4 Spot), 智能 cron 监控**

## Current State
- **Phase 11b 训练中**: Job 1035686747310129152 (n1-standard-8 + T4 Spot, pd-ssd 1300GB staging)
  - Docker: omega-tib:phase11-v2 (canary PASSED)
  - Loss: compute_spear_loss (Detached Straitjacket + T=0.5 + lambda_s=2e-5 + FP32)
  - Output: gs://omega-pure-data/checkpoints/phase11b_spear_v2/
  - 智能 cron 监控: Dense 5min → Cruise 30min, NaN 自动报警, Spot 自动重提交
  - 预估 ETA: staging ~20min + 训练 ~8h
- **Phase 10 P0 完成**: Asymmetry=1.30, Sharpe=2.55, 但确认 Casino Exploit (Logit Inflation 22.9x)
- **Phase 11a FAILED**: NaN 崩溃 @ Epoch 5 (勾股漂移 INS-046, S_T: 4->203K->Inf)
- **lesson-enforcer.sh hook 已部署**: PreToolUse 拦截 pd-ssd YAML 等已知错误

## Changes This Session (2 commits)
- `d3f5352` feat: Phase 11b Spear Protocol + P0 evidence + reports consolidation
- `7f7d942` docs: doc reorganization + Path Finder navigation + audit index
- 未提交: OMEGA_LESSONS C-044 (resume+旧checkpoint假完成)

## Key Decisions
1. **P0 Epiplexity Gating FAILED**: 所有配置恶化表现 (Ann.Ret +44%->-34%). 根因: Corr(z_sparsity,|pred|)=-0.34, 过滤高熵=过滤利润
2. **Phase 11a->11b**: Z-score 仿射不变性导致勾股漂移. 修复: detach(std) + T 0.1->0.5 + lambda_s 1e-7->2e-5
3. **n1+T4 而非 g2+L4**: T4 配额新批准, $0.21/h Spot vs $1.08/h, 且 n1 支持 Local SSD (虽然 Vertex AI 容器无法 mount)
4. **Vertex AI 无法 mount NVMe**: 所有机型容器 permission denied (C-041 更新). pd-ssd staging 是唯一方案

## Next Steps (Phase 11b 完成后)
1. 检查训练曲线: S_T 是否稳定? Val PfRet 趋势? NaN?
2. 全量推理 (phase7_inference.py + Phase 11b best.pt)
3. P0 Crucible 回测 (phase7_simulate.py, 25BP cost)
4. 报告 S7 Asymmetry Ratio — 是否突破 1.30 死锁

## Warnings
- **Phase 11b 是 Spot**: 可能被抢占, cron 会自动重提交 (checkpoint resume)
- **C-044**: output_dir 必须用新路径 (phase11b_spear_v2), 旧 checkpoint 会导致假完成
- **T4 配额**: Preemptible T4 仅批准 4 个, On-demand 被拒. 并行训练受限
- **trades.json 未提交**: 太大 (100K+ 行), 在 .gitignore 中

## Remote Node Status
- linux1: 无活跃任务 (Phase 10 推理已完成/取消)
- Vertex AI: Job 1035686747310129152 RUNNING

## Architect Insights (本次会话 — 13 条)
- INS-036: Softmax 尺度失控 (被 INS-040 取代)
- INS-037: P0 物理熔炉协议 (已执行)
- INS-038: 双头阿修罗 V2 (推迟 Phase 12)
- INS-039: Epiplexity Gating (FAILED)
- INS-040: 方差之枷 (被 INS-047 修正)
- INS-041: 压缩即智能实证定律 (已生效)
- INS-042: 非对称目标遮蔽 clamp(min=0) (已实现)
- INS-043: 建仓 Epiplexity Loss (已实现)
- INS-044: Spear-First 策略 (已生效)
- INS-045: P0 终极判决 Casino Exploit (T=0.1 被修正)
- INS-046: 勾股漂移 (已生效)
- INS-047: Detached Straitjacket (已实现)
- INS-048: lambda_s 动态引力重构 1e-7->2e-5 (已实现)

## New Lessons (本次会话 — 10 条)
- C-035~C-039: CPU 推理性能 (threads=1 最优, 多进程无加速, window_size 不匹配, z_sparsity final flush bug, GPU 硬编码)
- C-040~C-041: Vertex AI 磁盘 (pd-ssd 重复犯错, NVMe 容器不可用)
- C-042~C-044: 训练稳定性 (勾股漂移, lambda_s 量纲匹配, resume 假完成)

## Machine-Readable State
```yaml
phase: 11b
status: "training_in_progress"
job_id: 1035686747310129152
docker: "omega-tib:phase11-v2"
machine: "n1-standard-8 + T4 Spot"
output_dir: "gs://omega-pure-data/checkpoints/phase11b_spear_v2"
loss: "compute_spear_loss (detached straitjacket)"
params: {hd: 64, wt: 32, ws: 4, temperature: 0.5, lambda_s: 2e-5, batch_size: 256}
monitor: "smart_cron (dense 5min -> cruise 30min)"
commits_this_session: 2
insights_this_session: [INS-036 through INS-048]
new_lessons: [C-035 through C-044]
```
