# Phase 11: 建仓之矛最终判决 (The Spear — Final Verdict & Deployment Order)

**日期**: 2026-03-31
**来源**: 首席架构师 (对话直传)
**公理影响**: AXIOM UPDATE REQUIRED (Layer 2 — temperature 0.1, 确认 Spear Loss)
**关系**: 确认 phase11_spear_protocol, 宣判 P0 FAILED, 授权 Phase 11 部署

---

## P0 终极判决: Softmax 的"赌场剥削 (Casino Exploit)"

### 架构师死因诊断

Phase 10 模型不是交易员，是利用 Softmax 漏洞的"高波动率赌徒":

1. **劣币驱逐良币 (Logit Inflation)**:
   - 真智能 (Z-D9 高压缩): IC=+0.009, |pred|=2000 BP — 准但弱
   - 纯噪音 (Z-D0 低压缩): IC=-0.005, |pred|=6956 BP — 错但强
   - Softmax e^x 指数效应: e^6956 瞬间碾压 e^2000, 霸占 99% 资金权重

2. **Gating 失败的必然性**:
   - 44% 年化 = 4540 BP 方差硬吃 2024 牛市极少数尾部波动 (纯 Beta)
   - "高预测值"已和"瞎赌博"物理绑定，切断赌博通道 = 拔掉利润引擎
   - 剩余"真智能"区间绝对值太小，在原版 Softmax 中分不到钱

**终极判决: 事后过滤救不了底层被尺度腐蚀的模型。自由尺度 Softmax 在肥尾市场中必定坍塌为赌场。必须在梯度下降源头实施物理阉割。**

---

## 核心物理防线: 三重枷锁 (The Three Shackles)

### 1. 非对称目标遮罩 (Asymmetric Target Blinding)
```python
target_acc = torch.clamp(target, min=0.0)
```
所有下跌归零。避险无梯度奖励。要么找到拉升，要么什么都不做。

### 2. 横截面方差之枷 (The Variance Straitjacket)
```python
logit_mean = raw_logits.mean(dim=0, keepdim=True)
logit_std = raw_logits.std(dim=0, keepdim=True) + eps
locked_logits = (raw_logits - logit_mean) / logit_std
```
Logits 锁死在 N(0,1)。终结 6956 BP 极值作弊。唯一出路: 压缩拓扑特征提高排名。

### 3. 温度控制 (Temperature-Scaled Softmax)
```python
pred_prob = F.softmax(locked_logits / temperature, dim=0)  # temperature=0.1
```
N(0,1) 的 Softmax 太平均，T=0.1 将 1σ 放大 10 倍恢复尖锐度。集中度由人类控制。

---

## 最终代码蓝图 (Bulletproof)

```python
def compute_spear_loss(raw_logits, target, z_core, temperature=0.1, lambda_s=1e-7):
    eps = 1e-8
    
    # 1. 目标遮罩
    target_acc = torch.clamp(target, min=0.0)
    target_sum = target_acc.sum()
    
    # 2. 方差之枷
    logit_mean = raw_logits.mean(dim=0, keepdim=True)
    logit_std = raw_logits.std(dim=0, keepdim=True) + eps
    locked_logits = (raw_logits - logit_mean) / logit_std

    # 3. 建仓交叉熵
    if target_sum <= eps:
        # 熊市: 梯度仅来自 MDL, 模型自动静默
        loss_spear = torch.tensor(0.0, device=raw_logits.device, requires_grad=True)
    else:
        target_prob = target_acc / target_sum
        pred_prob = F.softmax(locked_logits / temperature, dim=0)
        loss_spear = -torch.sum(target_prob * torch.log(pred_prob + eps))
        
    # 4. MDL 压缩
    s_t = torch.norm(z_core, p=1, dim=-1).mean()
    total_loss = loss_spear + lambda_s * s_t
    
    return total_loss, loss_spear, s_t, locked_logits
```

---

## 执行路线图

**步骤 1: 本地代码清灰**
- simulate 恢复标准 Top 20% / Max 50 截面无门控逻辑
- P0 完成历史使命，无需保留 z_sparsity 过滤

**步骤 2: 云端重铸 (Phase 11 Vanguard V6)**
- 植入 compute_spear_loss 到 GCP 训练管道
- 超参: temperature=0.1, lambda_s=1e-7, hd=64 (架构不变)
- g2-standard-8, 20 Epochs

**步骤 3: 物理学验收断言**
- 训练中: Val Std_yhat (locked_logits) 永远死贴 1.0
- 回测后: z_sparsity 与 IC 的负相关被扭转, Asymmetry 突破 1.30 死锁
