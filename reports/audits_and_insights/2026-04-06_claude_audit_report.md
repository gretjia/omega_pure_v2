# Omega-TIB Independent Quality Audit Report
**Auditor**: Claude Opus 4.6 (Independent ML/Quant Auditor)
**Date**: 2026-04-06
**Subject**: Omega-TIB Model (24,581 params), Full Lifecycle Assessment

---

## Q1. hd=64 是否必须在 Phase 13 管线上重新测试？

**判定: 是。必须重测。**

证据链：
1. hd=64 的选定依据是 Phase 6 HPO T29 (IC=0.066)。
2. INS-072 宣布 Phase 6 全部基线作废 (C-062 torch.compile bug)。
3. Phase 14 Step 1 复测 T29: Rank IC=0.0023, pred_std=790 BP -- 这是一个噪声发生器，不是模型。
4. Phase 13 在修复后管线 (IC Loss + Pre-LN + AttentionPooling) 上直接沿用 hd=64，**从未对比 hd=128/256**。

hd=64 意味着每个注意力头的维度仅为 16 (64/4 heads)。这个维度在 NLP/CV 中极其罕见——标准 Transformer 头维度为 64。16 维的 key/query 空间是否足以编码 A 股 LOB 中的拓扑结构？没有数据回答这个问题。

更关键的是：hd=64 占参数量的绝对主导地位。FWT qkv 层 (12,288) + proj (4,160) + RPB (4,788) = 21,236, 占总参数的 86.4%。如果 hd=128，qkv 翻四倍到 ~49K，proj 翻四倍到 ~16K，RPB 不变 (取决于窗口大小而非 hd)，总参数约 70K。这仍然是一个极小模型。

**成本估算**: Phase 13 一次完整训练 = T4 10.5h。hd=128 约 15h (attention 是 O(D^2) 的，但实际受限于 IO，预计 1.5x)。三个 hd 值 (64/128/256) 并行跑约需 50h T4 = ~$25。这是一个极低成本、高信息量的实验。

---

## Q2. batch=256 的 IC 梯度信噪比是否 < 1？

**判定: 是。梯度信噪比 < 1，信号被采样噪声淹没。**

精确计算：

IC Loss = -Pearson(pred, target)。Pearson 相关系数的采样标准误差近似为：

$$SE(r) \approx \frac{1 - r^2}{\sqrt{N - 2}}$$

对于 r = 0.029 (Phase 13 Rank IC, Pearson IC 约 0.010):
- N = 256, SE = (1 - 0.01^2) / sqrt(254) = 0.9999 / 15.94 = **0.0627 = 6.27%**
- 真实信号: Pearson IC = 0.010 = **1.0%**
- **信噪比 = 0.010 / 0.0627 = 0.16**

这意味着每个 batch 的 IC 梯度中，只有 16% 是信号，84% 是噪声。优化器在本质上是在做随机游走，偶尔幸运地往正确方向迈一步。

不同 batch size 下的 SE:
| Batch Size | SE(r) | 信号/SE 比 | 有效 SNR |
|-----------|-------|-----------|---------|
| 256 | 6.27% | 0.16 | 极低 |
| 512 | 4.43% | 0.23 | 低 |
| 1024 | 3.13% | 0.32 | 低 |
| 2048 | 2.21% | 0.45 | 勉强 |
| 4096 | 1.56% | 0.64 | 可用 |
| 8192 | 1.10% | 0.91 | 接近 1 |

**要让梯度 SNR > 1，需要 batch size >= 10000**。

但这有一个微妙之处：AdamW 的自适应学习率和动量 (beta1=0.9) 实际上在做指数移动平均，等效于将 batch size 放大约 10x (1/(1-0.9) = 10)。所以有效 batch size 约 2560，对应 SE ~ 2.0%，有效 SNR 约 0.5。仍然低于 1，但 Adam 的二阶矩估计在一定程度上补偿了这一点。

**实际影响**：Phase 13 训练曲线的剧烈震荡 (E0-E14 Rank IC 从 0.007 到 0.029 再回到 0.012) 完美印证了这一分析。模型不是在稳定收敛，而是在噪声中碰运气。E9 的 0.0292 可能是 15 次独立抽样中的最大值。

**建议**: 梯度累积 (gradient accumulation) 到有效 batch=2048-4096 是零额外 GPU 成本的改进。唯一代价是训练时间 x8-x16，但 OneCycleLR 的 total_steps 需要相应调整。

---

## Q3. SRL 压缩是否充分？

**判定: 是。SRL 信息压缩在当前证据下是充分的。**

Phase 14 Step 2 是一个干净的 A/B 实验：
- Arm A (SRL only, 6维): Rank IC = +0.0122
- Arm B (SRL + 原始 V_D + sigma_D, 8维): Rank IC = +0.0064

Arm A 以近 2x 的优势胜出。这意味着 SRL 的 q_metaorder 不仅没有丢失 V_D 和 sigma_D 中的有用信息，反而通过物理先验将它们组合成了一个更高信噪比的单一特征。直接旁路反而引入了噪声。

但有一个重要保留意见：**这两个 Arm 的绝对 IC 都远低于 Phase 13 的 0.029**。Step 2 是独立训练的 short run，不是在 Phase 13 最优超参配置上跑的，所以绝对值不可直接比较。结论仅限于相对排序：SRL > SRL + raw macro。

---

## Q4. lambda_s=0 是否正确？

**判定: 是。在 Kurtosis=2006 的数据分布下，L1 惩罚是反信号的。**

6 Phase 的实证已经给出了结论性证据。让我给出数学论证：

**L1 在肥尾分布下为何杀信号**：

IC Loss 优化的是 Pearson 相关系数。假设 target 分布有 kurtosis=2006 (极端肥尾)，那么 target 的有效信息几乎全部集中在尾部的极少数样本上。

L1 惩罚 ||z_core||_1 等价于对瓶颈表示施加 Laplace 先验。这会将 z_core 中的大值推向零——而这些大值恰好对应模型对尾部事件的强响应。

具体地：
- 假设模型在 95% 的普通样本上 z_core 值在 [-1, 1]，贡献 L1 约 1.0。
- 在 5% 的尾部样本上 z_core 值在 [-10, 10]，贡献 L1 约 10.0。
- L1 梯度对所有值等权施加 sign(z) 的方向，不区分大小。

但 IC Loss 的梯度恰好需要模型在尾部样本上有大的预测差异——因为 Pearson 相关在标准化后，每个样本对 IC 的贡献与 (pred - mean) * (target - mean) 成正比。尾部的 target 偏差极大，是 IC 的主要贡献者。

L1 正则化相当于在说"不要在任何样本上有大的内部表示"，而 IC Loss 在说"必须在尾部样本上有大的预测差异"。两者在优化方向上存在系统性冲突。

**Phase 12 的数据完美印证**: L1 从 lambda_s=1e-4 开始，D9-D0 从 4.48 BP 压缩到 1.28 BP。L1 把 z_core 压平了，尾部信号也跟着死了。

---

## Q5. MLP baseline 是否应在进一步架构优化前执行？

**判定: 是。这是项目最大的实验空白之一。**

MLP baseline 的成本极低 (< 2h T4)，但信息量极高。它回答的核心问题是：**Omega-TIB 的物理层 + 拓扑层 + 注意力池化到底贡献了多少增量信号？**

设计：
- 输入: 同样的 [B, 160, 10, 6] 张量 (含 FRT 和 q_metaorder)
- 架构: Flatten → LayerNorm → Linear(9600, 256) → GELU → Linear(256, 64) → GELU → Linear(64, 1)
- 参数: ~2.5M (显著大于 Omega-TIB)
- Loss: IC Loss (同 Phase 13)
- 数据/训练: 完全相同的 shards、split、optimizer

如果 MLP 达到 Rank IC=0.025，那么 Omega-TIB 的整个物理+拓扑归纳偏置仅贡献了 0.004 的增量。这意味着要么归纳偏置不如预期重要，要么当前实现不够充分地利用了归纳偏置的优势。

如果 MLP 仅达到 Rank IC=0.005，那么 Omega-TIB 的归纳偏置贡献了 0.024，是信号的绝对主力。这将强力验证 OMEGA Manifesto。

不跑这个实验，你永远不知道 0.029 中有多少来自数据本身的模式 (任何模型都能抓到)，有多少来自你的物理先验。

---

## Q6. Phase 13 训练曲线 E9->E14 是什么状态？

**判定: [B] 噪声主导。**

判据：

1. **方差太大，无法区分过拟合和收敛**: E0-E14 的 Rank IC 标准差约 0.007 (range: 0.005 ~ 0.029)。在 +-0.007 的随机波动下，E9=0.029 和 E14=0.018 之间的差距 (0.011) 仅约 1.5 倍标准差。统计上无法拒绝"E9-E14 都是同一个分布的采样"的零假设。

2. **与 Q2 分析一致**: batch=256 下 IC 的 SE 约 6.3%，epoch 级别 (5000 steps) 的平均会将 SE 降低 sqrt(5000) 倍...不对。这里有一个关键区别：训练 IC 和验证 IC 不同。验证集是 1.9M 样本的单次前向，不存在采样噪声问题。所以验证 Rank IC 的波动不是采样噪声——它反映的是**模型权重在噪声梯度下的随机游走**。

3. **E10-E14 不是单调下降**: 0.021 → 0.012 → 0.018 → 0.017 → 0.018。这不像过拟合的典型模式 (单调下降)，而是随机震荡。如果是过拟合，验证 loss 应该稳定恶化，训练 loss 持续改善。

4. **Phase 13 在所有 15 个 epoch 都 Rank IC > 0**: 对比 Phase 12 的系统性负 IC，这说明 Phase 13 管线确实捕获了真实信号。但信号的精确强度在每个 epoch 之间有大的不确定性。

**核心结论**: E9 的 0.029 可能是真实信号强度的上界估计，而 E10-E14 的均值 ~0.017 更接近模型的真实稳态性能。最佳模型选择 (best Rank IC) 引入了选择偏差——在 15 次独立观测中取最大值，期望会高于真实均值约 1-2 个标准差。

**建议**: 用 SWA (Stochastic Weight Averaging) 或 EMA (Exponential Moving Average) 来平均最后 5 个 epoch 的权重。这会平滑掉权重空间的噪声，给出更稳定的估计。成本为零 (只需代码修改)。

---

## Q7. 单层注意力 + 零跨窗口通信 — 这是否是硬天花板？

**推理**:

当前模型的感受野：
- 时间维度: 32 bars = 0.64 天 (在一个窗口内)
- 空间维度: 10 (完整 LOB 深度，在窗口内)
- 跨窗口: **零通信**

5 个 32-bar 窗口覆盖 160 bars (~3.2 天)，但它们完全隔离。模型能检测到的最长连续模式是 0.64 天。

OMEGA Manifesto 说主力行为是"跨股票、跨板块、跨时间周期的立体协同"。一个 3-5 天的建仓计划在当前模型中被切成 5 个独立碎片，每个碎片独立处理后被 AttentionPooling 加权平均。AttentionPooling 确实赋予了不同窗口不同权重，但它只看 z_core 的值，不看窗口之间的*关系*。

**预期 IC 提升 (Swin-style shifted window, 2 层)**:

保守估计: +0.005 ~ +0.010 Rank IC (从 0.029 到 0.034-0.039)。

理由：
1. 第二层 shifted window 让相邻窗口的边界区域能交换信息。这相当于将有效感受野从 32 bars 扩展到 ~48 bars (1.5 个窗口的重叠区域)。
2. 但这不是翻倍——信号的主要来源可能仍然是单窗口内的模式。跨窗口信息的增量贡献取决于"有多少机构行为模式跨越了 32 bar 边界"。
3. 类比 CV: Swin Transformer 的 shifted window 在 ImageNet 上贡献了约 +1.5% top-1 accuracy (相对于非 shifted 版本)。相对于总信号来说约 10-15% 的提升。

如果 Phase 13 的 0.029 对应"模型能利用的真实信号的 ~85%"，那么跨窗口通信补上剩余的 ~15%，对应 0.029 * 0.15 = 0.004。加上两层的非线性容量增加，总计 +0.005 ~ +0.010 是合理区间。

**但有风险**: 两层注意力将参数从 24.6K 增加到 ~45K。在 batch=256 的噪声环境下，更多参数可能意味着更多噪声维度需要优化，净效果不确定。

---

## Q8. IC Loss 在 Kurtosis=2006 下是否最优？

**存在根本性矛盾。**

IC Loss (Pearson 相关) 对每个样本等权处理。数学上：

$$IC = \frac{\sum_i (p_i - \bar{p})(t_i - \bar{t})}{\sqrt{\sum_i(p_i - \bar{p})^2} \sqrt{\sum_i(t_i - \bar{t})^2}}$$

每个样本 i 对分子的贡献与 (t_i - mean_t) 成正比。在 kurtosis=2006 的分布中，99% 的样本的 |t_i - mean_t| 很小 (约在 +-190 BP 内)，而 1% 的尾部样本可能有 |t_i - mean_t| > 5000 BP。

所以 IC Loss 实际上已经*隐式地*给了尾部更大的权重——但这种权重是线性的 (与偏差成正比)，而 Taleb 哲学要求的是*凸性*暴露 (与偏差超线性增长的收益)。

**矛盾在于**: IC Loss 优化的是排序一致性 (对所有样本对等权排序)，而交易策略只关心极端十分位 (D0 和 D9)。一个 IC=0.03 的模型可能在 D4-D6 中间区域排序很好 (提升 IC 但不赚钱)，而在 D0/D9 的关键区域排序一般。

**替代 Loss 设计: Tail-Weighted IC Loss**

```python
def compute_tail_weighted_ic_loss(prediction, target, tail_boost=3.0, ic_epsilon=1e-8):
    """
    Tail-Weighted Pearson IC: 对尾部样本赋予更高梯度权重。
    tail_boost 控制尾部相对于中间的权重放大倍数。
    """
    pred = prediction.float().view(-1)
    tgt = target.float().view(-1)
    
    if pred.numel() < 2:
        return torch.tensor(0.0, device=pred.device, requires_grad=True)
    
    # 1. 计算 target 的截面分位数权重
    # 越接近尾部 (D0, D9)，权重越大
    tgt_rank = tgt.argsort().argsort().float() / (tgt.numel() - 1)  # [0, 1]
    # U-shaped weight: 高权重在两端 (D0 + D9)
    tail_weight = 1.0 + (tail_boost - 1.0) * (2.0 * torch.abs(tgt_rank - 0.5)) ** 2
    tail_weight = tail_weight / tail_weight.mean()  # normalize to mean=1
    
    # 2. Weighted Pearson correlation
    w = tail_weight
    pred_centered = pred - (w * pred).sum() / w.sum()
    tgt_centered = tgt - (w * tgt).sum() / w.sum()
    
    cov = (w * pred_centered * tgt_centered).sum() / w.sum()
    pred_std = torch.sqrt((w * pred_centered ** 2).sum() / w.sum() + ic_epsilon)
    tgt_std = torch.sqrt((w * tgt_centered ** 2).sum() / w.sum() + ic_epsilon)
    
    ic = cov / (pred_std * tgt_std)
    return -ic
```

预期效果：D9-D0 spread 应该增大 (因为尾部排序被优先优化)，但总 Rank IC 可能略微下降 (因为中间区域被牺牲)。这对交易来说是正确的权衡。

---

## Q9. 24.6K 参数 — 极简的胜利还是容量不足？

**推理**:

OMEGA Manifesto 的逻辑是对的："主力行为是低熵可压缩的" → 小模型应该足够。但"小"是相对于信号复杂度的，不是绝对的。

参数分配的问题比总量更严重：
- FWT qkv+proj+RPB: 21,236 (86.4%) — 这是编码拓扑结构的部分
- 信息瓶颈: 2,608 (10.6%) — 这是压缩信号的部分
- 池化+预测: 33 (0.1%) — 这是做决策的部分

模型把 86% 的参数花在了"看懂 LOB 拓扑"上，只有 10% 用来"压缩信号"，0.1% 用来"做预测"。

这个分配是否合理？如果 SRL 已经做了大部分物理压缩，那么 FWT 的任务应该是捕捉跨 LOB 深度的结构模式 (比如冰山单、分层挂单)。对于 10 层 LOB 深度、32 个时间步的窗口，320 个 token 的注意力模式可能确实需要这么多参数来编码。

**但瓶颈层 (64→32→16) 可能太窄了。** 最终的 z_core 维度只有 16。对于每个时空位置，模型只有 16 个数字来编码"这里发生了什么"。如果机构行为有 20-30 种可区分的模式 (建仓、洗盘、拉升、出货...)，16 维可能不够。

结论：**总参数量不是问题，参数分配是问题。** 考虑 hd=128 (64→32→16 变成 128→64→32)，这将瓶颈维度翻倍到 32，同时注意力容量也翻倍。这是最值得测试的单一变量。

---

## Q10. SRL 的 delta=0.5 在 A 股是否成立？

delta 偏离 0.5 的定性影响：

SRL 公式: Q = sign(dP) * |dP / (c * sigma)|^(1/delta) * V

- delta=0.4 → 1/delta=2.5: 同样的价格冲击产生更大的 Q 估计。相当于假设"A 股的机构更隐蔽——同样的元订单对价格的影响更小"。q_metaorder 的分布会更加肥尾 (极端值更极端)。
- delta=0.6 → 1/delta=1.67: 同样的价格冲击产生更小的 Q 估计。相当于假设"A 股的机构更粗暴——同样的元订单对价格的影响更大"。q_metaorder 的分布更集中。

A 股的特殊性：
1. T+1 制度使机构无法在日内频繁调仓，可能导致单次交易量更大 → 冲击更大 → delta > 0.5
2. 散户 >50% 意味着市场噪声更大，机构的真实冲击被散户噪声稀释 → 有效 delta < 0.5
3. 涨跌停使极端冲击被截断 → 不影响 delta 本身，但影响 SRL 在极端区域的有效性

**是否值得测试？** 是的，但优先级低于 hd 和 batch size。

**成本**: 零 GPU 成本。delta 只出现在 SRL 的 `power_constant = 1/delta`。改为 delta=0.4 (power=2.5) 和 delta=0.6 (power=1.67) 各训练一次，~20h T4 共 ~$10。但需要修改被标记为"永恒常数"的代码，需要架构师批准。

一个更聪明的做法是：**直接在验证集上测量 delta 的经验值**。用已有的 ETL 数据，对每只股票拟合 |dP/sigma| = c * (Q/V)^delta 的 log-log 回归，看斜率是否接近 0.5。这完全不需要训练模型。

---

## Q11. 正则化全面缺失 — 设计选择还是历史遗忘？

**lambda_s=0 是有意的设计 (6 Phase 实证)。其余三项 (weight_decay, dropout, mask_prob) 是历史遗忘。**

证据：
- weight_decay=1e-5: 代码中硬编码在 `torch.optim.AdamW(..., weight_decay=1e-5)`，从未作为超参搜索。1e-5 的 WD 对 24.6K 参数的模型几乎无效。
- dropout: 模型中不存在任何 dropout 层。
- mask_prob=0.0: VolumeBlockInputMasking 存在于代码中但在 Phase 13 中被禁用 (mask_prob=0)。

**轻量正则化的预期影响**:

对一个在 ~8M 训练样本 (1594 shards * ~5000 samples) 上训练 75K 步、batch=256 的 24.6K 模型：
- **理论过拟合风险极低**: 样本/参数比 = 8M/24.6K > 300。传统统计学认为 >20 就安全了。
- **但 IC Loss 不是 MSE**: IC Loss 优化的是排序，不是拟合。排序问题的有效维度远高于参数量，因为它涉及所有样本对的比较。

实际建议：
- **dropout=0.05 在 attention 输出后**: 预期影响微小但正向。不太可能伤害信号 (0.05 太轻了)，可能帮助平滑验证曲线的波动。
- **weight_decay=0.01**: 对 24.6K 模型，这会对 RPB 表和 qkv 权重施加轻微的 L2 约束。考虑到 RPB 有 4,788 参数且在 Phase 12 梯度极弱，WD 可能帮助 RPB 不要漂移太远。
- **mask_prob=0.3**: 最有意思的正则化。VolumeBlockInputMasking 强制模型在部分时间步缺失的情况下仍能预测，这可以被视为一种数据增强。但 Phase 13 禁用了它，且没有对比实验。

**优先级**: 中等。不如 batch size 和 hd 重要，但如果做 HPO 应该纳入 mask_prob 和 WD。

---

## Q12. Rank IC=0.029 在 A 股 L1 tick + T+1 隔夜的语境下处于什么水平？

**坦率地说：Rank IC=0.029 是一个边缘信号。**

量化背景：
- 券商自营/量化基金的 alpha 模型通常要求 Rank IC > 0.05，ICIR > 0.5
- 公开文献中 A 股日间截面 alpha 的 IC 范围：0.02-0.08 (好的因子)，>0.08 (极好的因子)
- 0.029 处于"可能有信号但不确定"和"明确有信号"的边界

**D9-D0=7.00 BP vs 交易成本 ~25 BP 的差距**:

这是一个致命的经济问题。Phase 13 的十分位表：
- D9 mean target: 8.85 BP
- D0 mean target: 1.85 BP
- D9 - D0 = 7.00 BP

Long-Short 策略的*毛收益*是 7.00 BP / 2 = 3.50 BP per leg。扣除 25 BP 往返成本后：**净亏损 -21.50 BP per trade**。

要覆盖成本，需要 D9-D0 > 50 BP (单边成本 12.5 BP * 2 legs = 25 BP，每边需要 >25 BP 的超额收益)。

**IC 与 D9-D0 的关系**: 在正态分布假设下，D9-D0 ≈ IC * 2.56 * sigma_target (2.56 是正态分布 D9 和 D0 中心的距离)。

需要的 IC = 50 / (2.56 * 189.6) = 50 / 485.4 = **0.103**。

即 Rank IC 需要从 0.029 提升到 ~0.10 (约 3.5x) 才能覆盖交易成本。这在单模型优化中几乎不可能。

**但有替代路径**：
1. 降低交易成本: 如果用 TWAP 执行 (5BP 冲击) + 低佣券商 (2BP) + 免印花税(ETF)，成本可降至 ~15 BP。
2. 组合 alpha: 与其他因子 (动量、估值、波动率) 叠加，总 IC 可达 0.05-0.08。
3. 选择性交易: 只在信号极端时交易 (D0/D9 的前 5% 而非前 10%)，D95-D5 的 spread 会更大。
4. 持有期延长: 20 bars ~ 0.4 天。如果延长到 2-3 天，成本被摊薄。

---

## Q13. 这个项目最大的盲区是什么？

**盲区 #1: 验证集可能存在数据泄漏 (时间序列交叉验证的缺陷)**

训练/验证的分割方式是 "前 80% shards 训练，后 20% shards 验证"。Shard 按文件名字母排序 (`omega_shard_*.tar`)。

关键问题：**shards 的命名顺序是否严格对应时间顺序？** 底稿 Section 九标记了 "Shard 命名是否严格按时间排序" 为 "缺失数据"。

如果 shards 不是严格按时间排序的 (例如按 symbol 或按处理顺序排列)，那么训练集和验证集可能包含同一天的不同股票的数据。在截面 IC 优化中，这意味着模型在训练时已经"看到了"验证集同期的市场状态，相当于前视偏差。

更严重的是：即使 shards 按时间排序，ETL 的 stride=20 (相邻窗口重叠 160-20=140 bars) 意味着在训练/验证边界处的样本有 ~87.5% 的时间重叠。这不是传统意义上的 "look-ahead bias"，但它意味着验证集的前几个 shard 与训练集的最后几个 shard 高度相关。

**应该有 embargo gap**: 在训练集和验证集之间放置 160 bars 的间隔，确保零重叠。

**盲区 #2: FRT (Financial Relativity Transform) 是在 GPU 上实时计算的，但 SRL 的输入用的是原始 ETL 值**

FRT 将 Bid/Ask 价格转换为 BP 偏差、Close 转换为累计对数收益、Volume 用 log1p 压缩。但 SRL 的三个输入 (delta_p, V_D, sigma_D) 是直接从 ETL 通道 7/8/9 取的原始值，没有经过 FRT 变换。

这意味着 LOB 特征 (ch0-4) 在 BP 和 log 尺度上，而 q_metaorder (由原始尺度的 delta_p/V_D/sigma_D 计算) 在一个完全不同的数值尺度上。虽然 q_metaorder 最后经过了 symlog 压缩，但这种尺度不匹配可能影响 input_proj 层的学习效率。

**盲区 #3: 模型预测的是什么？**

模型输出一个标量 `main_force_prediction`，训练目标是 forward VWAP return (BP)。但 IC Loss 只优化排序，不优化绝对值。这意味着模型学到的不是"这只股票明天涨多少 BP"，而是"这只股票明天在截面中的排名"。

这在概念上没问题，但在实际应用中产生了一个问题：**模型无法区分"所有股票都涨"和"所有股票都跌"的日子**。它只能给出相对排序。当市场系统性下跌时 (所有股票的 target 都是负的)，D9 仍然是最好的但可能还是亏钱。

这与项目的 Taleb 哲学 ("不对称比 > 3.0") 有根本性张力。不对称比需要绝对收益的不对称分布，而 IC Loss 只优化相对排序。

---

## Q14. 如果你接手这个项目，拥有 20 小时 T4 GPU 预算，你的前 3 个实验是什么？

### 实验 1: Gradient Accumulation + SWA (预期 Rank IC: 0.029 → 0.035-0.045)

**假设**: Phase 13 的 Rank IC=0.029 被两个因素严重压制：(1) batch=256 的梯度噪声导致优化不充分，(2) 最终 checkpoint 选择偏差。

**设计**:
- gradient_accumulation_steps = 16 (有效 batch = 4096)
- SWA: epoch 5 开始，对 epoch 5-14 的权重做指数移动平均 (tau=0.999)
- 其余完全同 Phase 13 (hd=64, IC Loss, lambda_s=0)

**成本**: ~10.5h T4 (同 Phase 13，gradient accumulation 不增加 GPU 时间，只是每 16 步才 optimizer.step()。但 OneCycleLR 需要将 total_steps 除以 16)

等等，这里有个细节。Gradient accumulation 不改变 wall clock time，但改变了 LR schedule 的有效步数。total_steps 从 75000 变成 75000/16 = 4687。需要调整 epochs 或 steps_per_epoch 来补偿。

修正方案: epochs=15, steps_per_epoch=5000, accumulation=16, total_optimizer_steps=4687, OneCycleLR(total_steps=4687)。

**预期成本**: 10.5h T4 = ~$3.50

**如果确认 (Rank IC > 0.035)**: 证明优化不充分是当前的主要瓶颈，Phase 13 的 0.029 远非管线极限。后续所有实验都应使用大 batch。
**如果否定 (Rank IC 无改善)**: 信号本身就是 ~0.03，需要架构改进而非训练技巧。

### 实验 2: MLP Baseline (预期 Rank IC: 0.005-0.025)

**假设**: Omega-TIB 的物理/拓扑归纳偏置贡献了 Rank IC 的主要部分 (>50%)。

**设计**:
- 输入: 同 Phase 13 的 6 维流形 (LOB_FRT + q_metaorder_symlog), flatten 为 [B, 160*10*6] = [B, 9600]
- 架构: LayerNorm → Linear(9600, 512) → GELU → Linear(512, 128) → GELU → Linear(128, 1)
- 参数: ~5.0M
- Loss: IC Loss, gradient accumulation=16
- 数据/训练: 完全同 Phase 13

**成本**: ~6h T4 (MLP 比 attention 快 2x) = ~$2

**如果确认 (MLP IC < 0.015)**: OMEGA 归纳偏置贡献了 >50% 的信号。继续优化 Omega-TIB 是正确方向。
**如果否定 (MLP IC >= 0.025)**: 归纳偏置的贡献极小。需要重新审视是否 SRL/FWT 真的在做有用的计算。

### 实验 3: hd=128 + dropout=0.05 (预期 Rank IC: 0.029 → 0.032-0.040)

**假设**: hd=64 的瓶颈 (最终 z_core 维度=16) 过窄，丢弃了部分可压缩信号。

**设计**:
- hd=128 (z_core 维度 = 32)
- 参数: ~70K
- 增加 dropout=0.05 after attention output (防止增加参数后的过拟合)
- gradient_accumulation=8 (有效 batch=2048)
- 其余同 Phase 13

**成本**: ~15h T4 = ~$5

**如果确认 (Rank IC > 0.035)**: hd=64 确实是瓶颈，Phase 6 HPO 的 "hd=64 ≈ hd=128" 结论在修复后管线上不成立。
**如果否定 (无改善)**: 瓶颈不在容量，可能在感受野 (跨窗口) 或数据质量。

**总预算**: 10.5 + 6 + 15 = 31.5h... 超了。调整: 实验 1 和 2 可以并行跑 (不同 Job)，实验 3 取决于实验 1 的结果。如果实验 1 确认大 batch 有效，则实验 3 直接用大 batch + hd=128。

修正预算: 实验 1 (10.5h) + 实验 2 (6h) = 16.5h。剩余 3.5h 不够跑实验 3。

**修正方案**: 将实验 3 改为 5 epoch 快速验证 (5/15 * 15h = 5h，但太短不可靠)。或者将实验 1 缩短到 8 epoch (足以看趋势)，节省 3h 给实验 3 的 8 epoch。

**最终分配**: 
- 实验 1: 8 epoch, ~5.5h
- 实验 2: 8 epoch, ~3h
- 实验 3: 8 epoch, ~8h
- 总计: ~16.5h, 留 3.5h buffer

---

## Q15. OMEGA Manifesto 理论与当前实现之间的脱节

### 脱节 #1: "压缩即智能" vs lambda_s=0 — **严重程度: 中**

理论说压缩是发现信号的核心机制。实现中 L1 正则化被完全关闭。

但这并不意味着模型没有在压缩。信息瓶颈 (64→32→16) 本身就是一种强制压缩——通过维度缩减而非稀疏惩罚。这是 INS-019 的核心洞察："hd=64 的物理瓶颈 > lambda_s 的正则化"。

所以实际的脱节不是"没有压缩"，而是"显式压缩 (L1) 有害，隐式压缩 (维度缩减) 有效"。理论没有区分这两者，但实证明确选择了后者。

**这个脱节是可接受的**。L1=0 不违反压缩哲学，只是选择了不同的压缩实现。

### 脱节 #2: "保留高维拓扑" vs 单层注意力 — **严重程度: 高**

理论说高维拓扑结构是关键，1D 展平会产生 O(sqrt(N)) 的信息损失。当前实现保留了 2D 结构 (好)，但只有 1 层注意力 (不够)。

一层注意力的感受野是一个 (32, 10) 窗口。在这个窗口内，模型能做的是：对 320 个 token 做全局注意力，找出哪些 (时间, 深度) 位置之间有关联。这对于检测局部的 LOB 结构 (如某个价位的阻力墙) 可能足够。

但主力行为的 *层级性* (从微观执行到宏观建仓) 需要多尺度的信息提取。一层注意力只能做一次特征变换。如果把 FWT 类比为 CNN，这相当于用一个 kernel 的 CNN 做图像分类。可以但效率极低。

### 脱节 #3: "有限窗口捕获" vs 5 个窗口零通信 — **最严重。这是硬天花板。**

这是理论与实现之间最大的裂隙。

理论说"有限窗口"是必要的 (避免 O(N^2) 全局注意力)，但窗口之间零通信不是理论的要求——它只是当前实现的简化。

实际影响：如果一个主力在 50 bars 内建仓 (跨越 2 个 32-bar 窗口)，当前模型只能看到两个独立的"半个建仓"模式，然后由 AttentionPooling 做加权平均。模型无法知道这两个"半个建仓"是同一个连续行为。

**弥合实验设计**: 

最小改动方案 (不需要重写架构)：

**Overlapping Windows**: stride < window_size_t 的窗口分割。例如 window_t=32, stride=16，这样相邻窗口有 50% 重叠。每个 token 出现在 2 个窗口中，间接建立了跨窗口连接。

实现成本：修改 `FiniteWindowTopologicalAttention.forward()` 中的窗口分割逻辑。参数量不变。计算量翻倍 (2x 窗口数)。训练时间约 +50%。

```python
# 当前: 不重叠
# x_win = x_nd.view(B, T//wt, wt, S//ws, ws, D)

# 修改: 50% 重叠滑动窗口
# stride_t = wt // 2
# 用 unfold 而非 view
x_unfold = x_nd.unfold(1, wt, stride_t)  # [B, num_win_t, S, D, wt]
```

这是最低成本的跨窗口通信实现。如果有效，再考虑 Swin-style shifted window 或多层架构。

---

## 附录: 审计发现优先级排序

| 优先级 | 发现 | 预期影响 | 成本 |
|-------|------|---------|------|
| P0 | Gradient accumulation (batch 256→4096) | Rank IC +0.005~+0.015 | 0h (代码改动) |
| P0 | MLP baseline | 决定项目方向 | 6h T4 |
| P1 | hd=128 重测 | Rank IC +0.003~+0.010 | 15h T4 |
| P1 | SWA/EMA 权重平均 | 稳定性 +、Rank IC +0.002~+0.005 | 0h (代码改动) |
| P1 | 验证集 embargo gap | 确认信号真实性 | 0h (代码改动) |
| P2 | 跨窗口重叠 (overlapping windows) | Rank IC +0.005~+0.010 | 15h T4 |
| P2 | Tail-Weighted IC Loss | D9-D0 提升、交易相关性提升 | 10h T4 |
| P3 | delta 经验测量 | 验证物理假设 | 0h (分析) |
| P3 | mask_prob + dropout 搜索 | 稳定性 +、Rank IC +/-0.002 | 10h T4 |

---

## 最终判断

Phase 13 的 Rank IC=0.029 是这个项目 14 个 Phase 中第一个可信的正信号。管线终于修对了——IC Loss、Pre-LN 残差、AttentionPooling、lambda_s=0 的组合第一次让模型能正常学习。

但 0.029 几乎肯定**不是**当前管线的极限，而是被以下因素压制后的值：
1. batch=256 的梯度噪声 (信噪比 0.16)
2. 最优 checkpoint 的选择偏差 (E9 是 15 个 epoch 中的幸运最高点)
3. hd=64 的瓶颈维度可能过窄 (从未在修复后管线上测试)
4. 单层注意力 + 零跨窗口通信限制了感受野

修复前两项不需要任何 GPU 成本 (gradient accumulation + SWA 只需代码改动)。如果这两项将 Rank IC 推到 0.04-0.05，项目的经济可行性会显著改善。

理论与实现之间最大的裂隙是跨窗口通信的缺失。OMEGA Manifesto 的核心假设是主力行为跨越多个时间尺度，但模型的感受野被硬切成了 0.64 天的碎片。这不是理论的要求，只是实现的简化，应该是下一阶段的首要任务。

最后一个不舒服的问题：**没有 MLP baseline，我们不知道 0.029 中有多少来自 OMEGA 的物理先验**。这是一个 6 小时就能回答的问题，但它决定了整个项目未来的研发方向。如果 MLP 也能到 0.025，那么所有的 SRL/FWT/拓扑理论都只贡献了 0.004。这种情况下，最有效的策略不是优化模型架构，而是优化特征工程和数据质量。

---

*End of Independent Audit Report*
*Claude Opus 4.6, 2026-04-06*
