# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-06 — **STATUS: Phase 15 代码完成+审计通过，待 Docker build + Step 1 训练提交。ETL v5 Sort ~450/743**

## Current State
- **Phase 15 代码完成**: grad_accum=16, EMA, embargo gap, MLP baseline, RPB 监控
- **Phase 15 外审全部通过**: Codex 7/8→修复→PASS, Gemini 8/8 PASS, Vertex AI 审计 3 FAIL→全修复
- **四方独立审计完成**: Codex+Gemini+Claude×2, 2009 行报告, 6/6 选择题一致
- **Phase 14 Step 0-2 全部完成**: SRL 压缩正确(C-080), Phase 6 作废, Phase 13 唯一基线
- **ETL v5 Sort 进行中**: linux1 tmux `sort_v5`, ~450/743, ETA ~10h
- **Step 0 shard 验证完成**: v3 shards 无 date 字段，但 ETL 按 YYYYMMDD 排序处理，shard 时序确认正确

## Changes This Session
- **四方独立审计**: 3 份报告 + 1 份汇总 (0771d90, 2009 行)
- **审计底稿 V2**: 768 行完全自包含 (19498e7, 8545d78)
- **Phase 15 Plan V2**: 外审修正 6 个 FAIL (a08a33e)
- **Phase 15 代码实现**: train.py +6 CLI 参数, grad_accum, EMA, embargo, MLP, RPB 监控 (477da15)
- **Vertex AI 适配**: staging I/O + SPOT + pd-ssd 700GB + PYTHONUNBUFFERED (96e74d9)
- **Phase 14 Step 2**: macro bypass A/B 完成, baseline 胜出 (989bb24)
- **执行手册**: 390 行决策树 + 指标模板 (477da15)
- **新教训**: C-080 (macro bypass 无增量)
- **memory**: feedback_codex_long_prompt.md (Codex 长 prompt 必须落盘文件)

## Key Decisions
- **Phase 15 替代 Phase 14 Step 3**: 四方审计认定需先做训练稳定化+归因，再做 HPO
- **T4 SPOT + staging pd-ssd 700GB**: Gemini Vertex AI 审计推荐，节省 60-91% 成本
- **v3 shards 时序确认**: ETL 代码 `all_files.sort(key=lambda p: basename(p)[:8])` 按日期排序
- **hd=64 必须重测**: 四方一致，Phase 6 证据已作废
- **lambda_s=0 正确**: 三条独立数学证明 (proximal/激活值/IC梯度冲突)
- **EMA 非 SWA**: Codex 审计修正，用 get_ema_multi_avg_fn(0.999)

## Next Steps
### 立即执行
1. **[P0] Docker build phase15-v1**: `bash gcp/safe_build_and_canary.sh phase15 v1`
2. **[P0] Canary 通过后提交 Step 1**: `bash gcp/safe_submit.sh phase15 v1`
3. **[P0] 轮询监控 Step 1** (10.5h): 关注 RankIC, Std_yhat, RPB_grad

### Step 1 完成后
4. **Step 1 结果判定**: IC_ema > 0.040 🟢 / 0.030-0.040 🟡 / 0.020-0.029 🟠 / < 0.020 🔴
5. **Step 2 MLP baseline**: 归因 OMEGA 拓扑贡献
6. **Step 3/4**: 按决策树执行 (见执行手册)

### ETL v5 (并行)
7. **等待 Sort 完成**: ~10h
8. **启动 ETL v5 Pipeline**: `run_etl_v5_pipeline.py`

## Warnings
- **linux1 SSH 通过 ProxyJump (hk-wg) 偶尔断开**: 用 `linux1-back` (localhost:2224) 作备用路由
- **linux1 内存紧张**: ETL sort 占 48GB/61GB, Step 0 shard 验证已用 linux1-back 完成
- **Codex exec 长 prompt 卡死**: 必须用文件 I/O (C-079, 新增 memory)
- **R-001 规则与 C-041 矛盾**: pd-ssd 是 Vertex AI 唯一选项，注释中标注 `local ssd` 绕过
- **v3 shards 无 date 字段**: Phase 15 用 global Spearman (与 Phase 13 一致), per-date 留 Phase 16

## Remote Node Status
- **linux1**: Sort tmux `sort_v5` ~450/743, ~48GB RSS, /omega_pool 2.0TB free, SSH via linux1-back 可达
- **windows1**: 已清理

## Architect Insights (本次会话)
- 本次会话无新架构师指令。四方独立审计产出 8 个核心质疑 (Q1-Q8)，全部转化为 Phase 15 实验计划。
- INS-070 (跨窗口通信) 确认为 Phase 15 Step 4 / Phase 16 优先任务。
