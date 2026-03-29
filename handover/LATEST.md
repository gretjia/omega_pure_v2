# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-29 — **STATUS: Phase 6 完成，准备模拟实盘 (Phase 7)**

## Current State
- **Phase 6 HPO 完成**: 70/70 trials, 0 failed, Job `4241649348649156608`
- **Phase 5a Top-3 回测完成**: 3/3 STRONG PASS
- **backtest_5a.py 修复**: `.numpy().copy()` 修复 PyTorch 悬挂视图内存泄漏 (Gemini 诊断)
- **Harness 升级+精简**: 压缩即智能, 人是机制 (净删 124 行)
- **GCS Shard 修复**: 200/200 完成

## Phase 6 HPO 最终结果

Best: **T36 IC=+0.0667** (+27.9% vs Vanguard V2)

锁定参数: `hd=128, wt=32, wu=2, bs=128, lr=3.0e-4, λ=1e-7, aw=1e-4, cg=1`

| Trial | IC | Spread | Mono | Top 10% | Net Profit |
|-------|-----|--------|------|---------|-----------|
| T36 (hd=128) | +0.067 | 12.55 BP | 7/9 | 14.56 BP | +4.56 BP |
| T29 (hd=64) | +0.066 | 11.45 BP | 8/9 | 14.37 BP | +4.37 BP |
| T55 (hd=64) | +0.066 | 9.14 BP | 5/9 | 12.35 BP | +2.35 BP |

收敛区域: wt=32, wu=2, bs=128, λ≈1e-7 (全 top-10 一致)

## Key Decisions This Session
1. **IC Loss STRONG PASS**: Huber Spread=-1.67→IC Loss Spread=+12.55 (方向翻转+盈利)
2. **A股成本修正**: 印花税 5BP 单边卖出 + 3BP 佣金 = ~8-10 BP round-trip
3. **7 维 HPO**: 新增 batch_size + anchor_weight, Gemini 双轮审计
4. **Harness 精简**: "人是机制" — 删掉过度工程化的 hooks/agents/rules
5. **backtest_5a.py OOM 修复**: `.numpy().copy()` 切断 PyTorch tensor 引用

## Next Steps: Phase 7 模拟实盘

### Gemini 量化审计要点 (已审计)
- **FAIL**: 111 天不够 → 用全量 3 年 walk-forward
- **FAIL**: 缺涨跌停处理 → 一字涨停买不进，跌停卖不出
- **FAIL**: 基准错 → CSI 500 改为中证 1000/全 A 等权
- **WARNING**: 成本 11BP → 20-25BP (含滑点+冲击)
- **WARNING**: 等权 → 信号加权+流动性过滤

### 推荐方案: 先做 C（全量推理不重训练）
1. 日期映射脚本 (parquet 文件名→date→shard 对齐)
2. backtest_5b_simulation.py (含涨跌停、滑点、T+1、信号加权)
3. linux1 CPU 全量推理 (9.9M samples, ~2h)
4. 模拟实盘 + 净值曲线
5. 预计总耗时 ~10h

### linux1 GPU 状态
- AMD Radeon 8060S: 64GB VRAM, ROCm 6.1, PyTorch HIP
- **暂不可用**: `HIP kernel errors` (gfx1201 kernel 兼容性)
- **CPU 推理可用**: 32 cores, 80K params 模型, ~20min/1.88M samples

## Machine-Readable State
```yaml
phase6_hpo_job: "4241649348649156608"
phase6_best_trial: {id: 36, ic: 0.0667, params: {hd: 128, wt: 32, lr: 3.0e-4, lambda_s: 1e-7, wu: 2, aw: 1e-4, bs: 128}}
phase6_backup_trial: {id: 29, ic: 0.0661, params: {hd: 64, wt: 32, lr: 3.2e-4, lambda_s: 1e-7, wu: 2, aw: 1e-3, bs: 128}}
docker: "omega-tib:v9-phase6"
best_checkpoint: "gs://omega-pure-data/checkpoints/phase6_icloss/trial_36/best.pt"
backup_checkpoint: "gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt"

data_range: {train: "2023-01-03 to 2025-06-10", val: "2025-06-11 to 2026-01-30", total_days: 552}
parquet_path_linux1: "/omega_pool/parquet_data/latest_base_l1/host=linux1/"
shard_path_linux1: "/omega_pool/wds_shards_v3_full/"

phase5a_jobs:
  t36: {job: "7934396533930196992", spread: 12.55, mono: "7/9", top10: 14.56}
  t29: {job: "3034796798699896832", spread: 11.45, mono: "8/9", top10: 14.37}
  t55: {job: "8893663254560112640", spread: 9.14, mono: "5/9", top10: 12.35}

gemini_sim_audit_findings:
  - "111天不够 → 全量3年walk-forward"
  - "缺涨跌停 → 一字板禁止交易"
  - "基准CSI500 → 中证1000/全A等权"
  - "成本11BP → 20-25BP含滑点"
  - "等权 → 信号加权+流动性"

linux1_gpu: {device: "Radeon 8060S", vram: "64GB", rocm: "6.1", status: "kernel_error_gfx1201"}
```

## Changes This Session (8 commits)
- `14bfbb4` Phase 6 HPO — 7-dim search + anchor_weight + Gemini dual audit
- `dc8f314` harness upgrade — auto-handover, external audit, experiment evaluator
- `ea47b92` Codex audit fixes — stop-guard robustness, evaluator thresholds
- `9bc0c50` compress harness — 压缩即智能, 人是机制
- `39b91be` handover update — Phase 6 HPO 52/70
- (earlier) `f3cbc88` INS-018 IC Loss, `9b0c137` architect directive

## Warnings
- **backtest_5a.py 已修复 OOM**: Docker v9-phase6 已重建包含 `.numpy().copy()` fix
- **linux1 GPU (ROCm) 暂不可用**: HIP kernel error on gfx1201, 用 CPU 推理代替
- **meta.json 缺日期**: ETL 只存了 sample_idx, 需要建 parquet 文件名→日期映射
- **current_spec.yaml 已更新为 IC Loss + Phase 6 HPO 搜索空间**

## Remote Node Status
- linux1: ONLINE, 32 cores, 64GB RAM (46GB free), /omega_pool 7% used
- windows1: 未涉及

## Architect Insights
- INS-018 横截面相对论: Phase 6 HPO 完成, T36 IC=+0.0667, STRONG PASS confirmed
