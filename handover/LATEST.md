# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-29 — **STATUS: Phase 7 代码完成，待部署到 linux1 执行**

## Current State
- **Phase 7 四脚本全部完成**: date_mapper / inference / simulate / report
- **Spec 变更已执行**: backtest 节重写 (INS-021/022/023)，公理验证 PASSED
- **旗舰模型**: T29 (hd=64, 19.7K params) — 压缩即智能的物理证明
- **时空修正 (INS-022)**: 20 bars = 0.4 天，非"数天到数周"。OMEGA 是 T+1 隔夜波段模型

## Phase 6 HPO 最终结果（不变）

Best: **T36 IC=+0.0667** | Flagship: **T29 IC=+0.0661 (hd=64, 单调性 8/9)**

| Trial | IC | Spread | Mono | Top 10% | Net Profit |
|-------|-----|--------|------|---------|-----------|
| T36 (hd=128) | +0.067 | 12.55 BP | 7/9 | 14.56 BP | +4.56 BP |
| T29 (hd=64) | +0.066 | 11.45 BP | 8/9 | 14.37 BP | +4.37 BP |

T29 选为旗舰：1/4 参数量达到几乎相同 IC + 更好单调性 = 更纯 Alpha

## Key Decisions This Session
1. **INS-011 废弃**: "严格日内"基于错误假设（秒级微观 Alpha），实际是 T+1 隔夜波段
2. **时空修正 (INS-022)**: 1 bar = 2% ADV → 50 bars/天 → 20 bars = 0.4 天
3. **策略重定位**: "捕捉主力长线建仓中的微观执行切片"（T+1 隔夜波段）
4. **T29 取代 T36**: 压缩即智能哲学 — 物理瓶颈更窄 = 更纯 Alpha
5. **25BP 成本锁定**: 印花税 5 + 佣金 6 + 滑点 7 + 冲击 7
6. **T+1 三铁律**: 物理锁 + 涨停买不进 + 跌停卖不出

## Changes This Session
- `architect/current_spec.yaml`: backtest 节重写 (overnight, T+1 lock, 25BP cost)
- `CLAUDE.md`: 添加核心论点 + 时间尺度修正
- `architect/directives/2026-03-29_*.md`: 两份指令归档
- `architect/insights/INS-019~023`: 5 个新洞察
- `tools/phase7_date_mapper.py`: shard→日期映射 (新建)
- `tools/phase7_inference.py`: T29 全量推理 + z_core hook (新建)
- `tools/phase7_simulate.py`: T+1 模拟 + 三铁律 (新建)
- `tools/phase7_report.py`: 结果报告 (新建)

## Next Steps: Phase 7 部署
1. **SCP T29 checkpoint**: `gsutil cp gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt`
2. **SCP 脚本到 linux1**: 4 个 phase7 脚本 + 依赖文件
3. **linux1 运行 date_mapper** (~10 min)
4. **linux1 运行 inference** (~2-3h, systemd-run)
5. **linux1 运行 simulate** (~30 min)
6. **SCP 结果回 omega-vm**, 运行 report

## Warnings
- **T29 checkpoint 路径**: `gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt`
- **linux1 GPU 不可用**: HIP kernel error, 必须 CPU 推理
- **meta.json 无日期**: 日期映射是近似值（基于 parquet 行数比例）
- **INS-022 时空修正是 VETO 级**: 所有"数天到数周"的表述已修正为"~0.4天 + T+1 强制隔夜"

## Remote Node Status
- 本次会话未涉及远程节点（代码编写阶段）
- linux1 上次状态: ONLINE, 32 cores, 64GB RAM, /omega_pool 7% used

## Machine-Readable State
```yaml
phase: 7
status: "code_complete_pending_deployment"
flagship_model: {trial: 29, ic: 0.0661, params: {hd: 64, wt: 32, lr: 3.2e-4, lambda_s: 1e-7, wu: 2, aw: 1e-3, bs: 128}}
flagship_checkpoint: "gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt"
backup_model: {trial: 36, ic: 0.0667, params: {hd: 128, wt: 32, lr: 3.0e-4, lambda_s: 1e-7, wu: 2, aw: 1e-4, bs: 128}}

time_scale_correction:
  bars_per_day: 50
  payoff_horizon_bars: 20
  payoff_horizon_days: 0.4
  macro_window_days: 3.2
  strategy_type: "T+1 overnight momentum"

backtest_spec:
  cost_bp: 25
  t_plus_1_lock: true
  limit_enforcement: true
  trailing_stop_pct: -10
  success: "asymmetry > 3.0 AND profit_factor > 1.5"

phase7_scripts:
  - tools/phase7_date_mapper.py
  - tools/phase7_inference.py
  - tools/phase7_simulate.py
  - tools/phase7_report.py

insights_this_session: [INS-019, INS-020, INS-021, INS-022, INS-023]
ins011_status: SUPERSEDED
```

## Architect Insights (本次会话)
- INS-019 隐式压缩胜利: hd=64 物理瓶颈 >> λ_s 显式惩罚
- INS-020 大统一因果链: SRL→Topology→Entropy→Epiplexity
- INS-021 INS-011 废弃: 日内→T+1 隔夜波段（时间尺度被 INS-022 修正）
- INS-022 时空修正: 20 bars = 0.4 天（VETO 级数学修正）
- INS-023 T+1 三铁律: 物理锁 + 涨停买不进 + 跌停卖不出
