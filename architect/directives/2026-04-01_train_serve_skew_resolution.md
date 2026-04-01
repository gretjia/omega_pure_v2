# 架构师指令：Phase 11c Train-Serve Skew Resolution + 全面验证协议

**日期**: 2026-04-01
**来源**: 首席架构师直接通信（对话内粘贴）
**公理影响**: NONE — 工程对齐修复，不涉及 spec 变更

---

## Part 1: Training Status Report — Phase 11c

**Status:** `RUNNING` | Epoch 8 Step 1000/5000 (40% = 8/20)

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

**Summary:** Std_yhat 从 E6 的 684 暴降到 E7 的 382 BP — 接近 E0 的 290 物理锚点。λ_s MDL 压缩在后半程加速生效。S_T 稳步从 157 → 112。

---

## Part 2: Architect Audit — Inference Scale Explosion Fix

### 致命的"尺度放大镜" (The Target-Scaling Demon)

遗留代码 `pred_bp = (preds.squeeze() * TARGET_STD + TARGET_MEAN)` 是 Phase 10 回测中"模型在疯狂赌博"的最终物理根因。

* **物理真相**：Phase 11c Pointwise Huber Loss 下，模型输出真实绝对 BP（如 +20 BP）。
* **回测灾难**：旧推理脚本以为输出是 Z-score，乘以 TARGET_STD (216.24)。20 BP → 4324 BP，放大 216 倍。
* **洗刷冤屈**：完美解释 P0 十分位中 |pred| 高达 4000~6000 BP。模型没有完全疯，是测量仪器放大了 200 多倍。

### C-008 Bug 根除
`.squeeze()` → `.view(-1)`。防止 Batch_Size=1 尾部数据维度坍缩。

### 修复文件清单

| 文件 | 变更 |
|------|------|
| `tools/phase7_inference.py` / `gcp/` | 移除 TARGET_STD/MEAN 缩放 + .view(-1) |
| `backtest_5a.py` / `gcp/` | 同上 |
| `train.py` / `gcp/` | 验证日志去缩放 + .view(-1) |
| `omega_epiplexity_plus_core.py` / `gcp/` | MDL loss 中 .view(-1) |

---

## Part 3: Prime Directive — 全面验证协议

### Directive 1: 代码合并与等待收敛
* 立即 Merge `fix/inference-scale-explosion` → `main`。
* 允许 Phase 11c (20 Epochs) 跑完。

### Directive 2: 净网推理与纯净回测
* Best Checkpoint → 净网推理 → pred_bp std 断言 300-400 BP → backtest_5a.py → phase7_simulate.py
* 先不加 z_sparsity 门控，看纯绝对 BP 的 Asymmetry Ratio 和 Profit Factor。

### Directive 3: Epiplexity 公理验证
* 十分位 Alpha 分解：按 z_sparsity 分桶，验证"高压缩=高 Alpha=精准 |pred|"。
* 成功标准：Corr(z_sparsity, |pred|) 归零（Phase 10 病态值 -0.34），低 S_T 桶 IC > 高 S_T 桶 IC。
