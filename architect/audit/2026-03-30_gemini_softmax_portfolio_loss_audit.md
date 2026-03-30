# Gemini 独立数学审计：Softmax Portfolio Loss 维度跃迁

- **日期**: 2026-03-30
- **模型**: gemini-3.1-pro-preview
- **审计对象**: INS-032~035 + current_spec.yaml 变更提案
- **总裁决**: CONDITIONAL GO (有条件放行)

---

## 审计结果

| # | 审计项 | 裁决 |
|---|--------|------|
| 1 | Phase 9 失败病理诊断（Pearson 尺度免疫 + Reward Hacking） | ✅ CONFIRMED |
| 2 | Softmax Portfolio Loss 数学性质 | ❌ REFUTED (实现有致命陷阱) |
| 3 | Spec 变更完整性 | ⚠️ CONCERN (遗漏和参数冲突) |
| 4 | z_sparsity 作为交易扳机 | ✅ CONFIRMED |
| 5 | 遗漏风险点 | ⚠️ CONCERN (L2 惩罚梯度副作用) |

---

## 3 个致命陷阱及修正

### 陷阱 1: Softmax 截面坍塌（时间轴 vs 截面轴混淆）

架构师代码 `pred.view(-1)` 后做全局 Softmax，如果 Batch 内混合不同股票不同时间点样本，等同于让"昨天的茅台"和"今天的平安"竞争同一资金池 → 时间穿越 / Look-ahead bias。

**修正**: Softmax 必须在截面维度(dim=1)上计算。DataLoader 必须保证每 Batch 是同一时间截面，或 Loss 内按 Time ID groupby 后在截面维度 Softmax。

### 陷阱 2: L2 惩罚项破坏底部排序

`l2_weight * mean(pred²)` 对所有非 Top 股票产生 -2λŷ 梯度，无脑压向 0 → 底部区分度丧失。

**修正**: 改为 `l2_weight * (mean(pred))²`，仅惩罚全局平移，不破坏个体方差。

### 陷阱 3: Batch Size 变成物理参数

Softmax Loss 下 Batch Size = 投资组合候选池大小，不同 batch_size 的 Loss 不可比 → 不可作为 HPO 搜索项。

**修正**: 固定 batch_size=256，从 HPO search_space 移至 fixed_params。

---

## 放行条件

1. ✅ 修复 Softmax 截面维度 — 已反映到 spec: `dim=cross_section`
2. ✅ 修正 L2 惩罚 — 已反映到 spec: `mean(pred)^2`
3. ✅ 补齐 Spec — batch_size 固定, temperature/l2_weight 显式配置, metric=val_portfolio_return
