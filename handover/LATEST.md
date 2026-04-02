# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-02 — **STATUS: Phase 11d 双轨复苏训练中 (g2+L4 Spot), A=E10/20, B=E6/20 (Spot 频繁抢占)**

## Current State
- **Phase 11d 双轨训练中** — 修复 Phase 11c 方差坍缩 (INS-054/055)
  - **Config A** (λ_s=1e-4, δ=200): Job 1109662714260619264, E10/20, RUNNING
  - **Config B** (λ_s=1e-5, δ=200): Job 2854869142517841920, E6/20, PENDING (Spot 抢占恢复中)
  - Docker: omega-tib:phase11d-v1 (canary PASSED)
  - Machine: g2-standard-8 + L4 (Spot), pd-ssd 1300GB staging
  - Output: gs://omega-pure-data/checkpoints/phase11d_A_v1/ 和 phase11d_B_v1/
  - 监控: cron 30min (自动重提交 FAILED jobs) + remote schedule 1h (CCR, 未确认可用)

- **Phase 11c 废弃**: 烟测揭露方差坍缩 — pred_std=5.6 BP (模型输出常数 ~30 BP), z_core 脑死亡 (0.44%), 仪表盘 Std_yhat 被旧 Docker 代码 *216x 放大为幻觉

- **训练曲线 (Phase 11d 半程)**:

  Config A (λ_s=1e-4):
  | Epoch | Val Loss | PfRet | Std_yhat | S_T |
  |-------|----------|-------|----------|-----|
  | E0 | 5283 | 7.15 | 8.22 | 176 |
  | E2 | 5227 | 7.27 | 16.17 | 224 |
  | E5 | 5219 | 7.34★ | 15.09 | 229 |
  | E8 | 5287 | 7.30 | 19.93★ | 228 |
  | E10 | 5228 | 7.32 | 14.79 | 225 |

  Config B (λ_s=1e-5):
  | Epoch | Val Loss | PfRet | Std_yhat | S_T |
  |-------|----------|-------|----------|-----|
  | E0 | 5329 | 7.07 | 8.72 | 179 |
  | E4 | 5253 | 7.41 | 22.52★ | 235 |
  | E5 | 5219 | 7.42★ | 18.34 | 233 |
  | E6 | 5216★ | 7.25 | 17.01 | 229 |

  两者 Std_yhat 在 13-23 BP 振荡，未稳定突破 30 BP。B 略优 (更高峰值、更好 PfRet)。
  Phase 11c 对比: pred_std 从 1.3-5.7 BP → 13-23 BP (3-4x 改善), S_T 从 116-157 → 225-235 (z_core 复苏)

## Changes This Session (18 commits)
- `dd6aeae` fix: 全栈清理 TARGET_STD/MEAN + .squeeze()→.view(-1) + 重复 main() (回滚 Gemini 错误修复后重做)
- `3565610` feat: Phase 11d — huber_delta=200 参数化 + lambda_s=1e-4 + 方差坍缩哨兵
- `de004f3` fix: 推理 P0 — GCS gs:// shard discovery + backtest fast_npy_decoder
- `092d65f` fix: phase7_inference.py 增加 --val_only (train/val 分离)
- `9fcdbb7` chore: Config A/B 升级 L4 + 6 workers
- `6f71ba9` docs: C-052/053/054 范式切换原子 checklist
- `c47b684` fix: monitor 自动重提交 FAILED Spot jobs
- `4376fc0` docs: Phase 11d post-flight plan (7 步)
- 归档: INS-052~056, C-049~056, 3 份架构师指令, 烟测报告

## Key Decisions
1. **Phase 11c 全面废弃**: 烟测证实 20 epoch 全是脑死亡模型 + 216x 仪表盘幻觉 (C-051)
2. **δ=50→200**: 释放 97.6% 样本的 MSE 梯度，肥尾不再被削峰 (INS-055)
3. **λ_s=1e-3→1e-4/1e-5**: 解除 z_core 结构税 (INS-054)
4. **19.7K 模型禁止多卡 DDP**: Scale-Up only (INS-056)
5. **方差哨兵阈值 10/30 BP 是粗估**: 训练完成后必须用数据重标定 (C-055)
6. **范式切换 = 全栈原子事件**: 创建 tools/paradigm_shift_checklist.md (C-054)

## Next Steps (Phase 11d 完成后)
1. **执行 Post-Flight Plan** (`architect/directives/2026-04-01_phase11d_post_flight_plan.md`)
   - Step 0: 选 winner config (A vs B)
   - Step 2: Val-only 推理 (--val_only)
   - Step 3: **实测标定方差哨兵阈值** (C-055, 最高优先)
   - Step 4-5: 回测 + 交易模拟
   - Step 6: Epiplexity 公理验证 (十分位 Alpha 分解)
2. 如 D9-D0 spread > 25 BP → Phase 12 (Epiplexity Gating 或实盘准备)
3. 如 spread < 25 BP → HPO 精调或架构重构

## Warnings
- **Config B Spot 频繁抢占**: us-central1 L4 紧张，已被抢占 2 次，cron 自动重提交 (max 3)
- **Std_yhat 未突破 30 BP**: 在 13-23 BP 振荡，复苏方向对但幅度待观察
- **方差哨兵阈值不可靠**: 10/30 BP 是粗估，Post-flight Step 3 必须重标定
- **Docker phase11d-v1 不含推理 P0 修复**: 推理修复在 de004f3 (Docker 构建后)，post-flight 推理需在本地或重建 Docker

## Remote Node Status
- linux1: omega_pure_v2_code repo 已克隆 (~/omega_pure_v2_code), /omega_pool 有全量 1992 shards, 烟测已验证可用
- Vertex AI: 2 jobs active (A=RUNNING E10, B=PENDING resume)

## Architect Insights (本次会话 — 5 条)
- INS-052: Train-Serve Skew 216x 幽灵 → architect/insights/INS-052_train_serve_skew_216x_demon.md
- INS-053: 净网回测协议 (superseded by INS-054/055)
- INS-054: 方差坍缩 — Huber δ=50 + λ_s=1e-3 致特征脑死亡 → architect/insights/INS-054_variance_collapse_brain_death.md
- INS-055: Phase 11d 双轨复苏 — λ_s↓ + δ↑ → architect/insights/INS-055_resuscitation_dual_track.md
- INS-056: 19.7K 模型禁止多卡 DDP → architect/insights/INS-056_no_multi_gpu_for_micro_model.md

## New Lessons (本次会话 — 8 条)
- C-049: Train-Serve Skew (推理脚本未同步训练范式切换)
- C-050: 死代码/幽灵 Bug (废弃变量必须 grep 全栈)
- C-051: 量纲剧变与方差坍缩 (换 Loss 必须重标定 λ_s/δ)
- C-052: 长训练前必须独立烟测 (不信仪表盘)
- C-053: Docker 构建 vs 代码修复时间点对齐
- C-054: 范式切换 = 全栈原子事件 (6 步 checklist)
- C-055: 阈值必须实测标定 (不拍脑袋)
- C-056: 监控不行动 = 没有监控

## Machine-Readable State
```yaml
phase: 11d
status: "training_in_progress"
config_a:
  job_id: 1109662714260619264
  state: RUNNING
  epoch: 10/20
  best_pfret: 7.34
  best_std_yhat: 19.93
  params: {lambda_s: 1e-4, huber_delta: 200}
config_b:
  job_id: 2854869142517841920
  state: PENDING (Spot resume)
  epoch: 6/20
  best_pfret: 7.42
  best_std_yhat: 22.52
  params: {lambda_s: 1e-5, huber_delta: 200}
docker: "omega-tib:phase11d-v1"
machine: "g2-standard-8 + L4 Spot"
monitor: "cron 30min (auto-resubmit) + schedule 1h (CCR)"
post_flight_plan: "architect/directives/2026-04-01_phase11d_post_flight_plan.md"
commits_this_session: 18
insights_this_session: [INS-052, INS-053, INS-054, INS-055, INS-056]
new_lessons: [C-049, C-050, C-051, C-052, C-053, C-054, C-055, C-056]
```
