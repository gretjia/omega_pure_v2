# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-07 — **STATUS: Phase 15 Step 1+2 完成 (MLP>Omega 🔴)。/deep-audit skill 上线。文档体系整理完毕。ETL v5 待确认。**

## Current State
- **Phase 15 Step 1+2 全部完成**: Omega IC_ema=0.0122 (🟠), MLP IC_ema=0.0159 (🔴)
  - MLP (5M params) 碾压 Omega-TIB (24.6K) 全指标
  - **203x 参数差距是混淆变量——需容量匹配 MLP 实验**
- **审计底稿 V2 更新**: 1072 行, 新增 §15-§19 (Phase 15 数据 + Omega Kernel 解剖 + 9 个未分离变量)
- **文档体系整理**: 所有 INDEX 更新, 旧文件标 SUPERSEDED, INS-019 标 invalidated, Phase 11 文件重组
- **/deep-audit skill 上线**: Codex 两轮审计通过 (V1→V2→V2.1)
- **ETL v5 Sort**: linux1, 状态待确认 (SSH 间歇不可达)

## Changes This Session (本次 handover 涵盖 2 个会话)
- **Phase 15 Step 1**: IC_ema=0.0122, Phase 13 IC=0.029 确认为选择偏差 (22b0d74)
- **Phase 15 Step 2 MLP**: IC_ema=0.0159, MLP > Omega (ace972e)
- **审计底稿 Phase 15 更新**: §15-§19 新增 304 行 (87073dd)
- **文档体系整理**: SUPERSEDED 标记 + INDEX 全更新 + Phase 11 文件重组 (c278fa6, 97ebb8d)
- **/deep-audit skill**: 迭代式深度审计, Codex 两轮审计 (584eec0)
- **Vertex AI 适配**: staging + SPOT + pd-ssd (96e74d9)

## Key Decisions
- **Phase 13 IC=0.029 是选择偏差**: Phase 15 实证确认, 真实均值 ~0.010
- **MLP > Omega 但容量混淆未解**: 🔴 结论待容量匹配实验
- **不延长 Step 1 到 E25**: EMA 阶段 E12→E14 斜率负, 已过收敛
- **/deep-audit 定位为咨询性 (advisory)**: 不替代 /dev-cycle 或 /axiom-audit 正式门禁
- **当前不建 MCP server**: Read/Grep 足以应对 35K 行文档

## Next Steps
### 最高优先级
1. **[P0] 容量匹配 MLP 实验**: ~25K-100K params MLP, 排除 203x 混淆变量
   - 如果匹配 MLP ≈ Omega → 拓扑无用 → 战略转向
   - 如果匹配 MLP << Omega → 拓扑有用但 Omega 需更多参数

### ETL v5
2. **检查 linux1 Sort 状态**: 用 linux1-back 路由
3. **Sort 完成后启动 ETL v5 Pipeline**

### 审计
4. **用 /deep-audit 审计 "Omega Kernel 是否需要重设计"**: 容量匹配实验后执行

## Warnings
- **MLP 对比不公平**: 5M vs 24.6K 参数。🔴 结论受容量差异影响
- **Cloud Logging 对某些 Job 无效**: 需从 GCS 读 train.log (`gcloud storage cat`)
- **linux1 SSH 间歇不可达**: 用 linux1-back (localhost:2224) 备用
- **Codex exec 长 prompt 卡死**: 必须用文件 I/O (memory/feedback_codex_long_prompt.md)
- **Docker tag 重复前缀**: build 脚本参数传 "15 1" 不是 "phase15 v1"
- **INS-019 已标 invalidated**: Phase 6 hd=64 证据已作废

## Remote Node Status
- **linux1**: ETL v5 Sort 状态待确认, SSH 间歇不可达, linux1-back 备用
- **windows1**: 已清理

## Architect Insights (本次会话)
- 本次会话无新架构师指令
- Phase 15 实验产出两个重大发现: (1) IC=0.029 选择偏差 (2) MLP>Omega 容量混淆
- /deep-audit skill 上线 — 项目首个强制迭代循环的审计工具
