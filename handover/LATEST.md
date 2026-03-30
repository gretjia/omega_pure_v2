# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-30 — **STATUS: Phase 9 暂停 — 非对称 Loss 泛化问题待解决**

## Current State
- **Phase 8 完成**: board_loss_cap Sharpe +34%, 执行层到达理论极限
- **Phase 9 进行中但暂停**: 7 个 Vertex AI job 迭代 (v1→v4)，全部停止
- **核心问题**: Leaky Asymmetric Pearson Loss 导致 val IC 持续下降
  - v1: dampening=0.05 + MSE anchor dampened → val IC=-0.001 (灾难性过拟合)
  - v3c: dampening=0.3 + anchor 对称 + anchor_weight=0.001 → val IC 0.006→0.004→0.003 (3 epoch 单调下降)
  - v4: anchor_weight=0.01 → staging 中被手动停止 (等待架构决策)
- **旗舰模型**: T29 (hd=64, 19.7K params) — Phase 6 对称版仍是最优 (OOS/IS=1.00)

## Changes This Session (14 commits)
- `738a462` Phase 7 comprehensive report (17-test diagnostic)
- `f5aa5a6` Architect ingest INS-024~029 (6 insights)
- `a94447d` Phase 8 simulate 重铸 + 12-run sweep
- `4c69d04` Phase 8 comprehensive report
- `77808ee` Architect ingest INS-030~031 (Phase 9 Go-Live)
- `0b2bf49` Phase 9 Leaky Asymmetric Pearson Loss
- `6157a3d` Gemini audit: vectorize masking, pin_memory
- `ea00751` GCS pipe mode + L4 job config
- `516e536` **FIX**: MSE anchor 恢复对称 (v1 过拟合根因)
- `f820d11` Fat Node + Local SSD + On-demand
- `ab3fa20` C-026: pipe 推理最优，训练需 staging
- `075621d` **FIX**: anchor_weight 0.001→0.01 (v3c val IC 下降)
- `b694cbf` Phase 9 evidence package (全版本数据)

## Key Decisions
1. **Phase 8 执行层到顶**: asymmetry 1.20 在 IC=0.028 下不可达 3.0
2. **Phase 9 非对称 Loss**: 方向正确但实现困难
   - MSE anchor 必须保持对称 (v1 教训)
   - dampening=0.05 太极端 → 0.3 仍不够
   - anchor_weight=0.001 (HPO 对称值) 对非对称 Loss 太弱
3. **Pipe vs Staging**: 推理用 pipe (单 pass)，训练用 staging (多 epoch) — C-026
4. **Vertex AI 快速迭代**: Custom Job 每次新 VM → 数据重复拉取 → 考虑 Workbench/Filestore

## Phase 9 训练数据汇总 (7 jobs)
| Version | dampening | anchor_wt | MSE sym? | Val IC | 结局 |
|---------|-----------|-----------|----------|--------|------|
| v1 | 0.05 | 0.001 | **NO** | -0.001 | 灾难性过拟合 |
| v2b | 0.3 | 0.001 | YES | — | Spot 抢占 |
| v3c | 0.3 | 0.001 | YES | 0.006→0.004→0.003 | val IC 单调下降 |
| v4 | 0.3 | **0.01** | YES | — | staging 中停止 |

## Next Steps (需要架构决策)
1. **选择迭代方式**:
   - A) pipe 模式 (0 min 启动, 慢 epoch) — 快速试参数
   - B) Workbench (持久 VM + GPU) — 最适合迭代
   - C) Filestore NFS (共享存储) — 生产级
2. **anchor_weight=0.01 是否足够?** 需要先跑出 val IC 数据
3. **是否需要更根本的改变?** dampening 可能不是正确的非对称化路径
4. **递交 PHASE9_EVIDENCE.md 给架构师审计**

## Warnings
- **Phase 6 T29 对称版仍是最强**: OOS/IS=1.00, 所有非对称尝试均未超越
- **anchor_weight 必须重新标定**: Phase 6 HPO 的 0.001 对非对称 Loss 无效 (C-027)
- **每次 Custom Job 重新拉 556GB**: 20 min 浪费 × N 次迭代
- **Std_yhat 膨胀是系统性的**: Pearson 尺度不变性 + 弱 anchor → 预测值爆炸

## Remote Node Status
本次会话未涉及远程节点（全部在 Vertex AI 上训练）

## Machine-Readable State
```yaml
phase: 9
status: "paused_val_ic_declining"
flagship_model: {trial: 29, ic: 0.0661, params: {hd: 64, wt: 32}}
phase9_attempts: 7
phase9_best_val_ic: 0.006
phase9_issue: "asymmetric loss causes val IC decline + Std_yhat explosion"
phase9_next: "anchor_weight=0.01 (v4) or architecture change"
commits_this_session: 14
insights_this_session: [INS-024, INS-025, INS-026, INS-027, INS-028, INS-029, INS-030, INS-031]
new_lessons: [C-024, C-025, C-026, C-027]
reports: [PHASE7_REPORT.md, PHASE8_REPORT.md, PHASE9_EVIDENCE.md]
```

## Architect Insights (本次会话 — 8 条)
- INS-024: 零过拟合认证 — OOS/IS=1.00
- INS-025: 对称 Loss 数学诅咒 — 模型退化为波动率雷达
- INS-026: 确信度过滤 — IC 翻倍至 0.054 (simulate 中无效)
- INS-027: 宏观气候雷达 — 实测有害
- INS-028: 压缩悖论 — 建仓=低熵，派发=高熵
- INS-029: Phase 9 两条路径 — 非对称目标截断 vs 双头阿修罗
- INS-030: Leaky Asymmetric Pearson Loss — dampening=0.3
- INS-031: Vanguard V3 Protocol — 锁死底盘换发引擎
