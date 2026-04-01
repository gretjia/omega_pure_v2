---
id: INS-051
title: 点对点建仓之矛 — Pointwise Huber Loss 替代 Softmax 交叉熵
category: training
date: 2026-04-01
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirm
source_directive: 2026-04-01_phase11c_pointwise_spear.md
source_gdoc: null
---

# INS-051: 点对点建仓之矛 — Pointwise Huber Loss 替代 Softmax 交叉熵

## 裁决
将 `compute_spear_loss` 中的 Softmax 交叉熵 + Detached Z-score 方差锁 **彻底替换为** Pointwise Huber Loss (delta=50)。新 Loss 函数 `compute_spear_loss_pointwise` 零跨 Batch 依赖，完全免疫时空错位。

核心设计：
1. **非对称目标致盲**: `target_acc = clamp(target, min=0)` — 纯建仓检测（继承 INS-042）
2. **Pointwise Huber Loss**: `F.huber_loss(pred, target_acc, delta=50.0)` — 绝对 BP 尺度锚定
   - delta=50: 0~50 BP 区间 MSE 级严苛锁定，>50 BP 切换 L1 防梯度爆炸
   - 无任何跨 Batch 比较，模型瞎赌(pred>0, target≤0)立即承受绝对误差惩罚
3. **MDL 压缩**: `lambda_s=1e-3` — Huber Loss 量纲(几十到几百) 要求更大的 λ_s

## 理由
INS-049 确认 Softmax/Z-score 在乱序 WebDataset 上制造宏观 Beta 走私。Huber Loss 从物理上封死 6956 BP logit 膨胀——Huber 的 L1 区间将梯度从 O(residual) 降为 O(1)，极端预测不再获得指数级奖励。同时绝对尺度锚定迫使 Std_yhat 回落到真实 A 股 BP 区间（几十到几百）。

**取代**: INS-043 (Spear Accumulation Loss), INS-047 (Detached Straitjacket), INS-045 (T=0.1→0.5)

## 影响文件
- `train.py`: 替换 `compute_spear_loss` → `compute_spear_loss_pointwise`，删除 temperature 参数
- `current_spec.yaml`: 更新 training.loss, loss_function, lambda_s; 删除 temperature, variance_lock
- `current_spec.yaml`: HPO 搜索空间删除 temperature，调整 lambda_s 范围到 [1e-4, 1e-2]
