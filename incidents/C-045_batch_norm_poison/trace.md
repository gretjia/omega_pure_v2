## 背景

Phase 10 引入 Softmax Portfolio Loss (02a2fbe)，使用 `Softmax(dim=0)` 将 batch 内预测值转化为 portfolio weights，然后乘以 batch Z-scored targets 计算 portfolio return。

WebDataset 使用 188 shards 的随机流式加载（shuffled），每个 batch 的样本来自不同日期、不同股票。这意味着同一个 batch 内的样本可能跨越牛市和熊市时期。

## 执行序列

1. Phase 10 训练配置:
   ```python
   # Softmax Portfolio Loss
   weights = F.softmax(predictions, dim=0)  # dim=0 = Batch 维度
   z_targets = (targets - targets.mean()) / targets.std()  # Batch Z-score
   portfolio_return = (weights * z_targets).sum()
   ```

2. WebDataset 随机 shard 加载:
   ```
   Batch 1: [2024-01-05_stock_A, 2024-06-15_stock_B, 2024-03-20_stock_C, ...]
   → 跨越不同市场环境的样本混合在同一 batch
   ```

3. 模型发现: 识别 macro bull/bear Beta 比 micro Alpha 简单 1000x:
   ```
   牛市样本 target: +200 BP (宏观趋势)
   熊市样本 target: -150 BP (宏观趋势)
   个股 Alpha:      ±5 BP   (微观信号)
   
   Softmax(dim=0) 只需把权重集中到牛市样本 → 稳定正 return
   无需学习任何个股 Alpha
   ```

4. Logit 膨胀观测:
   ```
   Std_yhat: 6956 BP (正常应 ~30 BP)
   模型输出: 极端正/负值区分牛熊样本
   Asymmetry ratio: 22.9x (Casino Exploit)
   ```

5. Phase 10 P0 Crucible Test 十分位拆解确认:
   ```
   D0 (最弱预测): 大量熊市样本
   D9 (最强预测): 大量牛市样本
   → 模型学到的是时间戳/市场环境的 Beta，不是个股 Alpha
   ```

6. 诊断: Softmax(dim=0) + Batch Z-score 在 shuffled WebDataset 上创建了跨期毒药:
   - Batch 内样本来自不同时期 → Batch 统计量包含宏观信息
   - Softmax 在 Batch 维度竞争 → 模型用宏观 Beta 赢得竞争
   - Z-score 在 Batch 维度标准化 → 进一步放大跨期差异

## 环境

- Vertex AI Custom Job, L4 GPU
- 188 shards WebDataset, shuffled 随机流式加载
- 556GB 数据涵盖 2021-2024 A股市场（包含多轮牛熊周期）
- Softmax Portfolio Loss (INS-033, Gemini 3x 审计通过)
- Gemini 审计未检出此问题（审计在理想化均匀分布假设下进行）
