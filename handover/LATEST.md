# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-31 — **STATUS: Phase 10 训练完成 — Softmax Portfolio Loss 收敛, 待回测**

## Current State
- **Phase 10 完成**: Softmax Portfolio Loss 替代 Pearson IC Loss, 20 epoch 训练成功收敛
- **Best Model**: Epoch 16, Val PfRet=0.210, Std_yhat=5055 BP
  - Checkpoint: `gs://omega-pure-data/checkpoints/phase10_softmax_v5/best.pt`
  - 最后 4 epoch (16-19) 稳定在 Val PfRet ≈ 0.207, Std ≈ 4900 BP
- **Phase 9 废弃**: 非对称 Pearson Loss 被判死刑 (INS-032/035), 7 jobs 全败
- **旗舰对比待定**: Phase 6 T29 (IC=0.066, OOS/IS=1.00) vs Phase 10 (PfRet=0.210, 不同 metric)

## Changes This Session (2 commits + 未提交变更)
- `02a2fbe` feat: Phase 10 Vanguard V5 — Softmax Portfolio Loss replaces Pearson IC Loss
- `bbad361` perf: GCS I/O optimizations — FUSE v2 file-cache + fast_npy_decoder + Spot
- 未提交: CLAUDE.md 热修复纪律 (#21-22), OMEGA_LESSONS C-028~C-034, safe_build/submit 修复, manifest 更新, phase10 YAML 修正, phase7_inference.py 除零修复

## Key Decisions
1. **Pearson IC Loss → Softmax Portfolio Loss**: 架构师裁决 + Gemini 3 轮审计通过 (INS-033)
   - Softmax "赢家通吃"权重 × batch Z-scored targets
   - L2 mean-shift penalty: `mean(pred)^2` (Gemini 修正)
   - 彻底删除 dampening / MSE anchor / Pearson
2. **On-demand 而非 Spot**: 用户选择, 总费用 ~$9.6
3. **pd-ssd staging 而非 FUSE v2**: 因 pd-balanced 配置漂移事故 (C-030), 回退到 Phase 9 staging 方案
4. **z_sparsity per-sample 导出**: INS-034, `tools/phase7_inference.py` 已实现

## Phase 10 训练数据汇总 (20 epochs, Job 8443272505497485312)
| Epoch | Val PfRet | Val Std (BP) | 阶段 |
|-------|-----------|-------------|------|
| 0-1 | 0.011→0.033 | 435→518 | 冷启动+warmup |
| 2-3 | 0.166→0.168 | 2518→3208 | 快速学习 Peak 1 |
| 4-8 | 0.083→0.074 | 4456→5382 | 崩塌+震荡 |
| 9-10 | 0.186→0.189 | 6372→5801 | 二次学习 Peak 2 |
| 11-15 | 0.175→0.122 | 3055→4851 | 高方差震荡 |
| **16-19** | **0.210→0.207** | **5055→4918** | **收敛 (Best=Epoch 16)** |

## Next Steps (需要架构决策)

### Step 1: 全量推理 (导出 predictions + z_sparsity)
```bash
# 脚本: tools/phase7_inference.py
# 需先下载 best.pt 到本地或用 GCS 路径
python3 tools/phase7_inference.py \
  --checkpoint <best.pt 路径> \
  --shard_dir /omega_pool/wds_shards_v3_full/ \
  --date_map /omega_pool/phase7/shard_date_map.json \
  --output phase7_results/phase10_predictions.parquet \
  --hidden_dim 64 --window_size_t 32 --batch_size 512
```

### Step 2: 回测模拟 (Phase 8 simulate)
```bash
# 脚本: tools/phase7_simulate.py
python3 tools/phase7_simulate.py \
  --predictions phase7_results/phase10_predictions.parquet \
  --cost_bp 25 \
  --output_dir phase7_results/phase10_results/
```

### Step 3: 与 Phase 6 T29 对比
- Phase 6 predictions: `phase7_results/predictions.parquet`
- Phase 10 predictions: `phase7_results/phase10_predictions.parquet`
- 回测器输出 Sharpe / asymmetry ratio / profit factor → apple-to-apple 对比

### Step 4: 架构改进 (Phase 10.1)
- Std_yhat=5055 BP 偏高, L2 mean-shift 对 Softmax 无效 (mean≈0 天然)
- 修正: `l2_weight * pred.var()` 替代 `l2_weight * pred.mean()**2`, weight 提到 1e-2
- 递交架构师: Phase 10 证据包 + Std_yhat 问题报告

## Warnings
- **Std_yhat=5055 BP 是隐患**: PfRet 和 Std 正相关, 模型可能在"赌大的"而非真正学排序
- **OOS/IS=1.38 异常**: Val > Train, 可能是 batch Z-score 的统计噪音, 回测前不可信任
- **费用超支**: 预估 $3 实际 $9.6, 根因: 配置漂移 (C-030) + ETA 未实测校准 (C-033/034)
- **未提交变更**: CLAUDE.md, OMEGA_LESSONS, safe scripts, manifest 等需 commit

## Remote Node Status
本次会话未涉及远程节点（全部在 Vertex AI 上训练）

## Architect Insights (本次会话 — 4 条)
- INS-032: Pearson 尺度免疫漏洞 — 非对称 dampening 诱导 Reward Hacking
- INS-033: Softmax Portfolio Loss — 从统计相关性到交易逻辑的范式跃迁
- INS-034: z_sparsity 作为交易扳机 — 高压缩率 = 主力控盘铁证
- INS-035: Phase 9 非对称 Pearson Loss 终极验尸 — 7 jobs 全败

## New Lessons (本次会话 — 7 条)
- C-028: pd-ssd 吞吐与容量挂钩, 训练用 Local SSD 或 FUSE v2
- C-029: Nearline 检索费陷阱 ($111/20epoch)
- C-030: 热修复配置漂移 — 只改出错字段, 禁止重写
- C-031: Vertex AI diskType/diskSize API 约束
- C-032: checkpoint_interval=0 除零崩溃
- C-033: ETA 必须用 Epoch 0 实测校准
- C-034: batch_size 变更必须重新量化 ETA

## Machine-Readable State
```yaml
phase: 10
status: "training_complete_pending_backtest"
best_model:
  epoch: 16
  val_pf_ret: 0.2103
  val_std_yhat_bp: 5055
  checkpoint: "gs://omega-pure-data/checkpoints/phase10_softmax_v5/best.pt"
  params: {hd: 64, wt: 32, temperature: 1.0, l2_weight: 1e-4, lambda_s: 1e-7}
phase10_job: 8443272505497485312
phase10_cost_usd: 9.6
phase10_duration_hours: 12.5
commits_this_session: 2
uncommitted_changes: true
insights_this_session: [INS-032, INS-033, INS-034, INS-035]
new_lessons: [C-028, C-029, C-030, C-031, C-032, C-033, C-034]
next_step_scripts:
  inference: "tools/phase7_inference.py"
  simulate: "tools/phase7_simulate.py"
  backtest_config: "gcp/phase5a_backtest.yaml"
```
