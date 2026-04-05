# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-05 — **STATUS: Phase 14 Step 0+1 完成 (BRANCH A)，Phase 13 确认为唯一基线，ETL v5 Sort 253/743**

## Current State
- **Phase 14 Step 0+1 完成**: Phase 6 T29 复测结果 BRANCH A（RankIC=0.0023, pred_std=790 BP → 信号死亡）
- **Phase 13 确认为唯一合法基线**: RankIC=+0.029, D9-D0=+7.00 BP
- **数据侧基线已建立**: Mean=6.93 BP, Std=189.60 BP, Skew=11.78, Kurtosis=2006, Data SNR=3.655%
- **ETL v5 Sort 运行中**: linux1 tmux `sort_v5`, 253/743 files, ~186s/file, ETA ~24h
- **Checkpoints**: Phase 13 `gs://omega-pure-data/checkpoints/phase13_v1/`, Phase 6 T29 `gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/`

## Changes This Session
- **全生命周期审计底稿**: `reports/audits_and_insights/2026-04-05_omega_tib_audit_workpapers.md` (5-Agent 编制, f536c27)
- **Session 总结**: `handover/2026-04-05_SESSION_AUDIT_SUMMARY.md` (9d3e6a2)
- **Phase 14 Oracle Test 脚本**: `tools/phase6_oracle_test.py` (c70fe69→99f2698, 6 次迭代修复)
- **"2.4% SNR" 证伪**: 来自 Phase 12 失败模型输出，非数据固有属性。数据真实 SNR=3.655%
- **Phase 6 T29 窗口发现**: HPO 实际用 window=(32,10)，非代码默认 (4,4) (4b16509)
- **新教训**: C-077 (伪常数传播), C-078 (三方审计元模式), C-079 (codex exec 长 prompt 卡死)
- **Codex 外审**: GPT-5.4 交叉验证 session summary, 4/5 CONFIRMED (c70fe69)
- **Vertex AI Jobs**: V1-V6 迭代 (CPU→T4, pipe→FUSE, +num_workers, +skip_step0), 最终 V6 成功

## Key Decisions
- **Phase 14 协议锁定**: Step 0→1→2→3 绝对串行, hd≥256 严禁
- **lambda_s=0 永久锁定**: 6 Phase 实证 + kurtosis=2006 独立论据，L1 在此分布下是"尾部信号绞肉机"
- **Phase 6 T29 BRANCH A**: 模型方差爆炸(790 BP), Phase 13 架构修复(Pre-LN+AttentionPooling)确认必要
- **审计底稿 7 疑点**: A(Phase 6 时间线)已用 oracle test 终结, B(窗口断裂)已修正(T29 实为 32,10), D(post_proj_norm)已确认, F(SRL 遮蔽)待 Step 2 实验, G(FRT)已被本次审计覆盖

## Next Steps
### ETL v5 管线（进行中）
1. **[P0] 等待 Sort 完成**: linux1 tmux `sort_v5`, 253/743, ETA ~24h
2. **[P0] Sort 完成后启动 ETL v5**: `run_etl_v5_pipeline.py`
3. **[P0] ETL 完成后**: merge → QC → upload GCS (`wds_shards_v4`)

### Phase 14 协议（Step 0+1 已完成）
4. **[Step 2] 宏观旁路 A/B 实验**: 将 σ_D + V_D 拼入特征流形，对照 Phase 13 基线。成功标准=统计显著正向增量（不要求跨 25 BP）
5. **[Step 3] 受控 HPO**: hd=[64, 128]，严禁 hd≥256

## Warnings
- **omega-vm 无 PyTorch**: 推理/训练必须在 Vertex AI 或 linux1 上执行
- **Vertex AI pipe 模式极慢**: 推理必须用 FUSE (`/gcs/` 前缀) + num_workers≥4
- **Codex exec prompt 不可超 2KB 内联**: 写文件再 `$(cat file)` 注入 (C-079)
- **Phase 6 HPO 实际参数**: T29 用 window=(32,10) 非 (4,4)，审计底稿疑点 B 已部分修正
- **数据极端肥尾**: Kurtosis=2006, Range [-9035, 42671] BP, 可能含数据质量问题（极低流动性股票跨周/月的 volume-clock 窗口）
- **未提交的本地变更**: tools/omega_etl_v3_topo_forge.py (ETL v5 性能重构), run_etl_v5_pipeline.py, tools/sort_parquet_by_symbol.py

## Remote Node Status
- **linux1**: Sort tmux `sort_v5` 253/743 files, ~186s/file, ETA ~24h, 45GB RSS, /omega_pool 2.1TB free
- **windows1**: 已清理 (旧进程/shards 已删除)

## Architect Insights (本次会话)
- 本次会话无新架构师指令。审计发现的架构问题（SRL 遮蔽、FRT 审计盲区）记录为疑点，待 Step 2 实验验证。
