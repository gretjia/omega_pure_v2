# Phase 5 Backtest SPEC — Signal-Driven A-Share Strategy

## Objective
用 T16 best.pt (FVU=0.998896) 在验证集上做历史回测，验证 0.11% 方差解释力能否转化为正期望收益。

## Model
- Checkpoint: `gs://omega-pure-data/checkpoints/phase4_standard/trial_16/best.pt`
- Architecture: OmegaTIBWithMasking(hidden=128, window=(16,10), cg=1)
- 参数: ~80K
- 输出: 预测值 (Z-score 空间) → pred_bp = pred * 216.24 + (-5.08) (BP)

## Data
- Validation shards: 最后 20% of 1992 shards = shard 1594-1992 (399 shards)
- 每个 sample 含: manifold_2d.npy, target.npy, c_friction.npy, meta.json(symbol, timestamp)
- 时间排序: shard 编号递增 = 时间递增 (temporal split)

## Strategy Logic

```
初始状态: portfolio = {}, cash = 1.0 (normalized)

对每个时间步 t 的每只股票 s:
  prediction_bp = model(manifold[s][t]) * TARGET_STD + TARGET_MEAN

  如果 未持有 s:
    如果 prediction_bp > BUY_THRESHOLD:
      买入 s，记录 entry_price = VWAP(t), entry_date = date(t)

  如果 持有 s:
    如果 days_held >= 1 (T+1 满足):
      如果 prediction_bp < SELL_THRESHOLD (信号反转):
        卖出 s，记录 exit_price = VWAP(t)
        PnL = (exit - entry) / entry * 10000 - COSTS_BP
```

## Parameters (扫描)
- BUY_THRESHOLD: [10, 20, 50, 100] BP (预测收益 > X BP 才买)
- SELL_THRESHOLD: [-10, -20, -50, 0] BP (信号反转阈值)
- MAX_POSITIONS: [5, 10, 20] (同时持仓上限)
- COSTS_BP: 15 BP roundtrip (印花税 5 BP 卖出 + 佣金 6 BP 双边 + 滑点 4 BP 双边, 2023年后减半印花税)

## Two-Phase Approach

### Phase 5a: 信号统计测试 (快速, ~10 min)
不需要 stock identity，不需要 T+1 模拟。纯统计测试：
1. 对全部 val 样本做推理 → (prediction_bp, actual_target_bp) pairs
2. 按 prediction_bp 分位数分桶 (top 10%, 20%, 50%)
3. 计算每个桶的: mean actual return, hit rate (>0), mean win/mean loss
4. 如果 top 10% 的 mean return > 15 BP (覆盖成本) → Phase 5b
5. 如果 top 10% 的 mean return < 0 → 信号无效，停止

### Phase 5b: 完整 T+1 回测 (需要 meta.json, ~30 min)
1. 读取 meta.json 获取 stock symbol + timestamp
2. 按 (symbol, timestamp) 排序重建时间序列
3. 模拟 T+1 约束的完整交易
4. 输出: 交易明细 CSV + 绩效报告

## Output Metrics
1. **Asymmetry Payoff Ratio** = mean(wins) / mean(losses) — 必须 > 3.0
2. **Sharpe Ratio** (年化)
3. 胜率 (win rate)
4. 平均持仓天数
5. 最大回撤 (max drawdown)
6. 净收益 (扣除成本后)
7. 交易次数
8. 年化收益率

## Infrastructure
- Vertex AI L4 custom job (same Docker v5 image)
- 推理时间: ~10-30 min (80K 参数, 399 shards)
- 总成本: ~$1-2
- 输出: gs://omega-pure-data/backtest/phase5_t16/

## Script: backtest.py
- 单文件, 嵌入 Docker 或 从 GCS 下载
- 依赖: torch, webdataset, numpy, json (全部已在 Docker v5 中)
- CLI args: --checkpoint, --shard_dir, --output_dir, --phase (5a or 5b)

## Success Criteria

### Phase 5a (当前模型, 欠训练)
- **PASS**: top decile mean return > 0 BP (信号方向正确)
- **STRONG PASS**: top decile mean return > 5 BP (方向正确且有统计意义)
- **FAIL**: top decile mean return ≤ 0 (信号方向错误, 停止)

### Phase 5a PASS 后的路径
1. 用 T16 最优超参做全量训练 (epochs=20-30, 100K+ steps, ~$5-10)
2. 用全量训练后的模型做 Phase 5b 完整回测
3. Phase 5b 成功标准: Asymmetry Payoff Ratio > 3.0

### 为什么不直接做 Phase 5b
T16 是 RECON trial (40K steps, 0.6 passes), 欠训练。
R²=0.11% 是信号存在性的证据, 不是最终预测力上限。
用欠训练模型测 asymmetry ratio 没有参考价值。
