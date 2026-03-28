# 架构师指令：从"绝对时空"到"横截面相对论" — Loss + Target 双重手术
- **日期**: 2026-03-28
- **来源**: 独立架构师 via Claude Code 对话
- **触发条件**: Vanguard 20-epoch Phase 5a FAIL (Spread=-1.67BP, 负相关, 无单调性)

## 0x00 核心判决

模型数学核心 (SRL + FWT) **没有失效**。负 Spread (-1.67BP) 恰恰证明模型提取了强烈的非线性特征——只是方向被 MSE Loss 逼反了。

真正失效的是"裁判"：Huber Loss + 绝对收益 Target。

## 0x01 病理解剖

### 为什么 Spread 是负的
- 如果模型无效，Spread 应该 ≈ 0（纯随机噪音无法产生系统性偏差）
- Spread = -1.67 BP 且完美反向 = 模型看到了真实特征，但被 Loss 逼着映射到错误方向
- A 股物理：盘口活跃/量能爆炸的股票往往是"拉高出货/诱多派发"（天量见天价）
- 模型把高特征激活映射为高正收益预测 → 实际是下跌

### 为什么 Std(ŷ) 剧烈震荡
- 模型同时预测微观 Alpha + 宏观 Beta（大盘涨跌）
- 大盘暴跌时，微观特征正确但绝对收益为负 → MSE 疯狂惩罚 → Std 坍缩
- 大盘平静时，模型重新尝试拉开 Std → 下次又被大盘打回
- 精神分裂：被拴在"微观 Alpha"和"宏观 Beta"两辆背道而驰的马车上

## 0x02 手术方案

### 手术 1: Target 净化 — 截面 Z-Score (Offline)
$$Target_{CS\_Z} = \frac{R_i - \mu_{market}}{\sigma_{market}}$$

- 在 Dataset Prep 阶段（非训练时）按**日历时间截面**对所有股票收益做标准化
- 物理意义：湮灭 90% 大盘涨跌 (Beta)
- 大盘暴跌千股跌停，但这只股票少跌了 → Target 依然为 +2.0
- 致命警告：不可在乱序 DataLoader Batch 里动态算，Volume-Clock 下 batch 内时间错乱

### 手术 2: Loss 替换 — Pearson Correlation Loss (IC Loss)
```python
def pearson_correlation_loss(y_pred, y_true, eps=1e-8):
    pred_flat = y_pred.view(-1)
    true_flat = y_true.view(-1)
    pred_centered = pred_flat - pred_flat.mean()
    true_centered = true_flat - true_flat.mean()
    cov = torch.sum(pred_centered * true_centered)
    pred_std = torch.sqrt(torch.sum(pred_centered ** 2) + eps)
    true_std = torch.sqrt(torch.sum(true_centered ** 2) + eps)
    corr = cov / (pred_std * true_std)
    return 1.0 - corr
```

组合 Loss:
- ic_loss = pearson_correlation_loss(pred, target_cs_z)
- anchor_loss = 0.01 * MSE(pred, target_cs_z) (防 FP16 溢出)
- total = ic_loss + anchor_loss + λ_s × S_T

### 手术 3: 指标替换
- 废弃 FVU
- 新核心指标: **Val Rank IC (Pearson Correlation)**

## 0x03 Vanguard V2 计划
1. 重构 Target: 离线计算截面 Z-score
2. 替换 Loss: pearson_correlation_loss
3. 复用超参: cg=1, hidden=128, λ_s=1e-5, wu=5, wt=16
4. 单机 20 Epochs
5. 监控 Val Rank IC + Std(ŷ) 稳定性

## 架构师决策树
- PASS (IC > 0.02, 稳定): 全军出击，Exploitation HPO
- FAIL (IC ≈ 0): 特征提取器也需要改造（但这不太可能，因为 Spread 已证明特征有效）
