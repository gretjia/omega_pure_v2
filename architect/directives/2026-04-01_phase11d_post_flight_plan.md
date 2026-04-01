# Phase 11d Post-Flight Plan — 训练完成后执行

**前置条件**: Phase 11d Config A 和/或 Config B 训练完成 (E20)
**执行者**: 下一个 session 的 AI + 用户
**参考**: C-052 (独立烟测), C-055 (阈值实测标定)

---

## Step 0: 确认训练结果

```bash
# 下载最终 train.log
gsutil cp gs://omega-pure-data/checkpoints/phase11d_A_v1/train.log /tmp/a.log
gsutil cp gs://omega-pure-data/checkpoints/phase11d_B_v1/train.log /tmp/b.log

# 提取所有 epoch 摘要
grep "DONE" /tmp/a.log
grep "DONE" /tmp/b.log

# 记录: 哪个 config 的 Best PfRet 更高? pred_std 更健康?
```

**决策**: 选 pred_std 更高且 PfRet 更好的 config 作为 winner。

---

## Step 1: 下载 Best Checkpoint

```bash
# 替换 X 为 winner (A 或 B)
gsutil cp gs://omega-pure-data/checkpoints/phase11d_X_v1/best.pt ./checkpoints/phase11d_best.pt

# 验证完整性
python3 -c "
import torch
ckpt = torch.load('checkpoints/phase11d_best.pt', weights_only=False)
print('Epoch:', ckpt.get('epoch'))
print('Val PfRet:', ckpt.get('best_metric'))
"
```

---

## Step 2: 净网推理 (Val Only — C-052)

```bash
PYTHONUNBUFFERED=1 python3 tools/phase7_inference.py \
  --checkpoint checkpoints/phase11d_best.pt \
  --shard_dir /path/to/wds_shards_v3_full \
  --date_map /path/to/shard_date_map.json \
  --hidden_dim 64 --window_size_t 32 --window_size_s 4 \
  --batch_size 512 \
  --val_only --val_split 0.2 \
  --output predictions_phase11d_val.parquet
```

**关键**: `--val_only` 确保只跑验证集，不污染 in-sample 数据。

---

## Step 3: 方差哨兵阈值实测标定 (C-055)

```python
import pandas as pd
import numpy as np

df = pd.read_parquet("predictions_phase11d_val.parquet")

# 3a. 基础统计
pred_std = df["pred_bp"].std()
pred_mean = df["pred_bp"].mean()
print(f"pred_bp: mean={pred_mean:.2f}, std={pred_std:.2f}")
print(f"target_bp: mean={df['target_bp'].mean():.2f}, std={df['target_bp'].std():.2f}")

# 3b. 十分位 spread 实测
df["pred_decile"] = pd.qcut(df["pred_bp"], 10, labels=False, duplicates="drop")
decile_means = df.groupby("pred_decile")["target_bp"].mean()
spread = decile_means.iloc[-1] - decile_means.iloc[0]
mono = sum(1 for i in range(len(decile_means)-1)
           if decile_means.iloc[i+1] > decile_means.iloc[i])
print(f"D9-D0 spread: {spread:.2f} BP")
print(f"Monotonicity: {mono}/{len(decile_means)-1}")

# 3c. pred_std → spread 映射
# 这个比值就是未来标定方差哨兵的依据
ratio = spread / pred_std
print(f"Spread/pred_std ratio: {ratio:.2f}")
print(f"要覆盖 25 BP 交易成本, pred_std 需 > {25/ratio:.1f} BP")
print(f"要覆盖 50 BP (安全边际), pred_std 需 > {50/ratio:.1f} BP")

# 3d. 更新哨兵阈值建议
cost_threshold = 25 / ratio  # 盈亏平衡
safe_threshold = 50 / ratio  # 2x 安全边际
print(f"\n建议更新 train.py 方差哨兵:")
print(f"  ERROR (脑死亡): pred_std < {cost_threshold/3:.0f} BP")
print(f"  WARNING (不足): pred_std < {cost_threshold:.0f} BP")
print(f"  HEALTHY (安全): pred_std > {safe_threshold:.0f} BP")
```

---

## Step 4: 无门控回测

```bash
PYTHONUNBUFFERED=1 python3 backtest_5a.py \
  --checkpoint checkpoints/phase11d_best.pt \
  --shard_dir /path/to/wds_shards_v3_full \
  --hidden_dim 64 --window_size_t 32 --window_size_s 4 \
  --costs_bp 15.0 \
  --output_dir results/phase11d_clean/
```

**关注**:
- D9-D0 spread > 25 BP (覆盖交易成本)
- Monotonicity ≥ 7/9
- IC > 0.03

---

## Step 5: 交易模拟

```bash
PYTHONUNBUFFERED=1 python3 tools/phase7_simulate.py \
  --predictions predictions_phase11d_val.parquet \
  --output_dir results/phase11d_clean/
```

**架构师成功标准**:
- asymmetry_payoff_ratio > 1.5 (冲 2.0+)
- profit_factor > 1.5

---

## Step 6: Epiplexity 公理验证 (十分位 Alpha 分解)

```python
df = pd.read_parquet("predictions_phase11d_val.parquet")

# 按 z_sparsity 分 10 桶
df["sp_decile"] = pd.qcut(df["z_sparsity"], 10, labels=False, duplicates="drop")

print("S_Dec    N    mean_zs   mean_target  mean_|pred|      IC")
for d in sorted(df["sp_decile"].unique()):
    b = df[df["sp_decile"] == d]
    mzs = b["z_sparsity"].mean()
    mt = b["target_bp"].mean()
    mpa = b["pred_bp"].abs().mean()
    ic = b["pred_bp"].corr(b["target_bp"])
    print(f"  S{d}    {len(b):>5}  {mzs:>8.5f}  {mt:>11.2f}  {mpa:>11.2f}  {ic:>8.4f}")

# 关键检验
corr_zs_pred = df["z_sparsity"].corr(df["pred_bp"].abs())
print(f"\nCorr(z_sparsity, |pred|) = {corr_zs_pred:.4f}  (Phase 10 = -0.34, Phase 11c = -0.22)")
```

**判据**:
- 如果"低 S_T = 高 Alpha = 高 IC" → Epiplexity 公理成立 → 启动 Gating
- 如果仍无序 → z_core 激活了但没学到有意义的拓扑信号 → 需架构师会诊

---

## Step 7: 决策分叉

```
IF Step 4 spread > 25 BP AND Step 5 asymmetry > 1.5:
  → Phase 12: Epiplexity Gating 或实盘准备
  
IF spread 10-25 BP (有信号但不够):
  → 考虑 HPO 在 Phase 11d 参数空间内精调 (lr, λ_s, δ)
  
IF spread < 10 BP (复苏失败):
  → 架构级重构（SRL 捷径问题、模型容量、目标函数）
```

---

## 执行纪律

- [ ] 全部用 val 数据，绝不碰训练集 (--val_only)
- [ ] 所有阈值用 Step 3 实测值，不用旧的 10/30 BP
- [ ] 结果写入 reports/phase11d_postflight_results.md
- [ ] 更新 handover/LATEST.md
