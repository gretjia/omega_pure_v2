# 架构师指令：Phase 11d 双轨复苏协议 (Resuscitation Protocol)

**日期**: 2026-04-01
**来源**: 首席架构师直接通信（对话内粘贴）
**公理影响**: AXIOM UPDATE REQUIRED — lambda_s + huber_delta Layer 2 变更
**触发**: Phase 11c 烟测揭露 216x 仪表盘幻觉 + 方差坍缩 (Variance Collapse)

---

## Part 1: 架构师独立物理诊断

### 1. Huber 的平庸之墙 (The Huber Ceiling)
A 股的非对称右尾是绝对的 Alpha 来源（主升浪单日可达 +200 BP 甚至更高）。当 δ=50 时，即使模型撞见了一个真正的大牛股，传导回网络的梯度也被死死锁死在 50。对于那 17.5% 的高价值样本，模型完全丧失了追捕的动力，因为追捕的暴利被严重削峰了。

### 2. λ_s 的断头台效应 (The MDL Guillotine)
最大梯度被卡死在 50，经过层层反向传播到瓶颈层 z_core 时已经非常微弱，而悬在头顶的 L1 结构税 λ_s 却高达 1e-3。

### 3. 模型的全局最优解作弊 (The Global Minimum Exploit)
反向传播算了一笔极其理性的账："为了拿到被削去大半的微弱梯度奖励而去激活神经元，我却要为每一根激活的神经元支付极其高昂的 λ_s 惩罚，这根本是一笔亏本买卖！"

因此，优化器极其聪明地自我植物人化：彻底关闭 z_core（z_sparsity 降至 0.44% 以实现绝对免税），然后单独利用最后一层 Linear 的 Bias，输出 clamp(target, 0) 的全市场正向均值（~30 BP）。

### 4. 为何"压缩即智能"理论在此次未通过？
当特征层大面积坏死时，里面残存的微小稀疏度波动，仅仅是底层的量子浮点噪音（Floating-point Noise），根本没有流淌任何提纯后的拓扑信号。你无法在一具死尸上测量智商，这就是 Epiplexity 理论在本次低端区域失效的根本原因。

---

## Part 2: Phase 11d 执行指令

### 执行指令 1：修改 Spec 参数 (Dual-Track Deployment)

```yaml
training:
  lambda_s: 1.0e-4           # [Config A] 降低10x。若为 Config B 则设为 1.0e-5
  loss_function:
    name: "pointwise_spear"
    huber_delta: 200.0       # 放大4x，释放 97.6% 样本的全额 MSE 梯度
```

### 执行指令 2：数学核心解缚 (Unshackling the Core)

确保 compute_spear_loss 已经开放了 huber_delta 超参的控制权：

```python
def compute_spear_loss_pointwise(raw_logits, target, z_core, lambda_s=1e-4, huber_delta=200.0):
    pred = raw_logits.float().view(-1)
    target = target.float().view(-1)
    z_core = z_core.float()
    
    target_acc = torch.clamp(target, min=0.0)
    loss_spear = F.huber_loss(pred, target_acc, delta=huber_delta)
    
    z_core_safe = torch.clamp(z_core, min=-20.0, max=20.0)
    s_t = torch.norm(z_core_safe, p=1, dim=-1).mean()
    
    total_loss = loss_spear + lambda_s * s_t
    return total_loss, loss_spear, s_t, pred
```

### 执行指令 3：部署预警哨兵 (The Variance Sentinel)

在验证循环中植入方差坍缩哨兵：

```python
pred_std_bp = preds.std().item()

if pred_std_bp < 10.0 and preds.numel() > 10:
    logger.error(f"VARIANCE COLLAPSE DETECTED: pred_std={pred_std_bp:.2f} BP < 10.0 BP.")
    logger.error("Model has undergone 'Brain Death'. Decrease lambda_s or increase Huber delta!")
elif pred_std_bp < 30.0:
    logger.warning(f"LOW VARIANCE: pred_std={pred_std_bp:.2f} BP. Nearing collapse threshold.")
else:
    logger.info(f"HEALTHY: Variance restored: pred_std={pred_std_bp:.2f} BP.")
```

### 执行指令 4：经验沉淀入库

> **[C-051] 量纲剧变与方差坍缩 (Dimensionality & Variance Collapse)**: 当移除归一化（如 Softmax/Z-score）或更换 Loss 函数（如改为 Pointwise Huber 绝对 BP）时，Loss 的量纲和梯度尺度会发生剧变。此时必须同步实测重标定正则化强度（λ_s）与截断超参（Huber δ）。否则，若正则化的结构税远大于特征提取的梯度奖励，模型将触发"方差坍缩"，主动关闭特征层（z_sparsity 极低）并输出全市场均值常数以逃避惩罚。同时，仪表盘绝不可使用旧的逆向缩放乘数，以防严重的视觉幻觉。

---

## Part 3: 架构师最终决断

**全线放开限制，启动 Phase 11d 抢救！**

双轨对照实验：
- Config A: λ_s=1e-4, δ=200 (平衡)
- Config B: λ_s=1e-5, δ=200 (激进)

成功标准：pred_std 从 5.6 BP 拉升至 30-150 BP 健康区间，z_sparsity 从 <1% 回到 2-10%，D9-D0 spread 越过 30 BP 成本覆盖线。
