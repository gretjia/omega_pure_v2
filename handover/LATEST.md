# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-28 — **STATUS: Phase 6 IC Loss HPO 运行中 (70 trials A100 Spot, Job 4241649348649156608)**

## Current State
- **Vanguard V2 (IC Loss) 完成**: 20 epochs, Best Val IC=+0.0522, FVU=0.9478
- **Phase 5a STRONG PASS**: Spread=+11.07 BP, 9/9 单调性, Corr=0.0154
  - Top 10% return = 13.32 BP (扣 10 BP A股成本后 = +3.32 BP 盈利)
- **Phase 6 IC Loss HPO 运行中**: Job `4241649348649156608`, 70 trials, 8 parallel, A100 Spot
  - 7 维搜索: lr, λ_s, warmup, hidden_dim, window_size_t, batch_size, anchor_weight
  - Docker v9-phase6, NVMe prefetch (gcloud storage cp)
  - 预算 ~$108, 预计 ~13h wall time
  - Cron `6e9126c0` 每 15 分钟监控
- **GCS Shard 修复完成**: 200/200 腐败 shard 从 linux1 重新上传, 0 失败
- **linux1 已安装 gsutil**: pip3 install (未认证，通过 omega-vm proxy 上传)

## Changes This Session
- `f3cbc88` feat: INS-018 IC Loss — Pearson Correlation replaces Huber/MSE
- `9b0c137` feat: architect directive — Cross-Sectional Relativity (INS-018)
- `d98f43d` docs: bitter lesson — cloud resource guess-and-check
- `5361929` feat: Vanguard v4 — 1TB disk + NVMe prefetch + resume
- `64abf95` feat: Vanguard Protocol — A100 Spot + TF32
- `2a223bf` feat: Phase 5a signal direction test
- (本次 commit) Phase 6 HPO: train.py anchor_weight, phase6_icloss_hpo.yaml, spec 更新, Dockerfile

## Key Decisions
1. **Huber → IC Loss**: Vanguard V1 Spread=-1.67 BP (FAIL), V2 IC Loss Spread=+11.07 BP (STRONG PASS). 方向完全翻转
2. **A股印花税修正**: 15 BP → 5 BP 单边卖出 + ~3 BP 佣金 = ~8-10 BP round-trip. Top 10% 已盈利
3. **7 维 HPO 搜索**: RECON HPO 在 Huber 下做的，IC Loss 梯度景观不同，需重搜。新增 batch_size + anchor_weight
4. **anchor_weight ≥ 1e-4**: Gemini 审计发现 0.0 有 FP16 NaN 风险
5. **warmup [2,3,5]**: Gemini 审计 — warmup=7 + epochs=15 只剩 8 epoch MDL 训练
6. **gcloud storage cp 替代 gsutil**: A100 网络 50-100 Gbps, prefetch 从 25min → 3-5min
7. **Shard 修复**: 200 个腐败 shard 根因 = 上传截断（非 ETL 错误），linux1 原始数据完好

## Next Steps
1. **等待 Phase 6 HPO 完成** (~13h, Job 4241649348649156608)
2. **Top-3 trials Phase 5a 回测**: 取 IC 最高的 3 个 trial, 提交 Phase 5a
3. **成功标准**: Spread > 8 BP + 9/9 单调性 → 实盘就绪
4. **如果不够**: 考虑离线预计算截面 Z-score Target (INS-018 Plan B)

## Warnings
- **Phase 6 HPO 在 A100 Spot 上**: 抢占风险存在，但有 step-500 checkpoint + exit(143) + auto-resume
- **batch_size=512 + hidden=256 + wt=32 可能 OOM**: OOM handler 自动报 999.0, ~3% trial INFEASIBLE
- **gcloud storage cp 在 Vertex AI 容器中**: 未 100% 验证，如果失败需监控首批 trial
- **current_spec.yaml 已更新**: loss/metric/HPO 搜索空间已改为 IC Loss 版本

## Remote Node Status
- linux1: ONLINE, /omega_pool 7% used (2.4T free), 无 Python 进程, gsutil 已安装 (未认证)
- windows1: 本次会话未涉及

## Architect Insights (本次会话)
- INS-017 先锋定标战役: Vanguard V1 (Huber) 20 epoch FAIL → 已归档, **完成: FAIL**
- INS-018 横截面相对论: MSE→IC Loss + 绝对收益→截面排序 → **Vanguard V2 STRONG PASS**
