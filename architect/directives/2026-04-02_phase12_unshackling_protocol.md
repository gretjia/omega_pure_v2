# 架构师终极诊断与系统级裁决 + 独立审计修正
# Phase 12 复苏协议 (The Unshackling Protocol)

**Date**: 2026-04-02
**Source**: 两份联合指令
  1. 首席架构师 / 递归审计委员会 — 终极诊断与系统级裁决
  2. Prime Executor / Codex 联合审计组 — Phase 11f 拦截与修正
**Source ID**: code-generated-file-OMEGA_LESSONS-1775175103098950766.md (conversation-embedded)
**Axiom Impact**: UPDATE REQUIRED — training.loss, metrics, target processing 全面重构

---

## 一、架构师终极诊断 (Architect's Verdict)

### 核心裁决：模型 19.7K 参数并非容量不足

模型表现出"优化器智能"——在被架构捷径、数学悖论、评价盲区和数据饥饿共同构建的病态环境中，找到了"阻力最小的路径"，以"躺平"实现全局最优。

### 证据与假说审计

#### 1. 确认假说 1：SRL 捷径学习 (Shortcut Learning) —— 确信度 99%

- **物理博弈**：SRL 层提取的元订单流是高信噪比物理量。优化器面临两个选择：
  - 路径 A：费力优化 Topology Attention，挤过 Epiplexity 瓶颈，还挨 L1 正则惩罚
  - 路径 B：通过残差/直通旁路，将 SRL 物理信号线性透传给 Decoder，轻松拿到 IC=0.009
- **结论**：梯度"水往低处流"。优化器走了捷径，把 `z_core` 权重压至接近 0（z_sparsity = 0.12%），完美规避 L1 惩罚。**`z_core` 不是学不到特征，而是被架构直通车"饿死"了。**

#### 2. 确认假说 4：Huber + 零目标 = 方差绞肉机 —— 确信度 100%

- `clamp(target, min=0)` + 点对点对称 δ=200 Huber Loss = "方差断头台"
- **数学机制**：48% 目标被抹零 → 零膨胀(Zero-inflated)分布。模型试图捕捉 200 BP 真 Alpha 时，一旦实际 target 为 0，Huber 给出二次方级惩罚。
- **结论**：模型最优自保策略 = 拟合条件均值(Conditional Mean)，退化为 30-50 BP 常数预测器。**这是方差坍缩 (INS-054) 的根本物理原因。**

#### 3. PfRet 的数学海市蜃楼 —— 最致命的评价失效

- 随机初始化 E0 就能拿到 `PfRet=7.15`
- **真相**：方差坍缩 → 预测值高度集中 → softmax/归一化后权重趋近均匀分布 $w_i \approx 1/N$
- **结论**：均匀等权组合收益 = 验证集所有正收益目标的算术平均值。**7.4 BP 不是模型预测 Alpha，而是验证集"大盘多头 Beta 均值"。** 我们一直用对横向排序能力完全免疫的掷骰子指标保存 Best Checkpoint！

#### 4. 空间视觉的自我阉割 —— 一级工程 Bug

- 公理 8 明确 LOB 是二维空间拓扑。L1-L4 档充斥虚假流动性（Spoofing）和噪声，真正机构挂单流形在 L5-L10 档。
- 强行砍掉 60% 深水区（`ws=4`）= 挖去 Topology Attention 的双眼
- **确认**：`train.py:504` 和 `gcp/train.py:504` 默认 `--window_size_s=4`，而 spec 固定为 10。这是早期防 OOM 遗留的脏补丁。

#### 5. Phase 6 IC=0.066 历史翻案

- IC Loss (Pearson/Spearman) 是**尺度免疫**和**位置免疫**的，只惩罚"排序错误"，不怕零目标，不怕均值偏离。
- Phase 6 没崩是因为它完美避开了"方差坍缩"陷阱。
- **历史误判**：INS-018 因模型预测绝对尺度极小而废弃 IC Loss。诊断对但药方错——为修正绝对尺度引入 Huber，连最宝贵的"排序能力"一起杀死了。

### Phase 12 复苏协议 (The Unshackling Protocol)

**Action 1: 验证并斩断捷径 (The Naked Ablation) [P0]**
- 在 Forward 中硬冻结 `z_core = z_core.detach() * 0`，仅跑 `SRL -> Decoder`
- 预期：IC 仍在 0.009 左右则实锤捷径。下一版必须物理切断 Skip Connection，逼迫梯度流经 Epiplexity 瓶颈

**Action 2: 砸碎旧尺子，重构 Metric [P0]**
- 从代码中彻底删除 `Val PfRet` 作为 early-stopping 和 `best.pt` 保存依据
- 替换为 **Rank IC** 或 **D9-D0 Spread**（头部 10% 减尾部 10% 收益差）

**Action 3: 恢复空间纵深 [P0]**
- 代码强制对齐 Spec，恢复 `--window_size_s=10`

**Action 4: 解除目标绞杀，解耦学习范式 [P1]**
- 取消 `clamp(target, min=0)` 或改用 `Leaky Clamp (min=-20)`
- 重新引入 Rank-based Loss（Differentiable Spearman 或 Contrastive Loss）主导特征提取
- 解耦尺度：主 Loss 负责排序，极小权重 MSE 锚定尺度；或两阶段训练

---

## 二、独立审计工程裁决 (Phase 11f 拦截与修正)

### 防线一：毁灭性的量纲溢出 (The Scaling Bomb) —— 已强制拦截

原始代码中：
```python
STATIC_MEAN = 40.0
target_centered = target_leaky - STATIC_MEAN
```

**事实**：WebDataset 管道中 Target 是原始小数(Raw Decimal)。40 BP = `0.0040`。

- **灾难推演**：对原始小数减 40.0 → `+0.0050` 变成 `-39.995` → FP16 溢出 → 第一个 Step 即 NaN
- **即使转为 BP 空间**：误差 50 BP 的 MSE = 2500，而 λ_s = 1e-3，L1 惩罚微乎其微 → 模型抛弃 Sparsity 约束

**修正**：统一转换到 BP 空间，除以 SCALE_FACTOR (10000) 将 MSE 量级压回 0.1~1.0

### 防线二：MSE 微观噪音放大器 —— 强制加装物理熔断器

- A 股 L1 盘口有大量微观结构噪音（异常大单、洗盘撤单、交易所数据毛刺）
- 无界 MSE 对 1000 BP 跳价毛刺产生 1,000,000 误差和 2000 核弹级梯度
- 两三个毛刺即可炸毁数千次迭代积累的微弱拓扑权重

**修正**：强制钳制在 ±500 BP（A 股天地板范围内），允许真 Alpha 区间内无界重赏但斩断离谱毛刺

### 防线三：不斩断捷径，重赏无济于事 (The Bypass Paradox)

- 面临巨大 MSE 误差时，优化器寻找"阻力最小路径"
- 如果不物理切断后门，模型为极速降低 MSE 只会更疯狂放大 SRL 直通权重
- **裁决**：Phase 11f 训练前，必须在 forward 算子中硬性剥离并物理切断跨过 z_core 的全局特征旁路

### Phase 11f 最终部署版本：compute_spear_loss_unbounded_audited

```python
import torch
import torch.nn.functional as F

def compute_spear_loss_unbounded_audited(raw_logits, target, z_core, lambda_s=1e-3):
    """
    Phase 11f: The Unbounded Spear (审计修正版)
    在释放无界梯度的同时，加装物理熔断与量纲护盾。
    """
    pred = raw_logits.float().view(-1)
    tgt = target.float().view(-1)
    z_core = z_core.float()
    
    # 1. 渗漏遮罩 (Leaky Blinding)
    target_leaky = torch.where(tgt > 0, tgt, tgt * 0.1)
    
    # 2. [修正] 统一投影到 BP 空间 (解决量纲与 L1 碾压问题)
    pred_bp = pred * 10000.0
    tgt_leaky_bp = target_leaky * 10000.0
    
    # 3. 静态置零 (Static Global Centering) 摧毁 Beta 走私
    STATIC_MEAN_BP = 40.0
    target_centered_bp = tgt_leaky_bp - STATIC_MEAN_BP
    
    # 4. [修正] 物理极值熔断 (Physical Outlier Clipping)
    # 容忍 500 BP (5%) 的巨幅真实波动，切断 >500 BP 的突发数据毛刺与错单噪声
    target_centered_bp = torch.clamp(target_centered_bp, min=-500.0, max=500.0)
    
    # 5. [修正] 尺度对齐的无界平方梯度 (Scaled Unbounded MSE)
    # 除以 10000 (100 BP 的平方)，将 MSE 从数千量级缩放至 0.1~1.0
    # 确保 lambda_s (1e-3) 不会被主梯度暴雨彻底冲毁
    SCALE_FACTOR = 10000.0
    loss_err = F.mse_loss(pred_bp, target_centered_bp) / SCALE_FACTOR
    
    # 6. 压缩即智能 (Epiplexity)
    z_core_safe = torch.clamp(z_core, min=-20.0, max=20.0)
    s_t = torch.norm(z_core_safe, p=1, dim=-1).mean()
    
    total_loss = loss_err + lambda_s * s_t
    
    return total_loss, loss_err, s_t, pred
```

### 终极执行决议

1. `autoresearch` 分支所有架构修复正式沿用
2. 公理入库：C-054 静态置零防线、C-055 有界梯度的平庸之恶、C-056 MSE量纲碾压（注：OMEGA_LESSONS.md 中这些编号已被占用，需分配新编号 C-057/058/059）
3. `best.pt` 保存指标强制变更为 **D9-D0 Spread**
