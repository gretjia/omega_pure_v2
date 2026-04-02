# Phase 11 工程师独立分析 — 致审计师/架构师

**Author**: Claude Opus (全程参与 Phase 10-11 全部工程实施)
**Date**: 2026-04-02
**Stance**: 以证据和数据为唯一依据，不预设立场

---

## 我的核心疑惑

经历了 Phase 11 的四次迭代 (11a/b/c/d) 和一次完整的 post-flight，我有一个越来越强烈但无法自行回答的疑问：

**这个 19.7K 参数的模型，是否从根本上就不具备从 A 股 L1 tick 数据中提取可交易 alpha 的能力？**

以下是支持和反对这个假说的证据。

---

## 证据 1: Loss 函数走马灯 — 每一个都"合理地失败"

| Phase | Loss | 结果 | 死因 |
|-------|------|------|------|
| 6 | IC Loss | IC=0.066, OOS/IS=1.00 | 被诊断为"尺度免疫"漏洞 |
| 9 | Asymmetric Pearson | 7 jobs 全败 | Reward Hacking (INS-035) |
| 10 | Softmax Portfolio | Asym=1.30 | Beta 走私 (INS-049) |
| 11a | Spear + Z-score | NaN 全崩 | 勾股漂移 (INS-046) |
| 11b | Spear + Detached Std | Beta 走私 | Softmax 残留 (INS-049) |
| 11c | Pointwise Huber δ=50 | pred_std=5.6 BP | 方差坍缩 (INS-054) |
| 11d | Pointwise Huber δ=200 | IC=0.002 | 方差是噪声非信号 |

**每次失败都有合理的物理解释，每次"修复"都引入了新的问题。** 但如果退一步看：我们已经尝试了 7 种不同的 Loss 函数，没有一种在全量 val 上产生可交易信号。这是否暗示问题不在 Loss，而在 Loss 上游？

**反论**: Phase 6 的 IC=0.066 是在全量 val 上的（非小样本），且 OOS/IS=1.00。这证明模型确实能学到信号。但 Phase 6 用的是 IC Loss，而 IC Loss 被后来的架构师裁决否定了（INS-018 superseded）。**那个被否定的 Loss 产出的信号到底是真信号还是统计幻觉？这个问题从未被严格验证。**

---

## 证据 2: z_core 跨所有 Phase 始终"死亡"

| Phase | z_sparsity | S_T | 诊断 |
|-------|-----------|-----|------|
| 10 (Softmax) | ≈0 | 低 | "脑死亡" (INS-050) |
| 11c (Huber δ=50) | 0.44% | 116-157 | 脑死亡 |
| 11d (Huber δ=200, λ_s=1e-4) | **0.12%** | 225-238 | **更死** |

**Phase 11d 的 λ_s 降了 10 倍，δ 放了 4 倍，S_T 从 157 涨到 235（看起来"活了"），但 z_sparsity 从 0.44% 降到 0.12%（实际更死了）。**

S_T = ||z_core||₁ 上升 + z_sparsity 下降 = 少数神经元的值变大了，但大多数仍然是零。模型在用极少数通道的大幅度波动来应对 Loss，而不是广泛激活特征层。

**这意味着 z_core（Epiplexity 瓶颈层）从 Phase 10 到 11d，从未真正被模型利用过。** 无论 Loss 怎么换、λ_s 怎么调，模型都选择绕过这一层。

**问题**: 是否存在架构上的"捷径"让模型可以绕过 z_core 直达预测层？如果是，z_core 就不是"被压死"而是"没必要活"。

---

## 证据 3: SRL 物理层可能提供了"免费午餐"

SRL Inverter 是确定性的（无可学习参数）：
```python
Q_hidden = sign(ΔP) × (|ΔP| / (c_i × σ_D))^2 × V_D
```

它直接从输入张量的 Ch7(ΔP), Ch8(V_D), Ch9(σ_D) 计算元订单流。这个物理量本身就携带信息——不需要任何学习。

**如果 SRL 输出直接被 Global Pool → Linear Decoder 捕获，模型可以完全跳过 Topology Attention 和 Epiplexity Bottleneck（z_core），靠物理层的"免费信号"拿到 IC≈0.01。**

Phase 11d 的 daily IC mean=0.009 恰好在这个量级。这意味着 Phase 11d 可能只是在做 SRL → Decoder 的直通，20 个 epoch 学的东西约等于零。

**验证方法**: 冻结 z_core 为全零（或随机噪声），只训练 Decoder，看 IC 是否与当前相同。如果相同，z_core 就是"死代码"。

---

## 证据 4: Val PfRet 的"神秘稳定性"

跨所有 Phase 和 Config，Val PfRet 始终在 **6.9-7.5** 区间：

| Phase/Config | Best Val PfRet |
|-------------|---------------|
| 11c E1 | 7.23 |
| 11d-A E11 | 7.44 |
| 11d-B E5 | 7.42 |
| 11d-A E0 (随机初始化) | 7.15 |

**E0（完全未训练的随机权重）就有 PfRet=7.15。** 训练 20 个 epoch 后 PfRet=7.28。

这个指标的计算方式是:
```python
weights = clamp(pred, min=0) / sum(clamp(pred, min=0))
pf_ret = (weights * target).sum()
```

当模型输出全正值（因为 clamp(target,min=0) 训练），weights 近似均匀分布，PfRet 就近似 mean(target)。**PfRet 对预测质量几乎不敏感** — 只要模型输出正值，PfRet 就在 7 附近。

**这意味着我们一直在用一个几乎无区分力的指标作为 best checkpoint 的选择标准。** best.pt 可能只是随机波动中的最高点，而非真正最优的权重。

---

## 证据 5: 小样本幻觉 vs 全量真相

| 数据集 | Samples | Dates | IC |
|--------|---------|-------|-----|
| Phase 11c 烟测 | 25,000 | 2 | 0.021 |
| Phase 11d 全量 val | 1,993,131 | 75 | 0.002 |

**10x 差异。** 2 个交易日的截面 IC 在统计上毫无意义。但我们（包括架构师）基于这个 0.021 做了一系列重大决策（设计 Phase 11d、制定 30 BP 阈值、规划 Epiplexity 验证）。

**教训已入 C-055，但更深的问题是**: 我们之前的 Phase 6 IC=0.066 是在多少 dates 上计算的？如果也是少数 dates，那个信号可能同样不可靠。

---

## 证据 6: window_size_s=4 vs spec=10

`current_spec.yaml` 规定 `spatial_axis: 10`（完整 LOB 10 档），但训练实际使用 `--window_size_s=4`。这意味着 **60% 的空间信息被丢弃**。

架构的核心论点是"空间轴不可被拍扁"（公理 8），Topology Attention 需要 2D 空间结构来捕捉 LOB 的拓扑连通性。但 ws=4 只保留了 4 档深度——离"拍扁"只有一步之遥。

**这个不一致可能是 z_core 死亡的贡献因素**: 如果空间轴被压到 4，Topology Attention 的输入太贫乏，无法提取有意义的拓扑特征，z_core 自然没有值得编码的信息。

---

## 证据 7: 48% 零目标的 clamp(target, min=0)

Asymmetric Target Blinding 将 48% 的样本目标设为 0（所有负收益和噪声）。这在概念上合理（"只检测建仓"），但在工程上：

- 模型对 48% 的数据只学到"输出接近 0 就不会被惩罚"
- Huber Loss 对"预测 30 BP 但目标 0"的误差 = 0.5 × 30² = 450
- Huber Loss 对"预测 30 BP 但目标 200 BP"的误差（δ=200 线性区）= 200 × (170 - 100) = 14000
- **对高回报样本的惩罚是零目标样本的 31 倍**

模型的最优策略：尽量靠近 0 和 30 BP 均值之间，不要冒险预测极端值。这与我们观察到的 pred_bp range [1.5, 136.6] 中位数 ~50 BP 一致。

**问题**: clamp(target, min=0) + Huber Loss 的组合是否在数学上就封死了模型学习个股差异的能力？

---

## 我的思路（假说排序）

从最可能到最不可能：

1. **架构捷径 (60%)**: SRL → Global Pool → Decoder 的直通路径让模型无需 z_core 就能拿到 IC≈0.01 的基线。需要验证：冻结 z_core=0 是否 IC 不变。

2. **模型容量不足 (20%)**: hd=64 / 19.7K params 对 [B, 160, 10, 10] 输入来说可能太小。需要验证：hd=128 是否改善（spec 已预留 HPO 搜索）。

3. **空间信息丢失 (10%)**: ws=4 丢弃了 60% LOB 深度。需要验证：ws=10 是否改善。

4. **目标定义过于激进 (10%)**: clamp≥0 + Huber 的组合数学上抑制了区分度。需要验证：leaky clamp (如 clamp(target, min=-10)) 或对称目标是否改善。

---

## 给审计师的请求

1. **Phase 6 IC=0.066 的有效性**: 请审计 Phase 6 的 val 数据量（多少 dates？多少 samples？）。如果 dates < 20，那个 IC 可能也是小样本幻觉，整个项目的信号前提需要重新评估。

2. **SRL 直通验证**: 是否有人做过"去掉 z_core，只用 SRL→Decoder"的消融实验？如果没有，这应该是最高优先级实验——它能一次性回答"模型是否需要学习层"。

3. **PfRet 指标有效性**: PfRet 对预测质量几乎不敏感（随机权重也有 7.15）。是否应该换成 IC 或 D9-D0 spread 作为 best checkpoint 选择标准？

4. **ws=4 vs ws=10 的历史决策**: 为什么实际训练用 4 而非 spec 的 10？这是有意还是遗留 bug？如果是有意的，哪个 Phase 做了这个决策？

5. **是否需要回退到 Phase 6 的 IC Loss 框架**: Phase 6 是唯一在全量 val 上展示过 IC=0.066 的配置。后续所有 Phase 都在尝试"更好的 Loss"但全部失败。是否应该严肃考虑"Phase 6 的 Loss 已经是最优解，后续的架构师裁决可能是错误的"这个可能性？

---

## 数据来源
- Phase 11c 烟测: `reports/audits_and_insights/2026-04-01_phase11c_smoke_test_report.md`
- Phase 11d 全量: `reports/phase11_complete_data_summary.md`
- Phase 11d 训练日志: `gs://omega-pure-data/checkpoints/phase11d_A_v1/train.log`
- Phase 6 结果: `reports/phase6/`
- 架构 spec: `architect/current_spec.yaml`
- 全部 insights: `architect/insights/INDEX.md` (INS-001~056)
- 全部 lessons: `OMEGA_LESSONS.md` (C-001~057)
