# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-02 — **STATUS: Phase 11 完成。Post-flight 揭示"有方差无信号"。需架构师方向性决策。**

## Current State
- **Phase 11d 训练完成**:
  - Config A (λ_s=1e-4, δ=200): SUCCEEDED 20/20
  - Config B (λ_s=1e-5, δ=200): E18 完成 (E19 crashed), 重提交 PENDING
  - Docker: omega-tib:phase11d-v1, Machine: g2-standard-8 + L4
- **Post-Flight 结论 (Config A best.pt, 全量 399 val shards, 1.99M samples)**:
  - pred_std: 17.33 BP (Phase 11c 5.64 → 3.1x 改善 ✅)
  - **但 IC: 0.0024 (Phase 11c 0.021 → 10x 恶化 ⛔)**
  - **D9-D0 spread: 2.91 BP (Phase 11c 8.90 → 更差 ⛔)**
  - **Rank IC: -0.026 (负 ⛔)**
  - z_sparsity: 0.12% (Phase 11c 0.44% → 更死 ⛔)
  - Daily IC mean: 0.009, 61% 天 IC>0 — 信号极弱但非零
  - **VERDICT: NOT TRADEABLE — 方差是噪声不是 Alpha**
- **Phase 11c 已完全废弃**: 216x 仪表盘幻觉 + 方差坍缩 (脑死亡)
- **Autoresearch branch** 在 linux1 上有另一个 agent 的实验 (Moment-Matched Spear, Dynamic Variance Tax)

## Changes This Session (~25 commits)
- `dd6aeae` fix: 全栈清理 TARGET_STD/MEAN + .squeeze()→.view(-1) (回滚 Gemini 后重做)
- `3565610` feat: Phase 11d — huber_delta=200 参数化 + lambda_s=1e-4 + 方差哨兵
- `de004f3` fix: 推理 P0 — GCS gs:// shard discovery + backtest fast_npy_decoder
- `092d65f` fix: phase7_inference.py --val_only (train/val 分离)
- `c47b684` fix: monitor 自动重提交 FAILED Spot jobs
- `a5714c1` fix: 方差哨兵阈值 CLI 化 (--sentinel_error/--sentinel_warn)
- `7cadccf` docs: Phase 11 全量数据汇总
- 归档: INS-052~056, C-049~057, 架构师指令 3 份, 烟测报告, post-flight plan

## Key Decisions
1. **Phase 11c 废弃**: 烟测揭露 216x 仪表盘幻觉 + pred_std=5.6 BP 脑死亡
2. **Phase 11d 双轨 A/B**: λ_s=1e-4 vs 1e-5, δ=200。结论: A≈B, λ_s 不是瓶颈
3. **Spot→On-Demand 切换**: L4 Spot 频繁抢占 (各 3+ 次), $8 换确定性
4. **Post-flight 残酷真相**: pred_std 上升但 IC 下降。模型学会了输出分散噪声，不是 Alpha
5. **小样本烟测不可信**: 5 shards/2 dates 的 IC=0.021 在 399 shards/75 dates 下崩塌到 0.002

## Next Steps — 需要架构师方向性决策
1. **核心问题**: 19.7K 模型 + SRL 物理捷径 + hd=64 容量是否是根本瓶颈？
   - 选项 A: 增大模型容量 (hd=128 或更大)
   - 选项 B: 修改 Loss 拓扑 (autoresearch branch 的 Moment-Matched Spear / Variance Bonus)
   - 选项 C: 重新审视目标定义 (clamp≥0 是否过于激进)
   - 选项 D: 回退到 Phase 10 的 Softmax 框架，但加防护 (INS-049)
2. **Config B 最后 E19**: PENDING, 可等可弃 (不影响结论)
3. **Autoresearch**: linux1 上 `autoresearch` branch 有实验性 Loss 变种, 未评估

## Warnings
- **Phase 11c 烟测 IC=0.021 是小样本假象**: 5 shards/2 dates 统计无效。以后烟测必须 ≥50 shards/≥20 dates
- **z_core 在 Phase 11d 更死 (0.12% vs 0.44%)**: δ=200 + λ_s 降低并未唤醒特征层，S_T 上升是少数神经元放大值
- **best.pt 被 Spot resume 多次重置**: 两个 config 的 best.pt 实际保存的 epoch 需从 checkpoint 元数据确认 (A=E17, B=E16)
- **另一个 agent 在 linux1 上创建了 feature/phase11e-moment-matched-spear 分支**: 含未审计的 Loss 变种代码
- **linux1 GPU 需要 `HSA_OVERRIDE_GFX_VERSION=11.0.0`**: 已存入 memory

## Remote Node Status
- linux1: 无活跃 Python 进程, /omega_pool 2.5T (7% used), GPU 推理已完成
- linux1 代码库: ~/omega_pure_v2_code (main branch, 需 git pull 更新)
- Vertex AI: Config B final job PENDING (4084263879859765248)

## Architect Insights (本次会话 — 5 条)
- INS-052: Train-Serve Skew 216x 幽灵 → architect/insights/INS-052_train_serve_skew_216x_demon.md
- INS-053: 净网回测协议 (superseded by INS-054/055)
- INS-054: 方差坍缩 — Huber δ=50 + λ_s=1e-3 致特征脑死亡 → architect/insights/INS-054_variance_collapse_brain_death.md
- INS-055: Phase 11d 双轨复苏 — λ_s↓ + δ↑ → architect/insights/INS-055_resuscitation_dual_track.md
- INS-056: 19.7K 模型禁止多卡 DDP → architect/insights/INS-056_no_multi_gpu_for_micro_model.md

## New Lessons (本次会话 — 9 条)
- C-049: Train-Serve Skew (推理脚本未同步训练范式切换)
- C-050: 死代码/幽灵 Bug (废弃变量必须 grep 全栈)
- C-051: 量纲剧变与方差坍缩 (换 Loss 必须重标定 λ_s/δ)
- C-052: 长训练前必须独立烟测 (不信仪表盘)
- C-053: Docker 构建 vs 代码修复时间点对齐
- C-054: 范式切换 = 全栈原子事件 (6 步 checklist)
- C-055: 阈值必须实测标定 (不拍脑袋)
- C-056: 监控不行动 = 没有监控
- C-057: 自动化脚本状态更新必须原子 (sed bug → 重复提交)

## Machine-Readable State
```yaml
phase: "11d_complete"
status: "postflight_done_awaiting_architect_decision"
config_a:
  state: SUCCEEDED
  epochs: 20/20
  best_pt: "gs://omega-pure-data/checkpoints/phase11d_A_v1/best.pt"
  best_pt_epoch: 17
  postflight:
    pred_std: 17.33
    ic_pearson: 0.0024
    ic_rank: -0.0262
    d9d0_spread: 2.91
    z_sparsity: 0.0012
    daily_ic_mean: 0.0092
    daily_ic_positive_pct: 61
    verdict: "NOT_TRADEABLE"
config_b:
  state: "E18_complete_E19_pending"
  best_pt: "gs://omega-pure-data/checkpoints/phase11d_B_v1/best.pt"
  best_pt_epoch: 16
docker: "omega-tib:phase11d-v1"
autoresearch_branch: "feature/phase11e-moment-matched-spear"
linux1_gpu: "HSA_OVERRIDE_GFX_VERSION=11.0.0"
full_data: "reports/phase11_complete_data_summary.md"
commits_this_session: 25
insights_this_session: [INS-052, INS-053, INS-054, INS-055, INS-056]
new_lessons: [C-049, C-050, C-051, C-052, C-053, C-054, C-055, C-056, C-057]
```
