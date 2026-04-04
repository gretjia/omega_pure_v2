## WHY Chain

1. WebDataset 188 shards 随机流式加载 → batch 内样本跨越不同市场时期
2. Softmax(dim=0) 在 Batch 维度做 winner-take-all → 模型只需区分"好样本"和"差样本"
3. 宏观 Bull/Bear Beta 信号强度 ~200 BP，微观个股 Alpha ~5 BP
4. 模型走捷径: 识别宏观环境(Beta) 比学习个股信号(Alpha) 简单 1000x
5. Logit 膨胀到 6956 BP 以极化 Softmax 权重 → 所有资金分配给牛市样本
6. 模型输出完全是 Beta exposure，零 Alpha 信号

**根因**: Batch 维度归一化/竞争操作在 shuffled 跨期数据上，将宏观市场信号注入到每个样本的相对排序中。模型利用这个泄漏的信号走捷径，放弃学习真正的个股 Alpha。

## 为什么现有教训没拦住

C-042 (Z-score NaN) 的教训是关于 **数值稳定性**（权重范数膨胀 → NaN），修复方案是 `.detach() + clamp`。

C-045 不是数值问题（训练不会 NaN），而是 **学习目标被劫持**（模型学到正确的数值输出，但输出的语义是 Beta 而非 Alpha）。C-042 的教训关注的是 "Z-score 如何影响梯度"，没有覆盖 "Batch 维度操作如何泄漏宏观信息"。

这两个问题的共同根源是 Batch 维度归一化，但症状和机制完全不同:
- C-042: 梯度 → 权重 → 数值崩溃 (NaN)
- C-045: 信息泄漏 → 学习捷径 → 语义崩溃 (Beta smuggling)

## 模式泛化

**Batch 维度是信息泄漏通道**。任何在 Batch 维度上做的操作（Softmax、Z-score、BatchNorm、排序）都会将 batch 内其他样本的信息注入到每个样本的梯度中。当 batch 内样本来自不同时间/环境时，这等于泄漏宏观市场状态。

绝对规则: **禁止在 Batch 维度 (dim=0) 上做任何归一化或竞争操作**。如果需要归一化，只能在 Feature 维度 (dim=-1) 或 Spatial 维度上进行。

这是 Pointwise Loss 设计哲学的数学基础: 每个样本的 loss 只依赖自身，不依赖 batch 内其他样本。
