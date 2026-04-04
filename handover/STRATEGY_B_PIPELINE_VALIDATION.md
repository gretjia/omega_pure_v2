# Strategy B: Pipeline Validation Before Any New Training

**Date**: 2026-04-04
**Source**: Gemini 战略评估 + 11 轮外部审计共识
**Status**: MANDATORY — 阻塞所有新训练

---

## 核心诊断

> "你在用换 Loss 函数来解决管线工程 bug。这就是你一直在原地转圈的原因。" — Gemini

### 死亡循环（Phase 6 → 12 重复了 7 次）
```
改 Loss → 训练 → 训练指标好看 → post-flight 失败 → 再改 Loss → ...
```

### 铁证：Phase 6 的完美单调递减
```
Phase 6 IC Loss, T29 best trial:
  训练 val IC = 0.066 (看起来很好)
  Post-flight daily IC = 0.028 (退化但正)
  Post-flight D9-D0 = -5.92 BP (负值!)
  Deciles: [3.33, 4.47, 4.57, 4.27, 3.89, 3.09, 1.58, 0.15, -1.45, -2.59]
  Monotonicity: 2/9 (完美单调递减)
```

**完美单调递减不是噪声**。随机模型的 decile 应该平坦。-5.92 BP 的系统性反转只有两种解释：
1. 推理管线有 bug（99% 概率，Gemini 判断）
2. 特征工程系统性反转信号（需排查 FRT）

---

## 行动计划（强制顺序，不可跳步）

### Step 1: 重跑 Phase 6 T29 checkpoint [1 小时]
用**修复后的代码**（含 _orig_mod strip, pred*10000, hidden_dim=64, overflow clamp）重跑 Phase 6 T29 checkpoint 的 post-flight。

**对比**：
- 旧 post-flight (phase6_results/phase7_results.json): D9-D0=-5.92, IC=0.028
- 新 post-flight (修复后代码): D9-D0=?

**判定树**：
```
新 D9-D0 翻正 (> 0) → 历史 post-flight 失败全是代码 bug
  → 所有历史基准作废，用修复后代码重建基准
  → Phase 13 可以继续（在修复后管线上训练+评估）

新 D9-D0 仍为负 → 问题不在代码
  → 进入 Step 2: 排查 FRT 信号反转
  → 进入 Step 3: 排查评估指标
```

### Step 2: 排查 FRT 信号反转 [仅在 Step 1 未翻正时]
Phase 6 训练**不用 FRT**（raw LOB 特征直接进 input_proj）。但推理脚本 phase7_inference.py 可能用了 FRT（wrapper forward）或不用（core forward）。

**检查**：
- Phase 6 训练用的是哪个 forward？（OmegaTIBWithMasking wrapper? 还是 bare core?）
- Phase 6 推理用的是哪个 forward？
- 如果训练无 FRT + 推理有 FRT = **Train-Serve Skew**（Gemini 99% 诊断）
- 如果训练有 FRT + 推理有 FRT = FRT 本身可能反转信号

### Step 3: 修复评估指标 [与 Step 1/2 并行或之后]
将 D9-D0 从全局排序改为**按日期截面排序**（INS-067）。
- 用 Phase 12 现有的 val predictions parquet 做截面分析
- 不需要重新训练，只需要改 postflight_analysis.py

### Step 4: 修复架构 [在 Step 1-3 结果明确后]
- 去 Global Mean Pooling → Attention Pooling
- 加残差连接 + Pre-LN
- 修复 RPB 梯度

### Step 5: Phase 13 训练 [在 Step 1-4 全部通过后]
- 选择 Loss 函数（基于 Step 1 结果：如果 IC Loss 在修复管线上有效，用 IC Loss）
- 在修复后的管线上训练
- 用修复后的 post-flight 管线验证

---

## 阻塞规则

**在 Step 1 结果出来之前，以下操作被阻塞：**
- ❌ 任何新的 `train.py` 训练 job
- ❌ 任何 Loss 函数修改
- ❌ 任何模型架构修改
- ❌ Docker build for training

**允许的操作：**
- ✅ 重跑历史 checkpoint 的推理（不训练）
- ✅ 修改 postflight_analysis.py（评估代码）
- ✅ 修改 backtest_5a.py（推理代码）
- ✅ 分析现有 parquet 数据

---

## 预期时间线

| Step | 时间 | 依赖 |
|------|------|------|
| Step 1: 重跑 Phase 6 T29 | ~1h | Phase 6 checkpoint 可用 |
| Step 2: FRT 排查 | ~30min | Step 1 结果 |
| Step 3: 截面评估 | ~30min | 可与 Step 1 并行 |
| Step 4: 架构修复 | ~2h | Step 1-3 明确后 |
| Step 5: Phase 13 训练 | ~5h | Step 1-4 通过 |
| **总计（最快路径）** | **~9h** | Step 1 翻正则跳 Step 2 |

---

## 教训编号

- **C-065**: 训练指标好看 ≠ 模型有效。**每次范式切换前必须先验证推理管线**，不可直接改 Loss 再训练。完美单调递减是 bug 特征，不是模型失败。(Ω1: 只信实测)
- **C-066**: **不要用换 Loss 来解决管线 bug**。Phase 6→12 重复 7 次同一错误：训练好看→post-flight 失败→换 Loss。正确做法：先修管线，再评估 Loss。(Ω1 + Ω5: 先验证管线再训练)

---

*Prepared: 2026-04-04. Endorsed by Gemini strategic assessment.*
*This document blocks all new training until Step 1 is completed.*
