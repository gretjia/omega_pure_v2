# 架构师指令：度量崩塌终极宣判 + Softmax Portfolio Loss 维度跃迁

- **日期**: 2026-03-30
- **来源**: 独立架构师（用户粘贴，非 Google Docs）
- **主题**: Phase 9 v1-v4 全面失败病理解剖 + Pearson Loss 死路宣判 + Softmax Portfolio Loss 终极替代方案

---

## 0x00 总裁决

架构师对 Phase 9 Evidence Package 的独立判决：

1. **核心洞察（SRL+FWT 拓扑检测主力建仓）10000% 正确，数学核心未废**
2. **非对称 Pearson Loss 在物理底层是绝对死路** — 不是实现问题，是数学原理问题
3. **立即 KILL v4 Job (6638582498177581056)**，停止算力燃烧
4. **维度跃迁**：从 Pearson IC Loss → Softmax Portfolio Loss（Learning to Rank 范式）

---

## 0x01 病理解剖：Train IC 暴涨 + Val IC 归零的根因

### 真相 1：皮尔逊的"尺度免疫"与作弊漏洞

Pearson IC 的数学本质是通过全局方差与协方差计算相关性。致命漏洞：**无论预测值放大 10000 倍，IC 值不变。**

当 `dampening=0.3` 把跑输大盘的 Target 压扁 70% 后：
- 网络发现作弊捷径：不需要压缩主力建仓规律，只需在 Training Batch 里死记硬背涨幅最大的妖股，把预测值推向正无穷
- **Train IC 暴涨**：极个别推向正无穷的预测值主导协方差分子
- **Std(ŷ) 爆炸**：预测值为逼近正无穷，方差疯狂膨胀
- **Val IC 归零**：死记硬背的噪音在 OOS 中完全失效

**结论：非对称 Pearson 从数学根基上诱导模型放弃"压缩"，走向"死记硬背的高熵作弊"（Reward Hacking）**

### 真相 2：锚定权重的"梯度精神分裂"

anchor_weight=0.01 (v4) 是"头痛医头"：
- Pearson 喊："把预测值拉向正无穷！榨取非对称协方差！"
- MSE Anchor 喊："滚回 0 均值正态分布！"
- anchor 太弱 → Pearson 赢 → Std(ŷ) 爆炸
- anchor 够强 → MSE 主导 → 退化回平庸的对称预测器
- **不存在平衡点**，这是数学上的结构性矛盾

### 真相 3：hd=64 底盘无罪

T29 (hd=64) 在 Phase 6 达成 OOS/IS=1.00 零过拟合。64 维隐空间是 A 股微观结构的"物理常数"。
- 扩大 hd=128 = 给网络逃避压缩的借口
- 泛化退化 100% 是 Loss 函数诱导作弊导致的
- **底盘无罪，发动机有罪**

---

## 0x02 哲学大一统：真正的"非对称压缩"

A 股物理世界的信息论本质：
- **主力建仓（Accumulation）**: TWAP 冰山单吸筹 → 时空上极度低熵（高度规律、极度可压缩）
- **主力派发 + 散户踩踏（Distribution）**: 涨停诱多 + 情绪崩溃 → 时空上极度高熵（纯粹混乱、不可压缩）

**对称 Loss 的死局**: 逼迫 hd=64 瓶颈同时压缩低熵建仓和高熵派发 → 高熵噪音塞满并污染脑容量

**正确路径**: 不篡改 Target 数据（掩耳盗铃），而是让网络在梯度下降时"主动"对高熵派发噪音闭眼，100% 算力集中在低熵建仓信号

---

## 0x03 维度跃迁：Softmax Portfolio Loss

抛弃 Pearson，换上 Learning to Rank 范式的"横截面 Softmax 组合损失"：

```python
import torch

def softmax_portfolio_loss(pred, target_cs_z, temperature=1.0, l2_weight=1e-4):
    """
    Softmax 截面组合期望收益损失 (ListMLE Ranking Loss)
    物理目标：完美契合"只做多"的非对称交易法则。
    彻底免疫尺度爆炸，物理屏蔽高熵噪音。
    """
    pred_flat = pred.view(-1)
    # 第一铁律：保留原始绝对对称的 target_cs_z，严禁任何 dampening 篡改物理真相
    target_flat = target_cs_z.view(-1)

    # 1. 资金分配投影 (The Epiplexity Filter)
    # 物理意义：预测分越高的股票，分配的虚拟资金权重呈指数级暴涨
    # 减去 max 纯为防止 exp 数值溢出（Softmax 标准操作）
    pred_stable = pred_flat - pred_flat.max().detach()
    weights = torch.softmax(pred_stable / temperature, dim=0)

    # 2. 模拟组合的真实期望超额收益
    # 核心非对称性：最高权重给暴涨股(主力建仓) → Loss 急剧下降
    # 误把权重给阴跌股(高位派发) → 庞大权重×真实负收益 = 毁灭性惩罚
    expected_portfolio_return = torch.sum(weights * target_flat)

    # 3. 极微弱的 L2 约束 (取代 MSE Anchor，防止 logits 无意义平移)
    l2_penalty = l2_weight * torch.mean(pred_flat ** 2)

    # 4. 压缩即智能：最大化组合收益 = 最小化负收益
    return -expected_portfolio_return + l2_penalty
```

### 为什么是"压缩即智能"的终极体现

Softmax 是指数级"赢家通吃"：
- 预测排名后 50% 的阴跌股 → Softmax 权重趋近 0
- **权重为 0 → 反向传播梯度为 0 → 自动切断对高熵派发噪音的学习**
- hd=64 的全部脑容量 100% 用于压缩低熵拓扑（SRL + FWT 检测的主力建仓）

### 与 Pearson Loss 的本质区别

| 维度 | Pearson IC Loss | Softmax Portfolio Loss |
|------|----------------|----------------------|
| 尺度免疫 | 有（致命漏洞） | 无（Softmax 归一化到概率分布） |
| 非对称性 | 需要 dampening 篡改 Target | 内生于赢家通吃的指数结构 |
| Std(ŷ) 爆炸 | anchor 太弱就爆炸 | L2 + Softmax 双重约束 |
| 梯度冲突 | Pearson vs MSE anchor 精神分裂 | 单一目标，无冲突 |
| 与交易逻辑对齐 | 统计相关性 ≠ 交易盈利 | 直接优化组合收益 |

---

## 0x04 z_sparsity 作为终极交易扳机

架构师指出 Phase 7 报告中的关键缺失：`z_sparsity` (MDL compression metric) 未包含在推理输出中。

物理含义：
- **高 Sparsity（大量神经元静默，极少数亮起）**: 模型遇到经典的低熵主力建仓算法，用极短的"代码长度"完美压缩信号 → **主力控盘铁证**
- **低 Sparsity（神经元散乱全亮）**: 盘口全是散户乱战，噪音太高，无法有效压缩

终极实盘交易扳机（The Crucible Logic）：
```python
if (Prediction_Rank 位于 Top 10%) AND (z_sparsity > 极高压缩率阈值):
    Execute_Long_Swing_Trade()
```

---

## 0x05 架构师最终出征令

**绝对纪律 4 条：**

1. **KILL v4**: 立刻终结 GCP 上 Job 6638582498177581056 的算力燃烧
2. **还原 Target 纯洁性**: DataLoader 中彻底删除 `dampening` 逻辑，把客观真实的 `target_cs_z` 还给模型
3. **换上 Softmax 引擎**: `softmax_portfolio_loss` 植入核心，移除 Pearson 和 MSE Anchor
4. **死锁 T29 原生架构**: 不许动 `hd=64`，保留微弱 `lambda_s=1e-7`

### train_step 极简重构

```python
# 彻底删除 target dampening，删除 pearson，删除 anchor_loss
loss = softmax_portfolio_loss(pred, target_cs_z) + (args.lambda_s * S_T)
```

### 监控指标变更

- **不再看 Train IC** — 它在 Softmax Loss 下不是有效监控指标
- **盯 Train Loss** — 它直接代表做多组合的负预期真实超额收益
- **盯 Val Loss** — OOS 组合收益是泛化的直接度量

---

## 对 current_spec.yaml 的影响

### 需要变更的字段：

1. `training.loss`: "Leaky Asymmetric IC Loss + Dampened MSE anchor + MDL" → "Softmax Portfolio Loss + L2 penalty + MDL"
2. `training.loss_function`: 完整替换为 softmax_portfolio_loss 公式
3. `training.downside_dampening`: **删除**（0.3 → 不存在）
4. `training.anchor_weight`: **删除**（被 l2_weight=1e-4 取代）
5. `training.lambda_s`: 0.001 → 1e-7（架构师指定）
6. `hpo.metric`: "1-IC" → 需要重新定义（基于 portfolio return）
7. `hpo.search_space.anchor_weight`: **删除**

### 不变的字段：

- `physics.delta`: 0.5（Layer 1 永恒）
- `physics.c_default`: 0.842（Layer 2 回退值）
- `tensor.shape`: [B, 160, 10, 10]
- `model_architecture`: Omega-TIB 四层不变
- `backtest`: 全部约束不变
