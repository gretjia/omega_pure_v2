# Post-Phase 10 三步走战略方案

**日期**: 2026-03-31
**来源**: 首席架构师 (对话直传)
**公理影响**: AXIOM UPDATE REQUIRED (Layer 2 — 训练损失 + 架构变更，待 P0 回测结果确认)

---

## 背景分析

基于完整研发历史:
- Phase 6 锁定对称 IC 极限
- Phase 7/8 确认非对称物理天花板
- Phase 9 非对称 Pearson 灾难性坍塌
- **Phase 10 Softmax 组合损失破局**

Phase 10 的 `Val PfRet = 0.210` 是一个决定性的理论胜利，证明网络能够学习到横截面组合（Cross-sectional Portfolio）的资金最优分配，摆脱了单点绝对值预测的束缚。但 `Std_yhat` 膨胀到 5055 BP 以及反常的 OOS/IS Ratio (1.38) 说明模型在数学底层存在严重的"尺度失控"隐患。

---

## P0 绝对优先: Phase 10 的"物理熔炉"实盘验证 (The Crucible Test)

验证集上的 0.210 只是数学上的相对分数，必须立刻将 Phase 10 的产出投放到 Phase 8 打磨好的防弹模拟器中，接受真实 A 股物理法则的审判。

### 操作指令

1. **全量拓扑推理 (Full Inference)**
   使用 `linux1` 节点执行全量扫描（提取 Phase 10 Epoch 16 的 `gs://omega-pure-data/checkpoints/phase10_softmax_v5/best.pt`）。
   - **架构师要求**：推理脚本必须确保利用 forward hook 将 `z_core` 的稀疏度（MDL 结构复杂度 `S_T`，即 `z_sparsity`）提取并写入 `predictions.parquet`。这是未来做置信度过滤（Conviction Filter）和识别市场高熵状态的底牌。

2. **物理法则模拟回测 (Simulation)**
   利用 Phase 8 已经修复完毕的 `phase7_simulate.py`（或 `phase8_simulate.py`），必须严格开启以下执行层铁律：
   - `board_loss_cap: true` (主板10%/科创20% 跌停物理兜底，斩断隔夜尾部灾难)
   - `cost_bp: 25` (真实的双边摩擦冲击成本)
   - `max_positions: 50`
   - `trailing_stop_pct: -10%`

### 生死审判标准

* **终极指标 (S7)**：`Asymmetry Payoff Ratio`（平均单笔盈利/平均单笔亏损）是否终于突破了 Phase 8 死死卡住的 `1.2` 极限，迈向 3.0？
* 如果突破，Softmax 路线封神！如果依旧卡在 1.2，说明 Softmax 只是等比例放大了波动率，并未改变上下行尾部捕捉的对称性本质。

---

## P1 数学热修复: 斩断 Softmax 的尺度失控 (Variance Regularization)

### 物理根因

`Std_yhat` 高达 5055 BP，且 L2 mean-shift 无效。

Softmax 函数是"平移不变"的（`softmax(x) = softmax(x + c)`），且对尺度极其敏感。L2 mean-shift 只能把均值拉回 0，但完全无法约束极差。网络为了最大化横截面 PfRet（让头部几只股票的资金分配权重逼近 100%），在梯度下降中会不计代价地**成倍放大 logits 尺度**（等效于隐式降低 Softmax Temperature 逼近 One-hot 独热分布），导致绝对数值极度失真。这在实盘中极易引发微小的噪声被放大，导致满仓单只股票的集中度灾难。

### 架构修改建议

必须将无用的 L2 mean-shift 彻底替换为 **方差惩罚 (Variance Penalty)** 或引入 **Logits LayerNorm** 物理锁：

```python
# 方案 A: 损失函数级方差惩罚 (直接惩罚截面预测值的离散度)
logits_variance = torch.var(pred, dim=-1) # 计算截面方差
# 只惩罚超出合理物理边界的方差 (例如允许 std 波动在 100 BP 内，100^2=10000)
variance_penalty = l2_weight * torch.mean(F.relu(logits_variance - 10000.0))

# 方案 B: 架构级 Logits 钳制 (更推荐的硬核物理锁)
# 在网络最后输出前，强制实施无参数 LayerNorm，把 Std 物理锁死在常数级别
pred = F.layer_norm(raw_pred, normalized_shape=(1,)) * BASE_SCALE_BP
```

---

## P2 战略分水岭: 终局之战"双头阿修罗" (Two-Headed Asura)

根据 P0（实盘模拟器）的回测结果，触发两条截然不同的路线：

### 胜利分支：If Asymmetry Ratio > 2.0 且稳步逼近 3.0

证明 Softmax Portfolio Loss 已经打破了单头网络的对称性魔咒，成功提取了主力的肥尾拉升信号。
* **Next Action**：应用 P1 的方差修复压制 5055 BP 的尺度爆炸，全面进入 **Phase 11 (Hyperparameter Optimization)**。围绕 Softmax Temperature、方差惩罚权重展开贝叶斯搜索。同时核查 OOS/IS=1.38 是否仅仅是因为牛市 Beta 偏差导致（通过查看逐年收益分解，看 23-24 熊市表现）。

### 失败分支：If Asymmetry Ratio 依然死锁在 ~1.2

揭示终极物理定律：**在 A 股高度不对称的市场机制下，只要在一个 Epiplexity 瓶颈层（单一的 `z_core`）里，神经元就无法同时兼顾"做多拉升特征（贪婪）"和"做空派发特征（恐惧）"的拓扑映射，发生了任务坍塌。**

* **Next Action**：启动 INS-029 中封存的 **Path B: 双头阿修罗架构 (Two-Headed Asura)**。

#### 架构重构细节

共享底层的 SRL物理反演 + 2D FWT拓扑层，但在最后的信息瓶颈处，硬性撕裂出两个平行的 `hd=32` 的 `z_core`：

* **Long Head (The Bull Detector)**：用 Softmax 专职学习胜率极低但赔率极高的主升浪建仓。
* **Veto Head (The Crash Detector)**：用 BCE 专职学习规避主力出货和崩盘黑洞（Target < -500 BP）。
* **机制**：实盘时赋予 Veto Head **"一票否决权"**。不管多头信号多强，只要否决头亮起，强制拒绝开仓。从物理结构上强行斩断左侧肥尾亏损，将 Asymmetry 暴力推上 3.0。

---

## 首席架构师的执行指令

**先不要改任何训练代码，立刻交卷测盲盒。**

对 Phase 10 Vanguard V5 的 `best.pt` 执行推理（提取 `z_sparsity`）和模拟器回测（带上 Phase 8 的防弹参数）。

跑出新的 `phase7_results.json`，把 **S7 (Asymmetry Payoff Ratio)**、**Profit Factor** 和 **多空价差（L/S Spread）** 作为 P0 结果，决定走 P1（修补 Softmax 方差）还是 P2（双头阿修罗）。
