# Omega-TIB 独立审计报告

作者：Codex GPT-5.4  
日期：2026-04-06  
审计立场：以 ML 工程、架构表达力、训练科学、评估契约一致性为主视角。

---

## 0. 先给结论

我的主判断很直接：

**OMEGA 的理论没有被证伪，当前实现也绝没有逼近这套理论的上限。真正的瓶颈首先不是“理论不够强”，而是实现还没有把理论里最关键的三件事做完：**

1. **没有把“日历日截面排序”真正落到训练选择与正式评估上。**
2. **没有把“跨窗口拓扑连续性”真正落到模型表达力上。**
3. **没有用一个足够强但足够朴素的 baseline 去测出 Omega 架构到底贡献了多少。**

Phase 13 的 `Rank IC=+0.0292` 不是假的，它至少说明当前管线终于从“系统性反信号/方差坍缩”爬到了“弱正信号”。但它也**不是**你现在就可以拿来宣判“理论成立且 hd=64 足够、单层窗口足够、loss 已最优”的结果。因为当前成功建立在一套**近似契约**上：

- 训练：`batch-level Pearson IC`
- best checkpoint 选择：`global Spearman`
- post-flight：`v3 shards 上的 global decile analysis`
- 真实交易逻辑与 spec 承诺：`calendar per-date cross-sectional`

这四件事现在没有对齐。你现在看到的是“近似目标下的正信号”，不是“理论目标下的最终能力”。

更尖锐一点说：**项目现在最危险的不是模型太弱，而是团队已经开始把一个近似指标上的局部成功，提前叙述成了架构真理。**

---

## 1. 三类事实

## 1.1 已被数据证明

- **IC Loss 明显优于此前几轮 MSE/Huber/Softmax 变体。** 在 `Std≈189.6BP, Kurtosis≈2006` 的目标分布上，点对点误差目标会退化成条件均值/波动率排序器；Phase 13 恢复 IC Loss 后首次得到稳定正向 Rank IC。
- **AttentionPooling + Pre-LN residual 是真实修复，不是 cosmetic patch。** 这组改动把模型从“均值池化摧毁时空结构 + RPB 梯度近死”拉回可训练区间。
- **显式 L1/MDL 惩罚在当前数据分布下是反信号。** 这不是风格判断，是 6 个 phase 的一致经验事实。
- **SRL 至少对 `V_D/σ_D` 这两个显式宏观锚点做了足够压缩。** Phase 14 Step 2 中，旁路把原始 `V_D, σ_D` 再直接拼回去，效果更差，不是更好。
- **Phase 13 至少学到了“弱但真实”的排序信息，不再是纯噪声发生器。** 15 个 epoch 的验证 Rank IC 全为正，这和之前“直接反信号”完全不是一个状态。

## 1.2 已被数据否定

- **Phase 6 及其衍生出的 hd=64 神话，不再是有效证据。** INS-072 已经把这条历史链整体作废；Phase 14 oracle retest 也只给出 `Rank IC=0.0023`。
- **“全局排序指标足以代表日内/逐日截面能力”这个假设被否定过，而且应该被持续视为高危。** Phase 7 历史报告已经明确记录过：prediction level 会跨日期漂移，global pooling 会把 temporal drift 混成“排序能力”。
- **“压缩即智能 = 显式 L1 惩罚”这个实现路径被否定。** 当前数据告诉你，正确的压缩来自结构瓶颈、物理变换和 inductive bias，不来自 loss 里硬塞一个 L1 税。

## 1.3 从未测试过

- 修复后管线上的 `hd=64 vs 128 vs 256`
- 单层 FWT vs 两层/shifted-window
- 跨窗口通信
- 真正的 `per-date` checkpoint selection 和正式 post-flight
- 简单 MLP baseline
- `δ != 0.5` 的 SRL 指数实验
- 轻量但有针对性的正则化（不是 blanket dropout/WD）
- EMA / SWA / 更稳定的权重平均

**所以现在最不该做的事，就是把未测试过的部分叙述成“已经接近理论极限”。**

---

## 2. 选择题（Q1-Q6）

## Q1. `hd=64` 是否必须在 Phase 13 管线上重新测试？

**判定：是。至少必须重测 `hd=128`；`hd=256` 值得做一次 ceiling check。**

证据很简单：

- `hd=64` 的核心正面证据来自 Phase 6 HPO，但这条历史链已经被 INS-072 作废。
- Phase 14 oracle retest 把 Phase 6 T29 打回 `Rank IC=0.0023`，说明旧容量结论不能再引用。
- 当前可信管线（IC Loss + Pre-LN + AttentionPooling）里，**只跑过 `hd=64`，没有任何有效对照。**
- 作废前的旧 HPO 里，`hd=64` 和 `hd=128` 差距本来就只有 `0.0006`，这反而更说明**在修复后管线里必须重测**，否则你根本不知道现在的天花板是架构限制、优化噪声，还是单纯 width 不够。

我的工程判断是：

- `hd=128` 是必须项，因为它是最小代价的“容量是否真不足”检验。
- `hd=256` 不是必须做完整 sweep，但至少应该做一次 smoke/full-run ceiling check。原因不是我相信 256 一定更好，而是你现在缺少一个“容量已经不构成限制”的证据点。

现在不重测，后面所有“Karpathy 极简胜利”的叙述都站不住。

---

## Q2. `batch=256` 的 IC 梯度信噪比是否 `< 1`？

**判定：是。按相关系数估计误差的近似，`B=256` 时信噪比约 `0.46`，明显小于 1。**

用底稿自己给的近似就够了。相关系数的标准误差可近似为：

`SE(r) ≈ 1 / sqrt(N - 3)`，粗略也可写成 `1 / sqrt(N)`。

取当前成功信号 `Rank IC ≈ 0.0292`：

- `B=256`  
  `SE ≈ 1/sqrt(253) = 0.0629`  
  `SNR ≈ 0.0292 / 0.0629 = 0.46`

- `B=1024`  
  `SE ≈ 1/sqrt(1021) = 0.0313`  
  `SNR ≈ 0.0292 / 0.0313 = 0.93`

- `B=2048`  
  `SE ≈ 1/sqrt(2045) = 0.0221`  
  `SNR ≈ 0.0292 / 0.0221 = 1.32`

补充两个阈值：

- 要让 `SNR ≈ 1`，需要 `B ≈ 1 / 0.0292^2 ≈ 1172`
- 要让 `SNR ≈ 2`，需要 `B ≈ 4688`

所以结论非常明确：

- `256` 对 IC 类目标来说偏小，至少从估计噪声角度看，梯度是在高噪音区工作。
- `1024` 只是勉强到边界。
- `2048` 才开始进入“信号略高于噪声”的区域。

严格地说，这不是参数梯度的精确 SNR，而是**目标估计器本身**的 SNR proxy。但对当前项目足够有指导意义：**你现在的优化不是在清晰地追一个信号，而是在噪声里抠一个相关性。**

---

## Q3. SRL 压缩是否充分？

**判定：是。就 `V_D/σ_D` 这两个显式宏观量而言，现有证据支持“SRL 已经提取得够干净”。**

证据来自 Phase 14 Step 2：

- Arm A: 仅 `LOB(5) + q_metaorder`，`Best Rank IC = +0.0122`
- Arm B: 在 Arm A 基础上再直通 `log1p(V_D), log1p(σ_D)`，`Best Rank IC = +0.0064`

如果 SRL 丢掉了这两个量里的可用边际信息，Arm B 至少应该持平，最好应该更强。结果它更差。

所以我会给出一个**边界清晰**的结论：

- **是，SRL 对“把 `V_D/σ_D` 作为额外原始通道直拼进去是否有增量”这道题，答案是没有。**
- **但这不等于 SRL 的整个物理前端已经“数学最优”。** 它没有回答 `δ` 是否正确，也没有回答 `c_i` 标定是否在所有运行环境下都真实生效。

换句话说，**SRL 的信息压缩方向大概率是对的，但 SRL 的参数化细节仍然值得实验。**

---

## Q4. `lambda_s=0` 是否正确？

**判定：是。对这份数据分布来说，L1 惩罚是反信号。**

这不是“我更喜欢不正则化”，而是你们已经做了足够多的反证：

- Phase 3：`λ=1e-3`，直接杀信号
- Phase 11c：`λ=1e-3`，脑死亡
- Phase 11d：`1e-4 vs 1e-5` 无本质改善
- Phase 12：L1 从 `2.09 → 1.16` 的同时，`D9-D0` 从 `4.48 → 1.28`
- Phase 13：`λ=0` 首次成功

### 为什么在肥尾分布下，L1 会专门绞杀尾部信号？

关键不是“肥尾导致 L1 数学上直接惩罚大 target”，而是：

**尾部 alpha 在模型内部通常对应“稀疏、间歇触发、幅度较大”的 detector；而 L1 的软阈值更新会在大多数无信号 batch 上持续把这些 detector 往 0 推。**

对任意参数 `w`，L1 的一步近端更新是：

`w_{t+1} = sign(w_t - ηg_t) * max(|w_t - ηg_t| - ηλ, 0)`

这里有个致命点：

- 对 bulk 样本，尾部 detector 的梯度 `g_t` 近似为 0
- 对 rare tail 样本，`g_t` 才会突然非零
- 但 L1 shrinkage `ηλ` 是**每一步都在扣**

于是发生什么：

- 大多数 batch 没有足够的 tail 信息时，参数只会被往 0 收缩
- 少数 batch 刚把 detector 拉起来，后面又会在一串无信号 batch 中被重新削掉

当前项目里这个效应更严重，因为：

- target 极度肥尾，`kurtosis≈2006`
- batch 只有 256，稀有事件在 batch 内占比本来就低
- 优化目标是 IC，单步有效梯度已经不大

因此显式 L1 不是“帮助模型压缩噪音”，而是在当前 regime 下**优先杀死稀疏 tail detector**。  

真正有用的压缩来自：

- SRL 物理变换
- 结构瓶颈 `64→32→16`
- 有限窗口注意力
- 小模型本身的低容量偏置

所以这里应该把理论叙述改掉：**不是“放弃压缩”，而是“放弃错误位置上的显式压缩”。**

---

## Q5. MLP baseline 是否应在进一步架构优化前执行？

**判定：是，而且优先级非常高。**

理由没有花活：

- 现在没有一个“同输入、同训练配方、去掉 SRL/拓扑 inductive bias”的 baseline。
- 没有 baseline，你就不知道当前 `+0.029` 里到底有多少来自：
  - FRT 这种 feature engineering
  - batch-level IC 这个训练目标
  - 数据分割与评估近似
  - Omega 的 SRL + 拓扑架构本身

如果一个 2 层 MLP 用同样的 FRT 输入、同样的 IC loss、同样的 per-date evaluator，轻轻松松做到 `0.025`，那你当前整个“物理 + 拓扑”大故事的净贡献只有 `0.004` 左右。这个问题必须尽早被问清楚。

我会把它称为**归因地基**。地基不打，后面所有“shifted window 提升了 30%”“hd=64 是物理窄门”都可能只是修辞。

---

## Q6. Phase 13 训练曲线 `E9→E14` 是什么状态？

**判定：C，收敛后的方差。不是典型过拟合。**

我的判据：

- 15 个 epoch 的 `Val Rank IC` **全部为正**。这和典型过拟合不一样；过拟合通常会出现持续性向下漂移，甚至回到零或负值。
- `E10-E14` 落在 `0.0124 ~ 0.0209`，是一个正值平台，不是断崖。
- `E9` 是局部最好点，但 `E14` 仍有 `0.0180`，说明模型没有“学坏”，而是在一个相对平坦的 basin 里晃动。

所以我不会把它叫做 A（过拟合），我会叫它：

**“已经收敛到一个弱正信号平台，但 checkpoint 选择依赖单次幸运峰值，且没有 patience-based early stopping / weight averaging 来稳定最优点。”**

这里有两层噪声：

1. 优化噪声：OneCycle 收尾时参数还在平坦盆地里漂
2. 评估噪声：当前用的是 global Spearman，不是 per-date 平均 Rank IC

所以 E9 更像“平台上的最好抽样点”，不是“之后立刻开始过拟合”的分水岭。

---

## 3. 开放题（Q7-Q12）

## Q7. 单层注意力 + 零跨窗口通信，是否是 `Rank IC=0.029` 的硬天花板？

**我的判断：它大概率是“当前实现族”的硬天花板，但不是 OMEGA 理论的硬天花板。**

原因非常直接：当前 160 bar 被切成 5 个 `32×10` 窗口，窗口之间完全隔离。  

这意味着模型**物理上不可能**表达下面这类模式：

- 机构在窗口 1 末端开始吸筹
- 窗口 2 延续
- 窗口 3 拉抬确认

在当前模型里，这不是“很难学”，而是**根本没有路径可学**。

### 我对 shifted-window 两层版的预期

如果做一个标准的两层 Swin 风格：

- Block 1: regular window
- Block 2: temporal shift 16 bars

那么有效感受野会从“绝对 32 bars 隔离”变成“相邻窗口可组合”，至少能看到 64 bars 级别的连续结构。

我的 lift 预期：

- **保守：`+0.003 ~ +0.005` 绝对 Rank IC**
- **中性：`+0.005 ~ +0.008`**
- **乐观：`+0.010 ~ +0.015`**

为什么我不报更大：

- 它仍然不是 full global attention
- 数据仍然极噪
- 评估若改成 per-date，基线本身可能先变

为什么我也不报更小：

- 当前限制是“表达不到”，不是“表达了但学不会”
- 这是比 width 更硬的约束
- 项目理论里最核心的那句“多窗/多期协同”目前根本没进模型

我预期这个改动带来的收益，**更可能先体现在 per-date monotonicity、top-decile hit-rate、稳定性上，而不一定先在 Pearson IC 上显著爆发。**

---

## Q8. IC Loss 在 `kurtosis=2006` 下是否最优？

**我的判断：不是。它是一个“把项目从死亡线拉回来”的正确目标，但不是与你们 Taleb 式叙事最一致的最终目标。**

### 根本矛盾在哪里？

IC Loss 的价值在于：

- 尺度不敏感
- 直接优化排序
- 能在高方差环境里避开 MSE 的均值坍缩

但它的局限也同样明显：

- 它对每个样本基本等权
- 它不会明确奖励“抓住正向极端尾部”
- 它会把“把 +500BP 排对”和“把 +2BP 排对”当成同类排序改进

这和“低胜率 + 尾部暴利”的交易哲学并不一致。

你们现在的情况是：

- **用 IC Loss 学到了一个温和的排序器**
- **但交易哲学想要的是一个极右尾识别器**

这两者不是完全冲突，但也绝对不是完全一致。

### 我建议的替代：`per-date tail-weighted IC + positive-tail pairwise`

不是直接扔掉 IC，而是把它升级成**更贴近交易目标的加权版本**。

核心思路：

1. **按日期分组**
2. **对正向尾部样本加权**
3. **额外加入“正向尾部必须排在普通样本前面”的 pairwise ranking 项**

一个可直接实现的版本：

```python
import torch

def tail_weighted_date_ic_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    date_id: torch.Tensor,
    q: float = 0.9,
    alpha: float = 4.0,
    beta: float = 0.3,
    tau: float = 1.0,
    eps: float = 1e-8,
):
    losses = []
    for d in torch.unique(date_id):
        m = (date_id == d)
        p = pred[m].float().view(-1)
        t = target[m].float().view(-1)
        if p.numel() < 16:
            continue

        q_hi = torch.quantile(t, q)
        q_mid = torch.quantile(t, 0.5)

        # 1) Tail-weighted IC
        tail = torch.relu(t - q_hi)
        w = 1.0 + alpha * tail / (tail.mean() + eps)
        w = w / (w.mean() + eps)

        p_c = p - (w * p).sum() / w.sum()
        t_c = t - (w * t).sum() / w.sum()
        cov = (w * p_c * t_c).sum() / w.sum()
        p_std = torch.sqrt((w * p_c.square()).sum() / w.sum() + eps)
        t_std = torch.sqrt((w * t_c.square()).sum() / w.sum() + eps)
        ic_term = -(cov / (p_std * t_std))

        # 2) Positive-tail pairwise term
        pos = t >= q_hi
        neg = t <= q_mid
        if pos.any() and neg.any():
            margin = (p[pos].unsqueeze(1) - p[neg].unsqueeze(0)) / tau
            pair_term = -torch.log(torch.sigmoid(margin) + eps).mean()
        else:
            pair_term = p.new_zeros(())

        losses.append(ic_term + beta * pair_term)

    if not losses:
        return pred.new_zeros((), requires_grad=True)
    return torch.stack(losses).mean()
```

我建议的实验顺序不是“一上来全替换”，而是：

1. 先把 **per-date evaluator** 修对
2. 在此基础上做 **weighted-date-IC** 小步替换
3. 再决定是否加 pairwise tail term

否则你会再次把“metric drift”和“loss 改进”缠在一起，没法归因。

---

## Q9. `24.6K` 参数，是极简胜利还是容量不足？

**我的判断：现在还不能盖棺定论。它证明了“局部模式可拟合”，没有证明“全任务容量充足”。**

为什么我不认为它已经证明“容量足够”：

- Crucible 只证明模型能过拟合 64 个样本到 `Pearson≈0.88`
- 这说明函数类不是线性的，也说明 local memorization 没问题
- 但**这不能证明它有足够的层级容量去表达“跨窗口、多阶段、低频长程”的主力行为**

当前 `24.6K` 的现实含义更像是：

- 它是一个很强的结构正则化器
- 它足以学习局部微观结构
- 但它未必足以同时承担：
  - 局部盘口几何
  - 窗内时间结构
  - 跨窗相位关系
  - 不同股票流动性 regime 的适配

更关键的是，当前瓶颈不一定是“参数数目”本身，而是**参数被组织的方式太浅**：

- 单层 attention
- 零跨窗通信
- 16 维最终瓶颈

所以我不会说“24.6K 太小”，我会说：

**在现有架构下，24.6K 更多像是“极小但偏盲”的模型，而不是“极小且足够”的模型。**

### 怎么区分“成功过滤噪声”和“过度压缩信号”？

做三个对照就够：

1. `hd=64 vs hd=128`，其余全固定，按正确 per-date 指标比较  
   如果 train 和 val 都上升，说明原来欠容量。

2. `single-window vs shifted-window`，保持 hd 不变  
   如果 shifted-window 提升大于单纯加宽，说明问题是表达层级，不是 width。

3. `Omega vs MLP baseline`  
   如果 MLP 接近 Omega，说明大量“胜利”来自输入变换和优化目标，不来自拓扑结构。

---

## Q10. SRL 的 `δ=0.5` 在 A 股是否成立？

**我的判断：值得测，而且成本不高，但必须连同 `c_i` 重标定一起测。**

当前公式是：

`Q_hidden ∝ (|ΔP| / (cσ_D))^(1/δ) * V_D`

所以：

- 若 `δ=0.4`，则 `1/δ = 2.5`
- 若 `δ=0.6`，则 `1/δ ≈ 1.667`

这会怎样改变 `q_metaorder`？

### 若 `δ=0.4`

- 小冲击对应的 `q` 会更小
- 大冲击对应的 `q` 会被更强地放大
- 分布会更尖、更稀疏、更肥尾

### 若 `δ=0.6`

- 大冲击被压平
- 中小冲击被相对抬高
- 分布更平、更密、中段更厚

由于后面还会经过 `clamp + symlog`，它不一定表现为“数值爆炸”，但会明显改变：

- 样本间排序
- tail vs middle 的相对间距
- SRL 前端对 rare event 的强调程度

### 为什么这在 A 股值得测？

因为 A 股与原始 SRL 实证市场不同：

- T+1
- 涨跌停
- 散户占比更高
- 机构执行与冲击结构不同

### 成本如何？

这个实验比你想象的便宜。仓库里已经有 `tools/omega_srl_friction_calibrator.py`，重标定 `c_i` 的流程是现成的。

一个务实方案：

1. 候选 `δ ∈ {0.4, 0.5, 0.6}`
2. 每个 `δ` 重新标定 `c_i`
3. 每个候选做 2-3 epoch smoke
4. 只让最好的一组进 full run

GPU 成本大概就是几个 smoke run，加上一条 full run。  
我会把它归为**中优先级**：值得做，但排在 `per-date evaluator / shifted-window / MLP baseline` 之后。

---

## Q11. 正则化全面缺失，是设计选择还是历史遗忘？

**我的判断：`lambda_s=0` 是设计选择；`dropout/WD/EMA` 的缺失更像历史遗忘或未完成工程化。**

先区分：

- `lambda_s=0`：有充分数据支持，不是遗漏
- `dropout=0`、`weight_decay≈0`、`EMA/SWA 缺失`：大多没有经过系统测试

### 我对 `dropout=0.05, WD=0.01` 的预期

如果你今天直接把它们 blanket 打上去，我的预期是：**大概率小负面，少数情况下无效，很难是正面。**

原因：

- 模型本来就极小
- 数据量近 `10M` 样本，经典意义上的“参数过多导致统计过拟合”不是主要矛盾
- 当前主要矛盾更像是**弱信号 + noisy objective + 表达受限**

在这种设置里：

- `dropout=0.05` 会破坏 rare co-activation，对 tail detector 不友好
- `WD=0.01` 对这么小的模型来说偏重，尤其会伤到 `qkv / RPB / attention_pool`

### 但我不主张“完全不要 regularization”

我主张的是：

- **不要用错 regularization。**

更合理的候选是：

- `EMA` 或 `SWA`：稳定平台期 checkpoint，不是强行压小权重
- `AdamW weight_decay=1e-4 ~ 1e-3`，且**排除** `LayerNorm/bias/RPB/W_pool`
- 不要 blanket dropout，若试也先在 bottleneck 后小范围 `0.02~0.05`

所以答案不是“正则化完全不需要”，而是：

**这个项目当前缺的不是更强 shrinkage，而是更稳的估计和更对口的结构先验。**

---

## Q12. `Rank IC=0.029` 在 A 股 L1 tick + T+1 隔夜语境下处于什么水平？

先说结论：

**作为“研究信号”，它不差。作为“可稳定覆盖 25BP 成本的生产信号”，它明显不够。**

### 与公开研究相比

这里要诚实：**公开文献里和你完全同口径的 apples-to-apples benchmark 很少。**

- 大量 LOB 论文汇报的是分类准确率、AUC、mid-price direction，不是日历日截面 Rank IC。
- LOB 文献综述本身就强调：即便很多模型在预测指标上很好，**稳定交易利润在现实成本下仍然不保证成立。**  
  参考：Zaznov et al., 2022, *Predicting Stock Price Changes Based on the Limit Order Book: A Survey*  
  DOI: https://doi.org/10.3390/math10081234
- 关于中国股票市场，Leippold, Wang, Zhou (JFE 2022) 明确指出中国市场存在可预测性，流动性特征尤其重要，但他们研究的是更广义的 return prediction，不是你这种 A 股 L1 tick + SRL + T+1 约束的微观架构。  
  DOI: https://doi.org/10.1016/j.jfineco.2021.08.017

所以我的位置判断是：

- **在“研究上是否有 alpha 痕迹”这个问题上，`0.029` 是有内容的。**
- **在“是否足以支撑一个高换手、T+1 隔夜、25BP round-trip 成本的策略”这个问题上，`0.029` 明显偏低。**

### `D9-D0 = 7BP` vs 成本 `25BP` 说明什么？

说明当前信号的横截面分离度只有成本门槛的 **28%** 左右。

最朴素的解释就是：

- 你能把好股票和坏股票稍微分开
- 但分开的幅度**远远不够**支付交易摩擦

### 需要多少 IC 才可能覆盖成本？

用当前点位做一个局部线性近似：

- 当前：`Rank IC = 0.0292` 对应 `D9-D0 = 7.00 BP`
- 经验斜率：`7.00 / 0.0292 ≈ 239.7 BP / IC-unit`

若要仅在 spread 意义上覆盖 `25 BP` 成本，则需要：

`IC_required ≈ 25 / 239.7 ≈ 0.104`

也就是说，**大概需要 `Rank IC ≈ 0.10 ~ 0.11` 这个量级，当前才勉强摸到“spread 覆盖成本”的门槛。**

现实里通常还要更高，因为：

- 成本并不严格线性
- 你不会真做满 D9-D0 long-short 无摩擦组合
- top-50 集中持仓会放大冲击
- corrected per-date metric 很可能低于当前 global proxy

如果从 long-only 视角看，当前 D9 的 raw mean 也只有 `8.85BP`，距离 `25BP` 仍差得很远。

所以我的结论非常朴素：

**`0.029` 是“值得继续做”的 alpha 研究结果，不是“已经可交易”的生产结果。**

---

## 4. 深度洞察（Q13-Q15）

## Q13. 这个项目最大的盲区是什么？

**最大的盲区不是数学，不是 SRL，不是 L1；而是“你们一直没有把要优化的东西、要验证的东西、要交易的东西严格对齐”。**

更具体地说，是三层契约漂移：

1. **训练目标**是 batch-level Pearson IC
2. **checkpoint 选择**是 global Spearman
3. **交易叙事**却是 calendar per-date cross-sectional alpha

这三者不是一回事。

这会带来一个非常坏的后果：

你每做一次架构改动，看到指标变好，就会本能地把它解释成“更接近主力拓扑”；  
但实际上它也可能只是：

- 更擅长做 global volatility sorting
- 更适应 batch-mixed pseudo cross-section
- 更擅长输出稳定的 rank proxy，而不是可交易尾部

这就是为什么我前面一直强调：**你们现在最缺的不是一个更聪明的 block，而是一条更诚实的测量链。**

还有一个次级盲区，同样严重：

**你们还没有做一个足够简单的 baseline。**

这导致项目在叙事上很容易把“FRT + data pipeline + IC loss”带来的收益，误记成“Omega 拓扑架构”的收益。

---

## Q14. 如果我接手项目，20 小时 T4 预算下的前 3 个实验是什么？

先说明：**按“预期 Rank IC 提升”排序，我会列 3 个主实验。**  
但在正式开跑前，我会先插一个不计排名的 **MLP baseline gate**，因为它只要 1-2 小时，却能极大降低后续实验解释歧义。

### Gate 0. MLP baseline（不计入排序，但我会先跑）

假设：当前很多收益可能来自 FRT + IC loss，而不是 Omega 拓扑结构。  
设计：同输入、同 batch IC、同优化器、同 per-date evaluator，换成一个 2-3 层 MLP / token-wise MLP pooling baseline。  
成本：`1-2h T4`。  
若确认：说明 Omega 的净架构增益可能很小，后续应优先做表达力而非继续打磨物理叙事。  
若否定：说明 SRL+拓扑确实有净增量，后续架构优化值得加码。

### 1. 两层 shifted-window Omega-TIB（最高优先级）

假设：当前硬瓶颈是零跨窗通信，不是 width。  
设计：

- 保持 `hd=64`
- 两个 FWT block
- Block 1 正常窗口
- Block 2 时间轴 shift 16 bars
- 其余训练配方尽量不动
- **必须**用 per-date evaluator 选 best checkpoint

成本：  

- 8 epoch smoke：约 `6-7h T4`
- 若 smoke 明显领先，再补 full run

若确认：说明 OMEGA 理论里“跨窗连续拓扑”确实是核心缺环。  
若否定：说明当前信号更偏短程执行切片，不是多窗连续建仓；下一步应优先优化 objective 或 baseline，而不是继续堆窗口拓扑。

我对提升的预期：**`+0.004 ~ +0.010` 绝对 Rank IC**

### 2. 提升有效 batch 到 1024（梯度累积）+ EMA

假设：当前主要被 IC 估计噪声卡住。  
设计：

- 微批次仍用 256，梯度累积 4 次
- optimizer step 数按等样本量重算
- 加一个简单 EMA，只用于验证和 best checkpoint
- 其余不动

成本：`5-6h T4` 做 8 epoch smoke 足够判断。

若确认：说明当前不是模型不会学，而是 batch IC 的统计噪声太高。  
若否定：说明 noise 不是第一瓶颈，表达能力或目标错配更重要。

我对提升的预期：**`+0.003 ~ +0.007`**

### 3. `hd=128` 有效管线复测

假设：`hd=64` 只是历史偶然被神化，当前真实最佳宽度未定。  
设计：

- 单层当前架构不变
- 只改 `hd=64 -> 128`
- 正确 per-date evaluator
- 8 epoch smoke

成本：`6-7h T4`

若确认：说明当前模型确实欠容量，后续“极简即最优”的叙事必须收缩。  
若否定：说明 width 不是主矛盾，进一步投入应转向层级/窗口通信。

我对提升的预期：**`0 ~ +0.005`**

### 为什么我没把“新 loss”排进前三？

不是因为我不重视 loss，而是因为：

- 现在 metric contract 还没落稳
- 先改 loss，归因会重新污染

我的顺序是：

1. 把 evaluator 修对
2. 测 baseline
3. 先打通表达力和优化信噪比
4. 再上 tail-aware objective

---

## Q15. OMEGA Manifesto 的理论与当前实现之间，最大的脱节是什么？

有三条脱节，而且严重程度不同。

### 脱节 1：理论说“保留高维拓扑”，实现只有单层局部窗口

这是**最严重的架构脱节**。

理论讲的是：

- 主力行为跨时间、跨空间、跨标的协同
- 一维压扁会撕裂拓扑

但当前实现只做到了：

- 保留 2D 张量
- 在单个局部窗口里做一次 attention

它没有做到：

- 多层级组合
- 跨窗口信息流
- 远程时序依赖

所以现在的模型更像：

**“二维局部模式提取器”**

而不是：

**“多尺度主力拓扑建模器”**

### 脱节 2：理论说“压缩即智能”，实现却是“显式 L1 被禁用”

这是叙事脱节，不一定是技术错误。

当前数据已经证明显式 L1 不该用。那就意味着理论实现方式必须改写：

- 压缩不再由 loss 里的 `λ_s ||z||_1` 实现
- 压缩改由 SRL、结构瓶颈、小模型、有限窗口、正确目标函数共同实现

这不是背叛理论，而是**把理论从错误实现里救出来**。

### 脱节 3：理论说“最终目标是日历日截面排序”，实现还在用 global proxy 选模型

这是**最严重的评估脱节**。

训练可以近似。  
评估不能长期近似。  

一旦评估继续近似，团队就会持续高估某些改动的真实交易价值。

### 哪个脱节最严重地限制了理论实现？

如果只问**模型能力**，我选：

**脱节 1：零跨窗通信。**

因为这是真正的物理表达限制。你就算换更好的 loss、调更大的 batch，只要跨窗关系进不了模型，理论里最核心的那部分都只是口号。

如果问**项目决策质量**，我选：

**脱节 3：评估契约漂移。**

因为它会让你误读任何实验结果。

### 如何设计实验去弥合最严重脱节？

我会这样做：

1. 用 ETL v4 / date-aware loader，把 `per-date` evaluator 真正落地  
   不再用 global Spearman 选 best checkpoint。

2. 在此 evaluator 上做单变量架构对照：
   - Baseline: 当前单层窗口
   - Variant A: 两层 shifted-window
   - Variant B: 仅加宽 `hd=128`
   - Variant C: MLP baseline

3. 所有实验统一：
   - 同数据
   - 同 batch 样本数
   - 同 optimizer/scheduler
   - 同 post-flight 指标

这样你才有资格回答：

- 理论有没有抓到东西
- 当前瓶颈是不是跨窗
- 24.6K 到底是胜利还是束缚

---

## 5. 最终裁决

我的最终裁决可以压缩成三句话：

**第一，Phase 13 证明的是“管线终于能产出弱正信号”，不是“OMEGA 理论已经被充分实现”。**

**第二，当前最可能限制上限的不是 SRL，不是 `lambda_s=0`，甚至不一定是 `hd=64`；而是“单层局部窗口 + 零跨窗通信 + 近似评估契约”这组三连。**

**第三，如果现在就把 `Rank IC=0.029` 解释成这套理论的极限，那是过早收官。你们离真正公平地审判这套理论，还差一条正确的 evaluator、一条 MLP baseline，以及一次跨窗口实验。**

换成更工程化的话：

- **理论还没输。**
- **实现也还没赢。**
- **现在真正该做的是把测量链、baseline 和表达力补齐，而不是继续神化现有成功。**

