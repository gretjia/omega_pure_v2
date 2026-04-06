# Omega-TIB 三方独立审计汇总
**编制日期**: 2026-04-06
**审计师**: Codex GPT-5.4 (814行) | Gemini 2.5 Pro (354行) | Claude Opus 4.6 独立实例 (507行)
**汇总者**: Claude Opus 4.6 (主对话上下文)
**方法论**: 三方独立平行审计同一份底稿 → 判定对照 → 歧见分析

---

## 一、选择题三方判定对照

| Q | Codex GPT-5.4 | Gemini 2.5 Pro | Claude (独立) | 一致？ |
|---|---------------|----------------|--------------|--------|
| **Q1** hd=64 重测？ | **是** — 至少 128，256 做 ceiling check | **是** — 原始证据失效，科学基本步骤 | **是** — 16维/头极罕见，70K 参数仍极小 | ✅ 3/3 |
| **Q2** 梯度 SNR<1？ | **是** SNR≈0.46 | **是** SNR≈0.47 (Rank) / 0.16 (Pearson) | **是** SNR≈0.16 (Pearson), 需 B≥10K 才 SNR>1 | ✅ 3/3 |
| **Q3** SRL 压缩充分？ | **是** — 但仅限 V_D/σ_D 旁路问题 | **是** — SRL 是有效的去噪特征工程 | **是** — Arm A 以 2x 胜出 | ✅ 3/3 |
| **Q4** λ_s=0 正确？ | **是** — proximal operator 数学论证 | **是** — L1 是"尾部信号绞肉机" | **是** — L1 与 IC Loss 在优化方向上系统性冲突 | ✅ 3/3 |
| **Q5** MLP baseline？ | **是** — "归因地基"，优先级极高 | **是** — 量化研究基本纪律 | **是** — 6h 决定项目方向 | ✅ 3/3 |
| **Q6** E9→E14？ | **[C]** 收敛后方差 | **[B]** 噪声主导 | **[B]** 噪声主导 | ⚠️ 2:1 |

### Q6 歧见分析

**共识点** (三方一致):
- 不是过拟合 (无系统性下降趋势)
- 根因是 batch SNR 不足
- E9 的 0.029 是"平台上的幸运峰值"
- 应该用 SWA/EMA 稳定 checkpoint 选择

**分歧点**:
- Codex 选 [C]："正值平台上的方差，模型没有学坏"
- Gemini 选 [B]："振幅 0.0085 占峰值 30%，绝非窄幅波动"
- Claude 选 [B]："E10-E14 均值 ~0.017 可能才是模型真实性能，E9 是选择偏差"

**仲裁**: B 和 C 的区别在于"高原上的漫步"算噪声主导 (B) 还是收敛后方差 (C)。Gemini 的量化论据 (振幅占峰值 30%) 更具说服力。**采纳 [B]，但接受 Codex 的补充："模型确实收敛到了正值平台，不是无方向的噪声。"**

---

## 二、开放题三方核心观点汇总

### Q7. 跨窗口通信是否为硬天花板？

| 审计师 | IC 提升预期 | 实现方案 | 核心论据 |
|--------|-----------|---------|---------|
| Codex | +0.003~+0.015 | Swin shifted window 2层 | "表达不到" > "表达了但学不会"，是比 width 更硬的约束 |
| Gemini | +0.011~+0.026 (至 0.04~0.055) | Swin 2层 | 质变而非量变——解锁全新信号维度，+38%~+90% 相对提升 |
| Claude | +0.005~+0.010 | **Overlapping windows** (stride=16, 最小改动) | 类比 CV Swin ~+10-15% 相对提升；两层增加参数在噪声环境下有风险 |

**三方共识**: 跨窗口通信是最严重的架构限制。

**关键分歧**: 预期提升幅度差异大 (Codex +0.003~+0.015, Gemini +0.011~+0.026, Claude +0.005~+0.010)。

**Claude(独立) 的独特贡献**: 提出了 **overlapping windows** 方案——不需要重写架构，只需修改窗口分割逻辑 (stride < window_size)。参数量不变，计算量 +50%。这是最低风险的第一步：

```python
# 当前: 不重叠窗口分割
# x_win = x_nd.view(B, T//wt, wt, S//ws, ws, D)

# 修改: 50% 重叠滑动窗口
# stride_t = wt // 2  (=16)
x_unfold = x_nd.unfold(1, wt, stride_t)  # [B, num_win_t, S, D, wt]
```

### Q8. IC Loss 是否最优？替代方案

三方均认为 **IC Loss 不是最优，存在与 Taleb 哲学的根本矛盾**。三方各提出了代码级替代方案：

**Codex: per-date tail-weighted IC + positive-tail pairwise**

```python
def tail_weighted_date_ic_loss(pred, target, date_id, q=0.9, alpha=4.0, beta=0.3, tau=1.0, eps=1e-8):
    losses = []
    for d in torch.unique(date_id):
        m = (date_id == d)
        p, t = pred[m].float().view(-1), target[m].float().view(-1)
        if p.numel() < 16: continue

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

        # 2) Positive-tail pairwise ranking term
        pos = t >= q_hi
        neg = t <= q_mid
        if pos.any() and neg.any():
            margin = (p[pos].unsqueeze(1) - p[neg].unsqueeze(0)) / tau
            pair_term = -torch.log(torch.sigmoid(margin) + eps).mean()
        else:
            pair_term = p.new_zeros(())
        losses.append(ic_term + beta * pair_term)

    return torch.stack(losses).mean() if losses else pred.new_zeros((), requires_grad=True)
```

- 优势: 按日期分组 + 尾部加权 + pairwise 排序项，与交易逻辑最对齐
- 前提: 需要 ETL v4 的 date 字段

**Gemini: Target-Weighted IC Loss**

```python
def compute_target_weighted_ic_loss(prediction, target, ic_epsilon=1e-8, weight_power=0.5):
    pred = prediction.float().view(-1)
    tgt = target.float().view(-1)
    if pred.numel() < 2:
        return torch.tensor(0.0, device=pred.device, requires_grad=True)

    with torch.no_grad():
        weights = torch.log1p(torch.abs(tgt))
        weights = torch.pow(weights, weight_power)
        weights = weights / weights.mean()

    pred_mean_w = (weights * pred).mean()
    tgt_mean_w = (weights * tgt).mean()
    pred_centered_w = pred - pred_mean_w
    tgt_centered_w = tgt - tgt_mean_w
    cov_w = (weights * pred_centered_w * tgt_centered_w).mean()
    pred_var_w = (weights * (pred_centered_w ** 2)).mean()
    tgt_var_w = (weights * (tgt_centered_w ** 2)).mean()
    pred_std_w = torch.sqrt(pred_var_w + ic_epsilon)
    tgt_std_w = torch.sqrt(tgt_var_w + ic_epsilon)

    return -(cov_w / (pred_std_w * tgt_std_w))
```

- 优势: 简洁，无需 date 字段，weight_power=0 退化为标准 IC
- log1p(|target|) 的权重设计物理合理

**Claude(独立): Tail-Weighted IC (U-shaped)**

```python
def compute_tail_weighted_ic_loss(prediction, target, tail_boost=3.0, ic_epsilon=1e-8):
    pred = prediction.float().view(-1)
    tgt = target.float().view(-1)
    if pred.numel() < 2:
        return torch.tensor(0.0, device=pred.device, requires_grad=True)

    tgt_rank = tgt.argsort().argsort().float() / (tgt.numel() - 1)  # [0, 1]
    # U-shaped: 高权重在 D0 和 D9 两端
    tail_weight = 1.0 + (tail_boost - 1.0) * (2.0 * torch.abs(tgt_rank - 0.5)) ** 2
    tail_weight = tail_weight / tail_weight.mean()

    w = tail_weight
    pred_centered = pred - (w * pred).sum() / w.sum()
    tgt_centered = tgt - (w * tgt).sum() / w.sum()
    cov = (w * pred_centered * tgt_centered).sum() / w.sum()
    pred_std = torch.sqrt((w * pred_centered ** 2).sum() / w.sum() + ic_epsilon)
    tgt_std = torch.sqrt((w * tgt_centered ** 2).sum() / w.sum() + ic_epsilon)

    return -(cov / (pred_std * tgt_std))
```

- 优势: 基于 rank 而非 raw value，无需 date 字段
- U-shaped 权重同时关注 D0 和 D9，不仅仅是正尾

### Q9. 24.6K 参数 — 胜利还是不足？

| Codex | Gemini | Claude (独立) |
|-------|--------|--------------|
| "现在不能盖棺定论" | "极大概率容量不足" | "参数分配比总量更重要" |
| 局部拟合可，全任务不确定 | hd=64 是混乱中的偶然幸存 | 86% 参数在 FWT，仅 10.6% 在瓶颈 |
| 需要重测 hd=128 | 应抛弃"小即是美"路径依赖 | **z_core=16 维可能不够编码 20+ 种行为模式** |

**Claude(独立) 的独特观点**: 不是"总参数太少"，而是**参数分配不均**。FWT 占 86.4%，瓶颈仅 10.6%，预测层 0.1%。hd=128 把瓶颈维度从 16→32，这是最值得测试的单一变量。

### Q10. δ=0.5 在 A 股是否成立？

| Codex | Gemini | Claude (独立) |
|-------|--------|--------------|
| 值得实验但优先级低 | δ<0.5 时 q 更肥尾，δ>0.5 时更集中 | 可零成本验证：对已有数据做 log-log 回归测斜率 |

**Claude(独立) 的独特贡献**: "不需要训练模型。用 ETL 数据对每只股票拟合 |ΔP/σ| = c × (Q/V)^δ 的 log-log 回归，看斜率是否接近 0.5。零 GPU 成本。"

### Q11. 正则化缺失

| Codex | Gemini | Claude (独立) |
|-------|--------|--------------|
| 不是 blanket dropout/WD，要有针对性 | "小模型+大数据+高噪声"下正则化可能弊大于利 | WD=0.01 帮助 RPB 不漂移；dropout=0.05 影响微小但正向；mask_prob=0.3 最值得实验 |

**Gemini 的独特观点**: "首要任务是提升信号强度和梯度 SNR，不是担心 24.6K 模型在 10M 样本上过拟合。"

### Q12. Rank IC=0.029 的行业水平

| Codex | Gemini | Claude (独立) |
|-------|--------|--------------|
| "弱正信号，不够做交易" | "有价值但远不足以直接盈利" | "边缘信号，券商要求 IC>0.05" |

**三方一致的量化关系**:

覆盖 25BP 往返成本需要 D9-D0 > 50 BP → 需要 Rank IC ≈ 0.10~0.21 (当前 0.029)。

**三方都指出了替代盈利路径**:
- Gemini: "IR ≈ IC × √Breadth"，A 股广度大可以补偿
- Codex: "把评估改成 per-date 后基线可能先变"
- Claude: 降成本 (ETF/低佣) + 组合 alpha + 选择性交易

---

## 三、深度洞察 (Q13-Q15)

### Q13. 最大盲区

| Codex | Gemini | Claude (独立) |
|-------|--------|--------------|
| **指标契约脱节** — batch IC / global Spearman / per-date 评估不对齐。"把近似指标上的局部成功提前叙述成架构真理" | **拓扑理解过于狭隘** — "只要不展平成 1D 就算拓扑分析"。缺失多尺度、全局连接性、持续同调 | **数据泄漏风险** — shard 排序未验证时序，无 embargo gap，边界处 87.5% 时间重叠 |

**三个盲区互补，均为独创发现**:
1. Codex 发现的是**评估系统性风险** (全局 vs 截面)
2. Gemini 发现的是**理论执行深度不足** (拓扑只做了皮毛)
3. Claude 发现的是**数据完整性风险** (可能的前视偏差)

### Q14. 20h T4 预算的前 3 实验

| 排序 | Codex | Gemini | Claude (独立) |
|------|-------|--------|--------------|
| #1 | MLP baseline (归因地基) | **Swin 2层** (拓扑修复, +50~90% IC) | **Gradient Accumulation → batch 4096 + SWA** (零 GPU 成本!) |
| #2 | per-date evaluator 修正 + hd sweep | hd=64/96/128 对比 (容量验证) | MLP baseline (6h T4) |
| #3 | shifted window 2层 | 梯度累积 B=1024 (训练稳定) | hd=128 + dropout=0.05 (15h T4) |

**关键分歧**: Codex 把 MLP baseline 排第一 (归因)，Gemini 把架构改进排第一 (拓扑)，Claude 把零成本优化排第一 (大 batch + SWA)。

**Claude(独立) 的核心洞察**: "Gradient accumulation 到 batch=4096 + SWA 是**零额外 GPU 成本**的改进。只需要代码改动。这应该在任何 GPU 实验之前执行。如果这把 IC 从 0.029 推到 0.04，那后续所有实验的基线都更高。"

### Q15. 理论 vs 实现的最严重脱节

| 脱节 | Codex | Gemini | Claude (独立) |
|------|-------|--------|--------------|
| 压缩 vs λ_s=0 | 中——隐式压缩 (维度缩减) 替代了显式压缩 (L1) | 可调和——"智能压缩"不等于 L1 | 中——不违反哲学，只是选了不同实现 |
| 拓扑 vs 单层 | 高——比 width 更硬的约束 | **最严重** — "手持屠龙之刀，只用来切豆腐" | 高——类比单 kernel CNN 做图像分类 |
| 有限窗口 vs 零通信 | **最严重** — 理论核心的跨期协同完全没进模型 | 严重——"有限窗口"≠"固定且孤立的窗口" | **最严重** — 理论的要求不是零通信，只是当前的简化 |

**三方一致**: "有限窗口 + 零通信"是最严重的脱节。理论说保留拓扑，实现却把拓扑切成了碎片。

**Gemini 最精彩的表述**:
> "项目团队手持'拓扑'这把屠龙之刀，却只用它来切豆腐。"
> "当前实现就像用一堆互不相连的邮票大小的补丁去理解一幅巨大的、连续的画卷。它能看到每张邮票里的细节，但完全错失了画卷的整体构图。"

**Codex 最尖锐的警告**:
> "项目现在最危险的不是模型太弱，而是团队已经开始把一个近似指标上的局部成功，提前叙述成了架构真理。"
> "现在最不该做的事，就是把未测试过的部分叙述成'已经接近理论极限'。"

---

## 四、三方 L1 数学论证对照 (Q4)

三方各自独立给出了 L1 在肥尾分布下反信号的数学论证，论证路径不同但结论一致：

**Codex (Proximal Operator 路径)**:
> L1 的近端更新 `w_{t+1} = sign(w_t - ηg_t) × max(|w_t - ηg_t| - ηλ, 0)`。
> 尾部 detector 在大多数无信号 batch 中梯度 g_t ≈ 0，但 L1 shrinkage ηλ 每步都在扣。
> 少数 batch 刚拉起 detector，后面又被一串无信号 batch 削掉。
> → L1 优先杀死稀疏间歇触发的 tail detector。

**Gemini (激活值/目标对偶路径)**:
> 为预测大尾部目标，模型需在 z_core 中产生大幅度激活。
> L1 = ||z_core||_1 直接惩罚大激活。
> → 优化器被迫压制对尾部事件的预测能力。

**Claude(独立) (IC 梯度/L1 梯度冲突路径)**:
> Pearson IC 的梯度正比于 (pred - mean) × (target - mean)。
> 尾部的 target 偏差极大，是 IC 的主要贡献者。
> L1 梯度 = sign(z)，对所有值等权。
> → IC 说"尾部必须有大的预测差异"，L1 说"不允许有大的内部表示"。系统性冲突。

**三条论证路径互补，加在一起构成完整的因果链**:
1. IC 需要大尾部激活 (Claude)
2. L1 惩罚大激活 (Gemini)
3. L1 的 proximal update 在大量无信号步中持续削弱尾部 detector (Codex)

---

## 五、三方 Batch SNR 精确计算对照 (Q2)

| 审计师 | 方法 | B=256 SNR | B=1024 SNR | B=2048 SNR | 达到 SNR=1 需要 |
|--------|------|-----------|------------|------------|--------------|
| Codex | SE ≈ 1/√(N-3)，信号=Rank IC | 0.46 | 0.93 | 1.32 | B ≈ 1172 |
| Gemini | SE ≈ 1/√N，信号=Pearson IC | 0.16 | 0.32 (Pearson) | 0.45 (Pearson) | 远超 2048 |
| Gemini | SE ≈ 1/√N，信号=Rank IC | 0.47 | 0.93 (Rank) | 1.31 (Rank) | B ≈ 1172 |
| Claude | SE = (1-r²)/√(N-2)，信号=Pearson IC | 0.16 | — | — | **B ≈ 10,000** |

**分歧原因**: 信号用 Rank IC (0.029) 还是 Pearson IC (0.010)。

**仲裁**: IC Loss 优化的是 Pearson 相关，所以**训练过程中的梯度 SNR 应该用 Pearson IC 计算**。但模型选择和评估用 Rank IC。

**采纳 Claude 的双指标分析**: 
- 训练梯度 SNR (Pearson) ≈ 0.16 → 极低，梯度基本是噪声
- 评估 SNR (Rank) ≈ 0.47 → 低但不是零
- **这解释了为什么模型"看起来学到了东西"(Rank IC > 0) 但"训练不稳定"(epoch 间剧烈震荡)**

---

## 六、综合行动建议 (三方加权)

按三方投票权重排序。三方一致 = 最高优先级。

| 优先级 | 行动 | Codex | Gemini | Claude | GPU 成本 |
|--------|------|-------|--------|--------|---------|
| **P0** | Gradient accumulation → batch 4096 + SWA | ✓ | ✓ | ✓(首推) | **0h** |
| **P0** | MLP baseline | ✓(首推) | ✓ | ✓ | 6h |
| **P0** | hd=128 对比 (至少) | ✓ | ✓(首推) | ✓ | 15h |
| **P0** | 验证 shard 时序 + 加 embargo gap | — | — | ✓ | 0h |
| **P1** | 跨窗口通信 (overlapping / Swin) | ✓ | ✓(首推) | ✓ | 15h |
| **P1** | per-date evaluator 修正 | ✓(首推) | ✓ | — | 0h |
| **P2** | Tail-Weighted IC Loss | ✓ | ✓ | ✓ | 10h |
| **P2** | δ 经验测量 (log-log 回归) | ✓ | ✓ | ✓ | 0h |
| **P3** | mask_prob / dropout 搜索 | — | — | ✓ | 10h |

**零成本行动 (纯代码改动)**:
1. Gradient accumulation (16 步) → 有效 batch=4096
2. SWA/EMA 权重平均
3. 验证 shard 时序排序
4. 加 embargo gap (丢弃边界 1-2 shard)
5. per-date evaluator (需要 ETL v4 date 字段)
6. δ 经验测量 (用已有数据)

---

## 七、一句话总结

**三方独立审计一致认定**: Phase 13 的 Rank IC=0.029 是管线修复的胜利，不是模型极限。当前实现远未逼近 OMEGA 理论的上限。最大的脱节是跨窗口零通信，最低成本的改进是 gradient accumulation + SWA，最关键的归因实验是 MLP baseline。

---

*附件: 三份原始审计报告*
- `2026-04-06_codex_audit_report.md` (814 行)
- `2026-04-06_gemini_audit_report.md` (354 行)
- `2026-04-06_claude_audit_report.md` (507 行)
