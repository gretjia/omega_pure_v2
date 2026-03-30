# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-30 — **STATUS: Phase 8 完成，Phase 9 (非对称 Loss) 待启动**

## Current State
- **Phase 8 完成**: 模拟器物理法则重铸 + 12-run parameter sweep + /dev-cycle 全流程
- **最佳配置**: board_loss_cap only (Ann +6.31%, Sharpe 0.662)
- **核心结论**: Asymmetry 1.20 在 IC=0.028 下数学不可达，Phase 9 是唯一突破路径
- **旗舰模型**: T29 (hd=64, 19.7K params) — 零过拟合 (OOS/IS=1.00)

## Phase 7 Diagnostic Summary (17 Tests)
- Daily CS-IC=0.028 (真实信号), Global IC=-0.007 (时间漂移假象)
- Daily CS monotonicity 5.26/9 (修正值，原报 2/9 是 global pooling bug)
- L/S spread +18.08 BP (修正值，原报 -5.92)
- Long alpha +13.3 BP (3x > short alpha +4.7 BP)
- 尾部捕获上下对称 (2.01x vs 1.84x) → 模型是波动率雷达，非方向性
- IS IC=0.0277 ≈ OOS IC=0.0276 → 零过拟合

## Changes This Session (3 commits)
- `738a462` docs: Phase 7 comprehensive report + trailing stop fix
- `f5aa5a6` docs: architect ingest — INS-024~029 (6 new insights)
- `a94447d` feat: Phase 8 — 模拟器重铸 + 12-run sweep

## Key Decisions
1. **Board loss cap 是唯一有效的执行层优化**: Sharpe 0.49→0.66 (+34%)
2. **Conviction filter 无效**: max_positions=50 已是绑定约束，conviction 过滤多余
3. **Regime filter 有害**: trailing NAV drawdown 减仓 = 错过反弹 (均值回复效应)
4. **Asymmetry 3.0 数学不可达**: IC=0.028, target_std=198 → 理论上限 ~1.2
5. **Phase 9 方向确定**: 非对称 Loss (路径 A: target masking, 路径 B: 双头阿修罗)

## Phase 8 Sweep Results
| Config | Ann.Ret | Sharpe | MaxDD | Asym |
|--------|---------|--------|-------|------|
| Phase 7 原始 | +4.58% | 0.493 | -26.5% | 1.201 |
| **+board_cap (最佳)** | **+6.31%** | **0.662** | **-25.1%** | 1.213 |
| +conv20+cap | +4.15% | 0.447 | -25.4% | 1.213 |
| +regime+cap | -2.69% | -0.177 | -29.2% | 1.204 |

## Next Steps
1. **Phase 9 立项**: 非对称 Loss 重训 — 路径 A (target masking, 1 行代码) 先试
2. **Phase 8.1 (可选)**: z_sparsity 输出到 inference (需重跑 Vertex AI job)
3. **Phase 7 Report**: 已归档到 `phase7_results/PHASE7_REPORT.md`

## Warnings
- **不要再调 simulate 参数**: Phase 8 sweep 已证明执行层到达理论极限
- **不要排除 688**: 科创板 IC=0.039 是最强信号，排除后 Sharpe 虽升但根因不对
- **Regime filter 是有害的**: trailing DD 减仓错过反弹，已在 spec 中标注

## Remote Node Status
- linux1-lx: SSH 超时 (Tailscale 掉线)。上次在线: 32 cores, 61GB RAM
- Vertex AI: 无活跃 job

## Machine-Readable State
```yaml
phase: 8
status: "complete_phase9_pending"
flagship_model: {trial: 29, ic: 0.0661, params: {hd: 64, wt: 32}}
best_simulate_config: {board_loss_cap: true, conviction: 0, regime: off}
best_metrics: {ann_ret: 6.31, sharpe: 0.662, max_dd: -25.1, asymmetry: 1.213}
phase9_direction: "asymmetric_loss (INS-029: path_A target_masking first)"
commits: ["738a462", "f5aa5a6", "a94447d"]
insights: [INS-024, INS-025, INS-026, INS-027, INS-028, INS-029]
```

## Architect Insights (本次会话)
- INS-024: 零过拟合认证 — OOS/IS=1.00
- INS-025: 对称 Loss 数学诅咒 — 模型退化为波动率雷达
- INS-026: 确信度过滤 — IC 翻倍至 0.054 (但 simulate 中无效，因 max_positions 绑定)
- INS-027: 宏观气候雷达 — 实测有害 (trailing DD 错过反弹)
- INS-028: 压缩悖论 — 建仓=低熵，派发=高熵 (Phase 9 封印)
- INS-029: Phase 9 两条路径 — 非对称目标截断 vs 双头阿修罗
