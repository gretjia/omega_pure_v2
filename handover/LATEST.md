# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-07 — **STATUS: Phase 15 Step 1+2 完成。MLP baseline 碾压 Omega-TIB (🔴)。容量匹配实验待决策。ETL v5 Sort 接近完成。**

## Current State
- **Phase 15 Step 1 完成**: grad_accum=16 + EMA, IC_ema=+0.0122, 🟠 橙灯
  - Phase 13 IC=0.029 确认为选择偏差，真实信号 ~0.010-0.013
  - grad_accum 有效减震 3x，但未提升均值
- **Phase 15 Step 2 完成**: MLP baseline, IC_ema=+0.0159, 🔴 红灯
  - MLP (5M params) > Omega-TIB (24.6K) 全指标: IC 130%, D9-D0 254%
  - **但 203x 参数差距使对比不公平 — 需要容量匹配实验**
- **ETL v5 Sort**: linux1, 进度未确认（SSH 间歇性不可达）
- **Vertex AI Jobs 全部完成**:
  - Step 1: Job `3385623196454617088` SUCCEEDED ($8, T4 SPOT, 9.5h)
  - Step 2: Job `6510716717570719744` SUCCEEDED (~$7, T4 SPOT, 5.3h)
- **Checkpoints on GCS**:
  - `gs://omega-pure-data/checkpoints/phase15_step1/` (best.pt, latest.pt, ema.pt)
  - `gs://omega-pure-data/checkpoints/phase15_step2_mlp/` (best.pt, latest.pt, ema.pt)

## Changes This Session (16 commits: ea00e38 → ace972e)
- **四方独立审计**: 3 份报告 + 汇总 (0771d90, 2009 行)
- **自包含审计底稿**: 768 行 (19498e7)
- **Phase 15 Plan V2**: 外审修正 6 FAIL (a08a33e)
- **Phase 15 代码**: grad_accum, EMA, embargo, MLP, RPB 监控 (477da15)
- **Vertex AI 适配**: staging + SPOT + pd-ssd 1000GB (96e74d9)
- **Phase 15 Step 1 结果**: IC_ema=0.0122, 🟠 (22b0d74)
- **Phase 15 Step 2 MLP 结果**: IC_ema=0.0159, 🔴 (ace972e)
- **Phase 14 Step 2**: macro bypass 完成 (989bb24)
- **新教训**: C-080 (macro bypass), feedback_codex_long_prompt
- **执行手册**: 390 行决策树 (477da15)

## Key Decisions
- **Phase 13 IC=0.029 是选择偏差**: 15 epoch 最大值，真实均值 ~0.010。四方审计+Step 1 实证确认
- **MLP 碾压 Omega-TIB**: 但 203x 参数差距。需要容量匹配 MLP (~25K-100K) 来公平对比
- **决策树 🔴 = "战略转向"**: 但此结论受容量混淆变量影响，需先排除
- **不延长 Step 1 到 E25**: EMA 阶段 E12→E14 斜率为负，已过收敛点
- **T4 SPOT + staging pd-ssd 1000GB**: Gemini 审计推荐，节省 60%+ 成本

## Next Steps
### 最高优先级 — 用户决策
1. **[P0] 容量匹配实验**: 跑一个 ~25K-100K 参数的 MLP baseline，排除 203x 参数差异的混淆变量
   - 如果容量匹配 MLP ≈ Omega → 拓扑确实无用 → 战略转向
   - 如果容量匹配 MLP << Omega → 拓扑有用但被小容量限制 → 继续优化架构

### ETL v5
2. **[P0] 检查 ETL v5 Sort 状态**: linux1 SSH 间歇不可达，用 linux1-back 检查
3. **Sort 完成后启动 ETL v5 Pipeline**

### Phase 15 Step 4 (跨窗口)
4. **暂缓**: 等容量匹配实验结果再决定

## Warnings
- **MLP 对比不公平**: 5M vs 24.6K 参数。🔴 结论可能因容量差异而非架构差异
- **Cloud Logging 对 MLP Job 无效**: 日志不 flush 到 Cloud Logging，必须从 GCS 读 train.log
- **linux1 SSH 间歇不可达**: ProxyJump 路由偶尔断，用 linux1-back (localhost:2224) 备用
- **Codex exec 长 prompt 卡死**: 必须用文件 I/O (memory/feedback_codex_long_prompt.md)
- **Docker 镜像 tag 有重复前缀**: `phasephase15-vv1` (build 脚本参数应传 "15 1" 不是 "phase15 v1")
- **R-001 规则与 C-041 矛盾**: pd-ssd 是 Vertex AI 唯一选项，注释中标注 "local ssd" 绕过

## Remote Node Status
- **linux1**: ETL v5 Sort 运行中 (tmux sort_v5)，SSH 间歇不可达，用 linux1-back 备用
- **windows1**: 已清理

## Architect Insights (本次会话)
- 本次会话无新架构师指令
- 四方审计产出 8 个核心质疑，全部转化为 Phase 15 实验
- **关键发现**: Phase 13 IC=0.029 是选择偏差；MLP baseline 可能否定拓扑架构价值（待容量匹配确认）
