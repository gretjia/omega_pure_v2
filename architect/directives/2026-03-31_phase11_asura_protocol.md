# Phase 11: 阿修罗协议 (The Asura Protocol) — 第一份指令

**日期**: 2026-03-31
**来源**: 首席架构师 (对话直传)
**公理影响**: AXIOM UPDATE REQUIRED (Layer 2 — 训练损失 + 架构 + 回测)
**状态**: P2 被第二份指令 (Spear Protocol) 取代，P0/P1 保留

---

## 架构师对 Phase 10 的理论诊断

Phase 10 的 44.02% 年化和 2.55 Sharpe 是"虚假繁荣":
- **发现 3 被定性为"最伟大的物理学定律"**: 低压缩=负 IC；高 |pred|=低压缩。完美证实"压缩即智能"公理
- **物理真相**: 模型遇到高熵噪音时无法提取紧凑结构(低压缩/高L1范数)，但在 Softmax 逼迫下选择"背诵噪音"并暴力放大预测值(Logit Inflation 4540 BP)
- **左尾截断本质**: 单头网络发生"任务坍塌"——把所有算力用来识别"必死局"(左尾压缩)，以此骗取 Softmax 低 Loss，而没有去寻找主升浪
- **Asymmetry=1.30 正式宣判单头网络在极端不对称市场中的物理天花板**

## P0 战役: 物理熔炉的终极压榨 (Epiplexity Gating)

**架构师指令**: 无需重新训练！在现有 `phase7_simulate.py` 中引入 Epiplexity Gating:
- **执行逻辑**: 每日生成横截面排名时，强行剔除 `z_sparsity` 位于后 50% (低压缩/高熵) 的股票
- **物理准则**: 剥夺模型的"赌徒资格"。没看懂(没压缩)就禁买，不管 Softmax 预测值多高
- **目的**: 观察切断高熵赌博后，Asymmetry 能否从 1.30 向上突破

## P1 战役: 横截面方差之枷 (The Variance Straitjacket)

**诊断根因**: Softmax 让 Top-1 权重逼近 0.98，通过无限放大极差 (Std_pred 暴增 22.9x)。L2 mean-shift 和 MDL 惩罚 (λ=1e-7) 被 Softmax 的巨大梯度淹没。

**架构师重铸**: 在网络输出进入 Softmax 前，强行锁死横截面的均值和方差:
```python
eps = 1e-8
spear_mean = raw_logits.mean()
spear_std = raw_logits.std() + eps
locked_logits = (raw_logits - spear_mean) / spear_std
```
- 物理效果: Std_yhat 永远被锁死在 1.0
- 逼迫模型退回 Epiplexity 瓶颈层，老实压缩特征，提高真实排名准确率

## P2 战役: 双头阿修罗 (The Two-Headed Asura)

**注意: 此 P2 被第二份指令 (Spear Protocol) 取代。保留以下内容作为设计历史记录。**

### 架构蓝图

```python
class TwoHeadedAsuraCompressor(nn.Module):
    def __init__(self, raw_feature_dim, hidden_dim, window_size=(4,4)):
        super().__init__()
        # 共享底层
        self.srl_inverter = AxiomaticSRLInverter()
        self.input_proj = nn.Linear(raw_feature_dim + 1, hidden_dim)
        self.tda_layer = FiniteWindowTopologicalAttention(hidden_dim, window_size)
        
        half_dim = hidden_dim // 2
        
        # Head 1: The Spear (主攻右尾)
        self.spear_bottleneck = nn.Sequential(
            nn.Linear(hidden_dim, half_dim), nn.GELU(),
            nn.Linear(half_dim, half_dim // 2))
        self.spear_decoder = nn.Linear(half_dim // 2, 1)
        
        # Head 2: The Shield (主防左尾)
        self.shield_bottleneck = nn.Sequential(
            nn.Linear(hidden_dim, half_dim), nn.GELU(),
            nn.Linear(half_dim, half_dim // 2))
        self.shield_decoder = nn.Linear(half_dim // 2, 1)
```

### 联合损失函数
```python
def compute_asura_loss(locked_spear_logits, prob_crash, target, z_spear, z_shield, lambda_s=1e-7):
    temperature = 0.1
    portfolio_weights = F.softmax(locked_spear_logits / temperature, dim=0)
    loss_spear = -torch.sum(portfolio_weights * target)
    
    is_crash = (target < -150.0).float()
    loss_shield = F.binary_cross_entropy(prob_crash, is_crash)
    
    s_t_spear = torch.norm(z_spear, p=1, dim=-1).mean()
    s_t_shield = torch.norm(z_shield, p=1, dim=-1).mean()
    
    total_loss = loss_spear + loss_shield + lambda_s * (s_t_spear + s_t_shield)
    return total_loss, loss_spear, loss_shield, s_t_spear
```

### 实盘决断铁律
```
if prob_crash > 0.5: Force Close & Ban Entry
```
否决头一票否决权。

---

## 架构师下一步指令
1. 立即执行 P0 (Epiplexity Gating 回测)
2. 确认 P1/P2 后授权修改核心代码
