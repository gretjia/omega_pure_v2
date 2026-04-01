# Phase 11c Post-Flight Plan: Pointwise Spear & Epiplexity Verification

**Date:** April 1, 2026
**Status:** Pending Training Completion
**Context:** This plan defines the strict execution path following the completion of the Phase 11c (Pointwise Spear) Vertex AI training run. It serves as the ultimate litmus test for both the absolute BP architectural shift and the Epiplexity (S_T) compression axiom.

---

## Step 0: Confirm Training Convergence

```bash
# SSH 到控制节点，查看训练日志尾部
# 确认 E20 完成，记录 Best Epoch 的 Val PfRet / S_T / Std_yhat
```

## Step 1: Download Best Checkpoint

```bash
# Checkpoint 位置:
gsutil cp gs://omega-pure-data/checkpoints/phase11c_pointwise_v1/best.pt ./checkpoints/

# 验证文件完整性
python3 -c "
import torch
ckpt = torch.load('checkpoints/best.pt', weights_only=False)
print('Epoch:', ckpt.get('epoch'))
print('Val PfRet:', ckpt.get('best_metric'))
print('Keys:', list(ckpt.keys())[:10])
"
```

## Step 2: Clean Inference (Generate predictions.parquet)

**Critical Context:** This step will execute using the newly patched `phase7_inference.py` which outputs native absolute BP, free from the Train-Serve Skew multiplier.

```bash
# 在 GPU 节点执行（或提交 Vertex AI inference job）
PYTHONUNBUFFERED=1 python3 tools/phase7_inference.py \
  --checkpoint checkpoints/best.pt \
  --shard_dir /path/to/wds_shards_v3_full \
  --hidden_dim 64 \
  --window_size_t 32 \
  --batch_size 512 \
  --output predictions_phase11c.parquet
```

## Step 3: `pred_bp` Physical Scale Assertion (Architect Redline)

**Critical Context:** This is the immediate mathematical proof of our Bug C-049 fix. If the Train-Serve Skew were still present, the std would be > 40,000 BP.

```python
import pandas as pd
df = pd.read_parquet("predictions_phase11c.parquet")
std = df["pred_bp"].std()
mean = df["pred_bp"].mean()
print(f"pred_bp — mean: {mean:.1f} BP, std: {std:.1f} BP")
print(f"range: [{df['pred_bp'].min():.0f}, {df['pred_bp'].max():.0f}]")

# The Ultimate Litmus Test
assert 200 < std < 500, f"FAIL: std={std:.1f} 不在 200-500 BP 物理区间"
print("✓ 物理标尺断言通过")
# 预期: std ≈ 300-400 BP（匹配训练时 Std_yhat）
```

## Step 4: Ungated Backtest

```bash
PYTHONUNBUFFERED=1 python3 backtest_5a.py \
  --checkpoint checkpoints/best.pt \
  --shard_dir /path/to/wds_shards_v3_full \
  --hidden_dim 64 \
  --window_size_t 32 \
  --costs_bp 15.0 \
  --output_dir results/phase11c_clean/
```
**关注指标:**
- `long_short_spread_bp` > 8 BP（扣成本后正期望）
- `monotonicity_score` ≥ 7/9
- 各 decile 的 `mean_actual_bp` 单调性

## Step 5: Trading Simulation

```bash
PYTHONUNBUFFERED=1 python3 tools/phase7_simulate.py \
  --predictions predictions_phase11c.parquet \
  --output_dir results/phase11c_clean/
```
**架构师成功标准:**
| 指标 | 目标 | 说明 |
|------|------|------|
| `asymmetry_payoff_ratio` | > 1.5（冲 2.0+）| 非对称 Target 遮蔽下右尾主升浪 |
| `profit_factor` | > 1.5 | 盈亏比 |
| `decile monotonicity` | daily cross-sectional | 避免全局池化偏差 |

## Step 6: Decile Alpha Decomposition — Epiplexity Axiom Verification

```python
import pandas as pd
import numpy as np

df = pd.read_parquet("predictions_phase11c.parquet")

# 按 z_sparsity 分 10 桶（低 S_T = 高压缩 = 桶 0）
df["sparsity_decile"] = pd.qcut(df["z_sparsity"], 10, labels=False)

# 每桶计算：mean alpha, mean |pred|, hit rate
for d in range(10):
    bucket = df[df["sparsity_decile"] == d]
    alpha = bucket["target_bp"].mean()
    pred_abs = bucket["pred_bp"].abs().mean()
    hit = (bucket["target_bp"] > 0).mean()
    corr = bucket["pred_bp"].corr(bucket["target_bp"])
    print(f"Decile {d} (S_T {'低' if d<3 else '中' if d<7 else '高'}): "
          f"Alpha={alpha:+.1f}BP  |pred|={pred_abs:.0f}BP  "
          f"Hit={hit:.1%}  IC={corr:.3f}  N={len(bucket)}")

# 关键检验: Corr(z_sparsity, |pred|) 不应为 -0.34
corr_old = df["z_sparsity"].corr(df["pred_bp"].abs())
print(f"\nCorr(z_sparsity, |pred|) = {corr_old:.3f}")
print("Phase 10 病态值 = -0.34")
print("✓ 打破" if abs(corr_old) < 0.15 else "✗ 仍病态")
```

**架构师判定标准:**
| 检验 | 通过条件 | 含义 |
|------|----------|------|
| Decile 0-2 Alpha > Decile 7-9 | 低 S_T = 高 Alpha | 压缩即智能 |
| Corr(z_sparsity, \|pred\|) ≈ 0 | 打破病态 -0.34 | 模型不再靠放大尺度获利 |
| 低 S_T 桶 IC > 高 S_T 桶 IC | 高压缩 = 精准预测 | Epiplexity 理论证实 |

## Step 7: Decision Fork

**IF Step 6 通过 (Epiplexity 公理证实):**
- 重启 Epiplexity Gating（INS-039 失败根因已排除）
- 设计 `z_sparsity` 门控阈值，过滤高熵赌徒
- 进入 Phase 12: 双头阿修罗 (Long Head + Veto Head)

**IF Step 6 不通过:**
- 分析哪一步断裂
- 可能需要调整 λ_s 或 MDL 压缩强度
- 回到架构师会诊
