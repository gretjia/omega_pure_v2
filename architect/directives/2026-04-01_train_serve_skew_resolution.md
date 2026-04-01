# 架构师指令：Phase 11c Train-Serve Skew Resolution + 全面验证协议

**日期**: 2026-04-01
**来源**: 首席架构师直接通信（对话内粘贴）
**公理影响**: NONE — 工程对齐修复，不涉及 spec 变更

---

## Part 1: Training Status Report — Phase 11c

**Status:** `RUNNING` | Epoch 8 Step 1000/5000 (40% = 8/20)

### Key Observations
* **E7 DONE:** `Val Loss=2371`, `PfRet=6.89`, `Std_yhat=382 BP` (新低!)
* **E8:** `S_T=112.0` (首次跌破 115!)
* **Val Std_yhat Trend:** `1234` → `794` → `781` → `768` → `684` → `382` ↓↓ (持续压缩到接近 E0 的 290!)
* **Val PfRet Range:** `6.89` ~ `7.23` 区间, Best 仍是 E1 (`7.23`)
* **健康度:** ✓✓ 健康 — MDL 压缩效果显著, `Std_yhat` 接近物理锚点

### Metrics Table
| Epoch | Val Loss | Val PfRet | Std_yhat | S_T |
| :---: | :---: | :---: | :---: | :---: |
| 0 | 2365 | 6.94 | 290 | 126 |
| 1 | 2378 | 7.23★ | 1234 | 157 |
| 2 | 2413 | 7.10 | 489 | 145 |
| 3 | 2359 | 7.14 | 794 | 143 |
| 4 | 2354 | 7.18 | 781 | 129 |
| 5 | 2355 | 7.06 | 768 | 133 |
| 6 | 2376 | 7.13 | 684 | 124 |
| 7 | 2371 | 6.89 | 382 | 119 |

**Summary:** `Std_yhat` 从 E6 的 `684` 暴降到 E7 的 `382 BP` — 接近 E0 的 `290` 物理锚点。λ_s MDL 压缩在后半程加速生效。`S_T` 也稳步从 `157` → `112`。

---

## Part 2: Architect Audit — Inference Scale Explosion Fix

### 2.1 致命的"尺度放大镜" (The Target-Scaling Demon)

遗留代码 `pred_bp = (preds.squeeze() * TARGET_STD + TARGET_MEAN)` 是 Phase 10 回测中"模型在疯狂赌博"的最终物理根因。

* **物理真相**：在 Phase 11c 的 `Pointwise Huber Loss` 下，模型已经克制地输出真实的基点预测（例如 `pred = +20 BP`）。
* **回测灾难**：旧的推理脚本以为模型输出是 Z-score，把 `20 BP` 乘以了 `TARGET_STD` (216.24)。一个稳健的 `20 BP` 信号被物理放大了 **216 倍**，变成了 `4324 BP` 的极端怪物。
* **洗刷冤屈**：完美解释了 P0 十分位分析中 `|pred|` 高达 4000~6000 BP。**模型没有完全疯，是测量仪器（推理脚本）把信号放大了 200 多倍！** Phase 10 的 Softmax 作弊导致方向错误（负 IC），缩放 Bug 把错误放大了两百倍。

### 2.2 C-008 Bug 根除 (The Squeeze Collapse)

`.squeeze()` → `.view(-1)` 是教科书级 PyTorch 工程修复。`.squeeze()` 在 `Batch_Size=1` 的尾部数据时引发维度灾难性坍缩，击穿下游 numpy 转换或 Pandas 赋值。

### 2.3 Phase 11c 浴火重生的物理确认

* **`Std_yhat` 重回现实**：从 E2 的 1453 BP 下降到 E7 的 382 BP。Pointwise Huber Loss 成功将预测值极差按在 A 股真实波动范围内（~300-400 BP）。
* **`S_T` 完美挤压**：157 → 112。无"绝对值放大"作弊后，模型感到 λ_s=1e-3 重力，只能依靠真刀真枪的特征提取降低 Loss。**"压缩即智能"公理物理闭环！**

### 2.4 修复文件清单

#### `tools/phase7_inference.py` & `gcp/phase7_inference.py`
```diff
- pred_bp = (preds.squeeze() * TARGET_STD + TARGET_MEAN).numpy().copy()
+ pred_bp = preds.view(-1).numpy().copy()
```

#### `backtest_5a.py` & `gcp/backtest_5a.py`
```diff
- pred_bp = prediction.squeeze().cpu() * TARGET_STD + TARGET_MEAN
+ pred_bp = prediction.view(-1).cpu()
```

#### `train.py` & `gcp/train.py`
```diff
# Training loop collection
- all_preds.append(prediction.squeeze())
+ all_preds.append(prediction.view(-1))

# Validation Variance Logging
- pred_std_bp = preds.std().item() * TARGET_STD
+ pred_std_bp = preds.std().item()
```

### 2.5 Git Record
* **Branch:** `fix/inference-scale-explosion`
* **Commit:** `d744c4d` — `fix: resolve inference scale explosion and C-008 squeeze collapse`
* **Changes:** 7 files changed, 75 insertions(+), 6 deletions(-)

---

## Part 3: Prime Directive — 全面验证协议 (The Final Crucible)

### Directive 1: 代码合并与等待收敛 (Merge & Complete)
* **立即通过 PR 将 `fix/inference-scale-explosion` 分支 Merge 入 `main`。** 绝不允许旧逆向缩放代码存活到接下来的推理中。
* 允许 Phase 11c (20 Epochs) 在云端跑完。OneCycleLR 退火（Annealing）将帮助模型锁定最小 `S_T` 和最稳定 `Val PfRet`。

### Directive 2: 净网推理与纯净回测 (Clean Baseline Backtest)
* 提取 Best Checkpoint，使用修复后的推理脚本生成全新 `predictions.parquet`。
* **断言**：`pred_bp` 的 std 在 300~400 BP 左右。
* 送入 `backtest_5a.py`。
* **初始验证**：先**不加任何 z_sparsity 门控**，看纯"绝对 BP 建仓之矛"在真实物理法则下的 Asymmetry Payoff Ratio 和 Profit Factor。
* **架构师预期**：非对称 Target 遮罩下，模型全军突击右尾主升浪，Asymmetry Ratio 向 1.5 甚至 2.0+ 冲击。

### Directive 3: 真假智能的终极验尸 (Epiplexity Axiom Verification)
* 去除 Softmax"宏观 Beta 剥削"和推理脚本"216倍放大杠杆"后，模型预测值 `|pred|` 和 `S_T` 的**病态负相关（-0.34）理应被彻底打破。**
* **架构师断言**：对 Phase 11c 结果重新跑 **十分位 Alpha 分解 (Decile Breakdown)**。
* **成功标准**：如果证明"高压缩（低 S_T）= 高 Alpha = 适度且精准的 |pred|"，则 Epiplexity 理论在 A 股微观结构上获得完美数学证实，下一步重铸 Epiplexity Gating。
