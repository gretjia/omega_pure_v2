# 架构师终极裁决 —— 击碎等价谬误，捍卫绝对的 Alpha
# External Audit Override

**Date**: 2026-04-02
**Author**: Chief Architect
**Source**: 对 Codex FAIL + Gemini CONDITIONAL PASS 审计结果的架构师覆盖裁决
**Stance**: 敬畏外部审计，但绝不盲从。在反向传播的物理管线中，数学公式的"表面等价"往往是致命的陷阱。

---

## 审计背景

Codex 和 Gemini 对 INS-057~062 spec diff 进行了独立审计，提出 4 个发现：
1. [CRITICAL] pred_bp 未居中 vs tgt_centered 已居中 — 模型输出语义变更
2. [HIGH] static_mean_bp=40.0 硬编码 — 牛/熊市场均值漂移风险
3. [FLAG] lambda_s 从 1e-4→1e-3 (10x) 需实测标定
4. [FLAG] omega_axioms.py 子串匹配 "spread" 过宽

---

## 裁决 1：Pred 居中博弈 —— 【死守路径 A，彻底封杀路径 B】

**裁决：维持现状（路径 A）。确立模型输出的物理语义正式变更为"纯粹的超额 Alpha (Excess BP)"**

**数学反证法与病理剖析：**

为什么 Codex 暗示的路径 B（`pred_centered = pred_bp - 40`，同时 `target_centered = tgt - 40`）是绝对的毒药？

路径 B 在 MSE 中的微积分底层误差项：
```
Err_B = (pred_bp - 40) - (target_bp - 40)
```

根据最基本的代数消元法，两个 -40 会被完全抵消！
```
Err_B ≡ pred_bp - target_bp
```

如果采用路径 B，**精心设计的"静态置零"防线在反向传播的数学底层就等同于不存在**。优化器会立刻发现这个漏洞，并在第一个 Epoch 就操控网络最后一层的 Bias 参数无脑飙升到 +40。模型将继续舒舒服服地"走私 Beta"，彻底拒绝唤醒 z_core。

**拥抱路径 A 与语义反转：**

只有路径 A：`Err_A = pred_bp - (target_bp - 40)`

当目标分布的数学期望被强行拉到 0 附近时，模型为了让 MSE 最小，**被迫只能将 Bias 压制到 0**。Bias 作弊的路被彻底焊死！模型别无选择，只能通过激活 z_core 去解释 0 轴两侧的个体方差（这正是我们苦苦追寻的 Alpha）。

**关于推理侧的对齐：**

不需要加回 40！核心指标是 Rank IC 和 D9-D0 Spread。在截面排序的世界里，Rank(X) ≡ Rank(X + 40)。绝对的大盘 Beta 偏移对多空排序毫无意义。让模型输出纯粹的 Excess BP 是架构上的降维打击。

---

## 裁决 2：static_mean_bp 的硬编码风险 —— 【拒绝动态计算，提升为 Config 注入】

**裁决：严禁 Batch 内动态计算，提升为 Config 注入的全局先验常量**

- **物理禁区**：如果在 Loss 内写 `target.mean()` 动态居中，将立刻触发 INS-049 跨时空 Batch 毒化，毁掉绝对的点对点因果性，同一 Batch 内的股票会产生严重的交叉泄露。
- **执行指令**：将 STATIC_MEAN_BP 从 Loss 内部的硬编码中抽离出来，作为函数的传入超参（默认值 40.0）。在标准流程中，该值必须由 ETL 管道在**整个 In-Sample 训练集**上做一次性全局统计得出，并写入 config.yaml 静态注入。用"静态物理锚点"代替"动态统计游标"。

---

## 裁决 3：lambda_s 量级跃进 —— 【采纳审计预警，强制回退至 1e-4】

**裁决：拒绝 1e-3，保留 1e-4 待实测**

- **量纲悖论**：工程师提议 1e-3 的理由是"MSE量级较大"。但在上一轮审计修正中已加入 SCALE_FACTOR = 10000。
- **沙盘推演**：50 BP 误差的未缩放 MSE = 2500，缩放后 loss_err ≈ 0.25。如果 λ_s = 1e-3 且 S_T ≈ 100，结构税 = 0.1。惩罚项与主 Loss 处于 1:2.5 的危险比例，极可能碾碎微弱的特征梯度，导致 z_core 二次脑死亡。
- **执行指令**：回退至 1e-4。让 L1 正则在较低安全水位（~4% 主误差占比）运行，后续交由 HPO 自动标定。

---

## 裁决 4：Axioms.py 弱匹配漏洞 —— 【全面同意】

**裁决：核准 Exact Match 修复方案**

- 彻底废除 `in` 子串匹配，修改为精确 allowlist = ["d9_d0_spread", "rank_ic"]。堵死 bid_ask_spread 等被误判的后门。

---

## 执行序列

1. 保持路径 A（仅 Target 居中），正式确立 Excess BP 输出语义，推理端无需加回
2. 将 static_mean_bp 改造为传参（默认 40.0）
3. 强制回调 λ_s = 1e-4
4. 应用精确匹配 Axiom 补丁
5. 打上 [AUDIT OVERRIDDEN] 标签
