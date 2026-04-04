# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-04 — **STATUS: Phase 13 架构师裁决完成，GREEN LIGHT 正式训练。ETL v4 (加 date 字段) 可并行在 windows1 执行**

## Current State
- **Phase 13 Crucible PASS**: IC_loss 0.036→-0.875 (2000 steps, 64 samples, T4)
- **架构师递归审计裁决完成**: 5 个阻塞性疑问全部裁决（详见下方 Key Decisions）
- **Docker phase13-v2**: Build+Push 成功，Crucible 验证通过
- **全链审计文档**: `handover/PHASE13_FULL_CHAIN_AUDIT.md` (698 行, 13 个证据附录)
- **ETL v4 可行性确认**: windows1 本地有 2.2TB 原始数据，raw parquet 含 date 字段，代码改动 ~40 行

## Changes This Session (0 commits, 纯审计对话)
- 无代码变更。本次会话为架构师审计报告的逐条证据交叉审计 + 5 项裁决对齐。

## Key Decisions
- **架构师裁决 Q1 — -28.4σ Rank IC 是波动率伪影**: 架构师撤回"底层信号已确认"定性。Leaky Blinding + MSE 制造的高波动选择 → 次日均值回归。Phase 13 Post-Flight 是真正验证。
- **架构师裁决 Q2 — 双轨制范式**: 训练用 batch-level IC（Volume Clock），评估用 per-date cross-sectional IC（Calendar）。**但 ETL v3 无 date 字段 → Post-Flight per-date 评估需 ETL v4**。
- **架构师裁决 Q3 — Crucible PASS 确认**: "Loss→0.0" 是 MSE 思维惯性，IC Loss 下界 -1.0，IC=0.88 对 24.4K 模型已是极限。正式放行。
- **架构师裁决 Q4 — Phase 6 基线彻底作废**: C-062 torch.compile bug 可能注入随机权重。"13 倍退化"定量结论作废（IC>MSE 定性仍成立）。Phase 13 = Epoch 0，无历史包袱。
- **架构师裁决 Q5 — 窗口隔离维持 Phase 14**: 控制变量法，Phase 13 已改 5 个变量。Phase 13 目标降级为"日内 TWAP/VWAP 拆单摩擦"（0.64 天感受野足够）。
- **ETL v4 并行方案**: windows1 闲置 + 数据在本地 + date 字段已存在于 raw parquet。可与 Phase 13 训练同步执行，Post-Flight 时用 v4 shards 做严格 per-date 评估。

## Next Steps
1. **[P0] 创建 phase13_train_config.yaml**: T4 Spot 正式训练配置
2. **[P0] 补写 manifest**: Crucible PASS 记录
3. **[P0] 提交正式训练**: `safe_submit.sh 13 2` (T4 Spot, ~10h, ~$2-3)
4. **[P0] ETL v4 在 windows1 并行**: 改 ETL 加 date 字段 (~40 行) → 重处理 2.2TB → 上传 GCS（单独 session）
5. **[P1] 训练后 Post-Flight**: 用 v4 shards 做严格 per-date cross-sectional D9-D0 / Rank IC
6. **[P2] backtest_5a.py 截面化改造**: 加 per-date 分组逻辑（依赖 v4 shards 的 date 字段）

## Warnings
- **正式训练 config 未创建**: 需要 `phase13_train_config.yaml`
- **manifest 缺 Crucible 记录**: safe_submit.sh 会检查
- **Phase 13 成功阈值未定**: Phase 6 基线作废后，原 "Rank IC > 0.03" 标准失去锚点。架构师说"稳定单调正向截面 Rank IC"但无具体数字。先跑数据再定。
- **Post-Flight per-date 评估依赖 ETL v4**: 如 v4 未完成，Post-Flight 只能用 global 近似指标
- **RPB 梯度恢复未直接验证**: Phase 13 Crucible 无逐参数 grad_norm 日志。IC=0.88 间接证明，建议正式训练加 grad_norm 监控。

## Remote Node Status
- **linux1**: 上次检查: llama-server 占 10.4GB RAM + ~8.4GB VRAM, sweep_v4.py 在跑。SSH via linux1-back。
- **windows1**: 闲置，可用于 ETL v4。128GB RAM, 8TB 外置 SSD (1.14TB free), 2.2TB 原始数据在本地。

## Architect Insights (本次会话)
- **架构师递归审计报告**: 5 条设想被推翻（Leaky Blinding / MSE / Global TopK / Mean Pooling / L1），2 条被证实（微型模型 / IC Loss 容忍度），3 组重构方案。已通过逐条证据交叉审计验证 7/8 论断。
- **双轨制范式确立**: Volume Clock 训练 + Calendar 评估，解决了 Q2 范式冲突。
- **Phase 13 正式定位**: "日内 TWAP/VWAP 拆单摩擦捕获"（0.64 天感受野），多日建仓模式留待 Phase 14 跨窗口注意力。

## Machine-Readable State
```yaml
phase: "13_architect_greenlight"
status: "pending_full_training + ETL_v4_parallel"
blocking_gate: "phase13_train_config.yaml + manifest entry + safe_submit.sh"
docker: "omega-tib:phase13-v2 (CURRENT, Crucible PASS on T4)"
crucible:
  job_id: "5026336437654519808"
  gpu: "T4 (n1-standard-8)"
  result: "IC_loss=-0.875, RankIC=0.140 (64 val samples)"
  duration: "214s"
  verdict: "PASS (architect confirmed: IC=0.88 sufficient for 24.4K model)"
training_plan:
  gpu: "T4 Spot"
  estimated_time: "~10h"
  estimated_cost: "$2-3"
  config: "PENDING creation"
etl_v4:
  node: "windows1"
  status: "READY (feasibility confirmed)"
  changes: "~40 lines (add date.npy to shards)"
  raw_data: "2.2TB on local 8TB SSD"
  reprocess_time: "1-2h multi-worker, 8-12h single"
  output_dest: "gs://omega-pure-data/wds_shards_v4/"
architect_rulings:
  q1_rank_ic: "Volatility artifact — signal claim withdrawn"
  q2_paradigm: "Dual-track: Volume Clock train, Calendar eval"
  q3_crucible: "PASS — IC=0.88 sufficient"
  q4_baseline: "Phase 6 invalidated — Phase 13 = Epoch 0"
  q5_windows: "Deferred to Phase 14 — control variable method"
audit:
  doc: "handover/PHASE13_FULL_CHAIN_AUDIT.md"
  annexes: 13
  verdict: "GREEN LIGHT (upgraded from CONDITIONAL GO)"
  resolved_questions:
    - "Q1: -28.4σ Rank IC attribution → volatility artifact"
    - "Q2: Volume Clock vs Per-date → dual-track paradigm"
    - "Q3: Crucible -0.875 vs 0.0 → PASS (MSE thinking corrected)"
    - "Q4: Phase 6 baseline → fully invalidated"
    - "Q5: Window isolation → Phase 14"
  remaining:
    - "pred_std variance collapse risk (monitor during training)"
    - "RPB gradient revival (indirect evidence only, add grad_norm logging)"
    - "Phase 13 success threshold TBD (no historical anchor)"
harness:
  lessons: 71
  rules: 18
  incidents: 71
spec:
  status: "FINAL + 2 APPROXIMATION (batch-level IC, global D9-D0) — ETL v4 resolves eval approximation"
ssh_route: "linux1-back (反向隧道), windows1-w1 (WireGuard)"
```
