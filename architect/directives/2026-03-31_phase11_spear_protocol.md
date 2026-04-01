# Phase 11: 建仓之矛 (The Spear Protocol) — 第二份指令 (取代 Asura P2)

**日期**: 2026-03-31
**来源**: 首席架构师 (对话直传)
**公理影响**: AXIOM UPDATE REQUIRED (Layer 2 — 训练目标 + 损失函数 + 架构)
**关系**: 保留 Asura Protocol 的 P0/P1，**取代 P2** 为单头 Spear-first 策略

---

## 理论重构: 从"时间有界熵"审判 Phase 10

基于《From Entropy to Epiplexity》文献视角:

1. **归纳的代价 (Cost of Induction, 5.3.1节)**:
   模型要最大化似然(拟合 Softmax 全分布)，必须学会"归纳"。但归纳"主力长达数月的隐蔽建仓"需极高认知复杂度(极精密的 2D 拓扑提取)。

2. **Softmax 的伪随机作弊 (CSPRNG 效应)**:
   模型发现归纳右尾(建仓)太难，但识别左尾(大跌破位)特征粗暴。为抢夺 Softmax 横截面权重，它选择捷径: 对看不懂的右尾噪音(高 H_T)，不做结构压缩，而像伪随机数生成器一样暴力膨胀预测值绝对尺度(Logits 放大 22.9x)来盲目下注。

3. **真相**: 模型越给出极高 |pred|，z_sparsity 压缩率越低(瞎赌)，IC 为负。它不是在选股，是在通过死记硬背左尾噪音骗取 Softmax 低 Loss。

**架构师裁决**: "现阶段只训练出找到主力建仓的 Epiplexity，把主力出货放到下一个阶段。" 试图用一个微小认知瓶颈同时压缩"贪婪"与"恐惧"必然导致任务坍塌。

---

## P0 战役: Epiplexity Gate (与第一份指令相同)

在 `phase7_simulate.py` 每日截面选股逻辑中植入"认知门控":
```python
# 1. 剥夺畸形尺度的作弊资格
filtered = today_signals[today_signals['pred_bp'].abs() < 1000]

# 2. Epiplexity 认知门控
median_compression = filtered['z_sparsity'].median()
high_epiplexity_pool = filtered[filtered['z_sparsity'] <= median_compression]

# 3. 在"真智能"池中选 Top
ranked = cross_sectional_rank(high_epiplexity_pool)
new_longs = ranked.nlargest(max_positions)
```

**验收标准**: 剔除高熵噪音后，Asymmetry Ratio 从 1.30 质的跃升(逼近 1.8-2.0)。

---

## P1 战役: 数学核心重铸 — 建仓之矛 (The Spear Compressor)

### 1. 目标空间的绝对遮罩 (Asymmetric Target Blinding)
```python
target_accumulation = torch.clamp(target, min=0.0)
```
**物理意义**: 跌 1% 和跌 10% 在模型看来完全相同(全为 0)。避开大跌不再有任何梯度奖励。唯一生存方式: 从 5000 只股票中找到真正会拉升的大牛股。

### 2. 方差之枷 (The Variance Straitjacket)
```python
eps = 1e-8
logit_mean = raw_logits.mean(dim=0, keepdim=True)
logit_std = raw_logits.std(dim=0, keepdim=True) + eps
locked_logits = (raw_logits - logit_mean) / logit_std
```
无论网络内部多狂妄，输出 Std 永远被锁死在 1.0。

### 3. 纯粹的建仓 MDL 损失 (Accumulation Epiplexity Loss)
```python
def compute_spear_loss(locked_logits, target_accumulation, z_core, lambda_s=1e-7):
    eps = 1e-8
    # 构造真实的横截面资金分配概率 (只包含右尾)
    target_prob = target_accumulation / (target_accumulation.sum() + eps)
    
    # 预测概率 (温度 1.0，由人类掌控尖锐度)
    pred_prob = F.softmax(locked_logits, dim=0)
    
    # H_T: 交叉熵残差 (捕捉建仓)
    loss_acc = -torch.sum(target_prob * torch.log(pred_prob + eps))
    
    # S_T: 压缩即智能 MDL 惩罚
    s_t = torch.norm(z_core, p=1, dim=-1).mean()
    
    return loss_acc + lambda_s * s_t, loss_acc, s_t
```

### 架构师的绝杀巧思 — 熊市自动静默
当遇到单边熊市 (`target_accumulation.sum() == 0`)，`target_prob` 变成均匀分布(无意义)，`loss_acc` 梯度极小。主导梯度只剩 MDL 惩罚项 `s_t`。模型在纯噪音市场中被 L1 惩罚强行关闭所有神经元，安全地"什么都不学"(全输出 0)，完美规避强行拟合高熵熊市噪音的陷阱！

---

## 架构师下一步指令
1. **立即执行 P0** (Epiplexity Gating 回测) — 不动训练代码
2. 拿到 P0 证据包后启动 P1 (修改 omega_epiplexity_plus_core.py + train.py)
3. Shield Head 推迟到 Phase 12
