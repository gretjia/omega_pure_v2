# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-29 — **STATUS: Phase 7 代码完成 + 三轮审计通过，待部署 linux1**

## Current State
- **Phase 7 四脚本完成 + 三轮审计通过**: Codex (代码对齐) + Gemini (性能/OOM) + omega_axioms (公理)
- **Spec 变更已执行**: backtest 节重写，公理验证 PASSED
- **旗舰模型**: T29 (hd=64, 19.7K params) — 压缩即智能
- **时空修正 (INS-022)**: 20 bars = 0.4 天。OMEGA 是 T+1 隔夜波段模型

## Phase 6 HPO 最终结果

Best: **T36 IC=+0.0667** | Flagship: **T29 IC=+0.0661 (hd=64, 单调性 8/9)**

| Trial | IC | Spread | Mono | Top 10% | Net Profit |
|-------|-----|--------|------|---------|-----------|
| T36 (hd=128) | +0.067 | 12.55 BP | 7/9 | 14.56 BP | +4.56 BP |
| T29 (hd=64) | +0.066 | 11.45 BP | 8/9 | 14.37 BP | +4.37 BP |

## Changes This Session (3 commits)
- `7f8e795` feat: Phase 7 — spec重写 + 5 insights (INS-019~023) + 4 脚本 + CLAUDE.md
- `6186f9c` fix: Codex 审计修复 — F1(入场target结算) F2(涨跌停) F3(张量10ch) F4(分段写入) W3(M3链路)
- `afbc726` perf: Gemini 审计修复 — mini-batch 512 + 16 threads

## Key Decisions
1. **INS-011 废弃**: "严格日内"→ T+1 隔夜波段 (INS-021)
2. **时空修正**: 20 bars = 0.4 天，非"数天到数周" (INS-022 VETO)
3. **T29 旗舰**: hd=64 物理瓶颈 = 更纯 Alpha (INS-019)
4. **25BP 成本**: 印花税5+佣金6+滑点7+冲击7
5. **T+1 三铁律**: 物理锁+涨停买不进+跌停卖不出 (INS-023)
6. **F1 修复**: simulate 用入场 target 结算 (Codex audit)
7. **性能优化**: batch 5000→512 + threads 4→16 (Gemini audit)

## Next Steps: Phase 7 部署
1. SCP T29 checkpoint: `gsutil cp gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt`
2. SCP 脚本到 linux1: `scp tools/phase7_*.py omega_epiplexity_plus_core.py omega_webdataset_loader.py linux1-lx:/omega_pool/phase7/`
3. linux1 运行 date_mapper (~10 sec)
4. linux1 运行 inference (~2h, systemd-run --slice=heavy-workload.slice)
5. linux1 运行 simulate (~5 min)
6. SCP 结果回 omega-vm, 运行 report

## Warnings
- **T29 checkpoint**: `gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt`
- **linux1 GPU 不可用**: HIP kernel error, CPU-only
- **涨跌停检测是 best-effort**: 基于 spread-lock 启发式，无昨收数据
- **日期映射是近似值**: 基于 parquet 行数比例，±1-2 天误差

## Audit Summary (三轮)
| 审计 | 工具 | 结果 |
|------|------|------|
| 代码对齐 | Codex (gpt-5.4) | 4 FAIL → 全部修复 |
| 性能/OOM | Gemini | 1 WARNING → 已修复, 0 OOM risk |
| 公理验证 | omega_axioms.py | ALL PASSED |

## Remote Node Status
- 本次会话未涉及远程节点（代码编写+审计阶段）
- linux1 上次状态: ONLINE, 32 cores, 64GB RAM, /omega_pool 7% used

## Machine-Readable State
```yaml
phase: 7
status: "code_complete_audited_pending_deployment"
flagship_model: {trial: 29, ic: 0.0661, params: {hd: 64, wt: 32, lr: 3.2e-4, lambda_s: 1e-7, wu: 2, aw: 1e-3, bs: 128}}
flagship_checkpoint: "gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt"

time_scale: {bars_per_day: 50, payoff_bars: 20, payoff_days: 0.4, strategy: "T+1 overnight momentum"}
backtest: {cost_bp: 25, t1_lock: true, limit_enforcement: true, trailing_stop: -10%, success: "asymmetry>3.0 AND pf>1.5"}

scripts: [phase7_date_mapper.py, phase7_inference.py, phase7_simulate.py, phase7_report.py]
audits: {codex: "4F fixed", gemini_perf: "1W fixed", axioms: "ALL PASS"}
commits: ["7f8e795", "6186f9c", "afbc726"]
insights: [INS-019, INS-020, INS-021, INS-022, INS-023]
```

## Architect Insights (本次会话)
- INS-019 隐式压缩胜利: hd=64 >> λ_s
- INS-020 大统一因果链: SRL→Topology→Entropy→Epiplexity
- INS-021 INS-011 废弃: 日内→T+1 隔夜波段
- INS-022 时空修正: 20 bars = 0.4 天 (VETO)
- INS-023 T+1 三铁律: 物理锁+涨停+跌停
