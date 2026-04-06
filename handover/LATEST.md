# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-06 — **STATUS: Phase 14 Step 0-2 全部完成，Step 3 受控 HPO 待启动，ETL v5 Sort 403/743**

## Current State
- **Phase 14 Step 0-2 全部完成**: Step 2 宏观旁路 A/B → 基线胜出(C-080)，6-dim 架构锁定
- **Phase 13 确认为唯一合法基线**: RankIC=+0.029, D9-D0=+7.00 BP
- **数据侧基线已建立**: Mean=6.93 BP, Std=189.60 BP, Skew=11.78, Kurtosis=2006, Data SNR=3.655%
- **ETL v5 Sort 进行中**: linux1 tmux `sort_v5`, 403/743 files, ~166s/file, ETA ~17h
- **Checkpoints**: Phase 13 `gs://omega-pure-data/checkpoints/phase13_v1/`, Step 2 Arm A `gs://omega-pure-data/checkpoints/phase14_step2_arm_a/`, Step 2 Arm B `gs://omega-pure-data/checkpoints/phase14_step2_arm_b/`

## Changes This Session
- **Phase 14 Step 2 A/B 实验完成**: macro bypass (log1p V_D + σ_D) vs baseline
  - Arm A (baseline): Job `2184063695481470976`, Best RankIC=+0.0122, D9-D0=+5.09 BP
  - Arm B (bypass): Job `5988585033818963968`, Best RankIC=+0.0064, D9-D0=+9.06 BP (但 RankIC 弱)
  - **结论**: 基线胜出 90%，SRL 信息压缩正确，macro bypass 无增量
- **代码变更**: `omega_epiplexity_plus_core.py` + `train.py` 添加 `--macro_bypass` flag（保留但不采纳）
- **Vertex AI YAML 修复**: `store_true` → `lambda` 解析（Gemini 审计发现）
- **Docker**: `phase14-vstep2` 镜像已构建推送（可复用于 Step 3）
- **外部审计**: Codex (GPT-5.4) 9/9 PASS + Gemini (2.5-pro) 14/14 PASS（代码审计 + YAML 审计 + Vertex AI 适配）
- **新教训**: C-080 (macro bypass A/B 无增量，SRL 遮蔽非问题)

## Key Decisions
- **Phase 14 协议锁定**: Step 0→1→2→3 绝对串行, hd≥256 严禁
- **macro_bypass=False 锁定**: Step 2 实证，SRL 反演已充分提取 V_D/σ_D (C-080)
- **lambda_s=0 永久锁定**: 6 Phase 实证 + kurtosis=2006 独立论据
- **审计底稿 7 疑点全部终结**: A(oracle test), B(修正), D(确认), F(Step 2 A/B), G(审计覆盖)
- **Step 3 部署决策**: T4 ON_DEMAND, pipe 模式, Vizier Bayesian HPO, ~20-30 trials

## Next Steps
### ETL v5 管线（进行中）
1. **[P0] 等待 Sort 完成**: linux1 tmux `sort_v5`, 403/743, ETA ~17h
2. **[P0] Sort 完成后启动 ETL v5**: `run_etl_v5_pipeline.py`
3. **[P0] ETL 完成后**: merge → QC → upload GCS (`wds_shards_v4`)

### Phase 14 Step 3 受控 HPO
4. **[Step 3] 准备 Vizier Study config**: hd=[64,128], window_t=[8,16,32], lr=[1e-4,1e-3]
5. **[Step 3] Docker `phase14-vstep2` 可直接复用**（代码已包含所有改动）
6. **[Step 3] 可先用 v3 shards 跑 HPO**（不必等 ETL v5）

## Warnings
- **omega-vm 无 PyTorch**: 推理/训练必须在 Vertex AI 或 linux1 上执行
- **Vertex AI pipe 推理禁止**: 推理必须用 FUSE (`/gcs/` 前缀)，训练 pipe 可用 (C-063)
- **Codex exec prompt 不可超 2KB 内联**: 写文件再 `$(cat file)` 注入 (C-079)
- **数据极端肥尾**: Kurtosis=2006, Range [-9035, 42671] BP
- **未提交的本地变更**: OMEGA_LESSONS.md (C-080), handover/LATEST.md, omega_epiplexity_plus_core.py, train.py, gcp/*.yaml, gcp/ 副本同步

## Remote Node Status
- **linux1**: Sort tmux `sort_v5` 403/743 files, ~166s/file, ETA ~17h, 31GB RSS, /omega_pool 2.0TB free
- **windows1**: 已清理 (旧进程/shards 已删除)

## Architect Insights (本次会话)
- 本次会话无新架构师指令。审计疑点 F (SRL 遮蔽) 已由 Step 2 A/B 实验终结 — SRL 反演充分提取宏观信息，无需旁路。
