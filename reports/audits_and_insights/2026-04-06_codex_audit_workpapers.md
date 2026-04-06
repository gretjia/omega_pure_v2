# OMEGA-TIB 外部审计底稿 — ���包含版
**编制日期**: 2026-04-06
**编制��**: Claude Opus 4.6 (5-Agent研究) + Codex GPT-5.4 (数据复核)
**审计对象**: Omega-TIB 模型 (24,581 参数)，Phase 3 至 Phase 13 全生命周期
**本文件性质**: 完全自包含——审计��不需要打开任何其他文件或执行 git 命令

---

## 一、完整源码：创世版本 (2026-03-16, commit `f7ccde9`)

```python
# 前代名称: SpatioTemporal2DMAE
# 本项目第���个 commit，从前代��目继承

import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class AxiomaticSRLInverter(nn.Module):
    """物理反演层: Q_hidden = sign(ΔP) × (|ΔP| / (c × σ_D))^2 × V_D"""
    def __init__(self, c_constant: float = 0.842):   # ← ��世版 c 是全局硬编码常数
        super().__init__()
        self.c = c_constant                          # TSE 文献全局平��值
        self.power_constant = 2.0                    # 1/δ = 1/0.5 = 2.0，永恒物理常数

    def forward(self, delta_p, sigma_d, v_d):        # ← 创世版接收 3 个独立张量
        eps = 1e-8
        dimensionless_impact = torch.abs(delta_p) / (self.c * sigma_d + eps)
        q_magnitude = torch.pow(dimensionless_impact, self.power_constant) * (v_d + eps)
        return torch.sign(delta_p) * q_magnitude

class FiniteWindowTopologicalAttention(nn.Module):
    """有限窗口2D注意力——绝对禁止1D展平"""
    def __init__(self, dim, window_size=(4, 4), num_heads=4):  # ← 创世版窗口 (4,4)
        super().__init__()
        self.dim = dim
        self.window_t, self.window_s = window_size
        self.num_heads = num_heads
        self.qkv = nn.Linear(dim, dim * 3, bias=False)
        self.proj = nn.Linear(dim, dim)
        self.scale = (dim // num_heads) ** -0.5
        # ← 创世版：无 RPB (相对位置偏��)。17分钟后的 commit 8105a08 才添��

    def forward(self, x_nd):
        B, T, S, D = x_nd.shape
        # 窗口分割 → 窗口内 QKV 注意力 → 还原
        # (省略窗口分割/padding/还原代码，与当前版相��但无 RPB 加法)
        ...

class OmegaMathematicalCompressor(nn.Module):
    """压缩器主体���SRL → FWT → Bottleneck → 全局均值池�� → 预测"""
    def __init__(self, raw_feature_dim, hidden_dim, window_size=(4, 4)):
        super().__init__()
        self.srl_inverter = AxiomaticSRLInverter()
        self.input_proj = nn.Linear(raw_feature_dim + 1, hidden_dim)  # ← 创世版：外部传入 raw_feature_dim
        self.tda_layer = FiniteWindowTopologicalAttention(hidden_dim, window_size)
        self.epiplexity_bottleneck = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim // 4)
        )
        self.intent_decoder = nn.Linear(hidden_dim // 4, 1)

    def forward(self, price_impact_2d, raw_features_2d, sigma_d, v_d):  # ← 创世版：4 个独立输入
        with torch.no_grad():
            q_metaorder = self.srl_inverter(price_impact_2d, sigma_d, v_d).unsqueeze(-1)
        native_manifold = torch.cat([raw_features_2d, q_metaorder], dim=-1)
        x = self.input_proj(native_manifold)
        structured_features = self.tda_layer(x)
        z_core = self.epiplexity_bottleneck(structured_features)
        pooled_z = torch.mean(z_core, dim=[1, 2])     # ← 创世版：全局均值池化
        main_force_prediction = self.intent_decoder(pooled_z)
        return main_force_prediction, z_core

def compute_epiplexity_mdl_loss(prediction, target, z_core, lambda_s=1e-3):  # ← 创世版 λ_s=1e-3
    h_t = F.mse_loss(prediction.squeeze(), target)     # ← 创世版用 .squeeze() (后证明有 bug)
    s_t = torch.norm(z_core, p=1, dim=-1).mean()
    return h_t + lambda_s * s_t, h_t, s_t
```

---

## 二、完整源码：当前版本 (Phase 13, 2026-04-04+)

### 2.1 数学核心 (`omega_epiplexity_plus_core.py`, 317 行, commit `fd3b041`)

```python
"""
OMEGA-TIB: Topological Information Bottleneck (Phase 0.5 Update)
Mathematical core: SRL Physics → FWT Topology → MDL Compression → Intent Prediction
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class AxiomaticSRLInverter(nn.Module):
    """
    Layer 1 Physics: Square Root Law inverse decrypter.
    Q_hidden = sign(ΔP) × (|ΔP| / (c_i × σ_D))^2 × V_D
    δ = 0.5 is eternal (POWER_INVERSE = 2.0). Never learnable.
    c is per-stock (from a_share_c_registry.json), passed as c_friction tensor.
    """
    def __init__(self):                          # ← 当前版：c 不再硬编码
        super().__init__()
        self.power_constant = 2.0                # 1/δ = 1/0.5 = 2.0 (eternal)

    def forward(self, delta_p, sigma_d, v_d, c_friction):  # ← 当前版：+c_friction 参数
        eps = 1e-8
        c = c_friction.expand_as(delta_p)        # [B,1] → [B,T]
        dimensionless_impact = torch.abs(delta_p) / (c * sigma_d + eps)
        q_magnitude = torch.pow(dimensionless_impact, self.power_constant) * (v_d + eps)
        return torch.sign(delta_p) * q_magnitude


class FiniteWindowTopologicalAttention(nn.Module):
    """Layer 2 Topology: Finite Window 2D attention. NO 1D flattening."""
    def __init__(self, dim: int, window_size: tuple = (32, 10), num_heads: int = 4):
        super().__init__()
        self.dim = dim
        self.window_t, self.window_s = window_size    # ← 当前默认 (32,10) 非 (4,4)
        self.num_heads = num_heads
        self.qkv = nn.Linear(dim, dim * 3, bias=False)
        self.proj = nn.Linear(dim, dim)
        self.scale = (dim // num_heads) ** -0.5

        # ← 当前版有 RPB (Swin-style, commit 8105a08 添加)
        self.relative_position_bias_table = nn.Parameter(
            torch.zeros((2 * self.window_t - 1) * (2 * self.window_s - 1), num_heads)
        )
        coords_t = torch.arange(self.window_t)
        coords_s = torch.arange(self.window_s)
        coords = torch.stack(torch.meshgrid([coords_t, coords_s], indexing='ij'))
        coords_flatten = torch.flatten(coords, 1)
        relative_coords = coords_flatten[:, :, None] - coords_flatten[:, None, :]
        relative_coords = relative_coords.permute(1, 2, 0).contiguous()
        relative_coords[:, :, 0] += self.window_t - 1
        relative_coords[:, :, 1] += self.window_s - 1
        relative_coords[:, :, 0] *= 2 * self.window_s - 1
        relative_position_index = relative_coords.sum(-1)
        self.register_buffer("relative_position_index", relative_position_index)
        nn.init.trunc_normal_(self.relative_position_bias_table, std=.02)

    def forward(self, x_nd: torch.Tensor) -> torch.Tensor:
        B, T, S, D = x_nd.shape
        pad_t = (self.window_t - T % self.window_t) % self.window_t
        pad_s = (self.window_s - S % self.window_s) % self.window_s
        if pad_t > 0 or pad_s > 0:
            x_nd = F.pad(x_nd, (0, 0, 0, pad_s, 0, pad_t))
        _, T_pad, S_pad, _ = x_nd.shape

        # 窗口分割: [B, T_pad, S_pad, D] → [B*nW, wt*ws, D]
        x_win = x_nd.view(B, T_pad // self.window_t, self.window_t,
                          S_pad // self.window_s, self.window_s, D)
        x_win = x_win.permute(0, 1, 3, 2, 4, 5).contiguous().view(
            -1, self.window_t * self.window_s, D)

        # 多头注意力
        qkv = self.qkv(x_win).chunk(3, dim=-1)
        q, k, v = map(lambda t: t.view(
            -1, self.window_t * self.window_s, self.num_heads,
            D // self.num_heads).transpose(1, 2), qkv)
        attn = (q @ k.transpose(-2, -1)) * self.scale

        # RPB 加法
        rpb = self.relative_position_bias_table[
            self.relative_position_index.view(-1)
        ].view(self.window_t * self.window_s, self.window_t * self.window_s, -1)
        rpb = rpb.permute(2, 0, 1).contiguous()
        attn = attn + rpb.unsqueeze(0)
        attn = attn.softmax(dim=-1)

        out = (attn @ v).transpose(1, 2).reshape(-1, self.window_t * self.window_s, D)
        out = self.proj(out)

        # 还原窗口结构
        out = out.view(B, T_pad // self.window_t, S_pad // self.window_s,
                       self.window_t, self.window_s, D)
        out = out.permute(0, 1, 3, 2, 4, 5).contiguous().view(B, T_pad, S_pad, D)
        if pad_t > 0 or pad_s > 0:
            out = out[:, :T, :S, :].contiguous()
        return out


class AttentionPooling(nn.Module):                    # ← Phase 13 新增 (commit 481870b)
    """Phase 13 B.1: 可学���注意力池化，替代全局均值池化"""
    def __init__(self, dim: int):
        super().__init__()
        self.W_pool = nn.Parameter(torch.empty(dim))
        self.scale = dim ** -0.5
        nn.init.normal_(self.W_pool, std=0.02)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        B, T, S, D = z.shape
        z_flat = z.view(B, T * S, D)
        scores = (z_flat @ self.W_pool) * self.scale
        weights = torch.softmax(scores, dim=1)
        return torch.einsum('bt,btd->bd', weights, z_flat)


class OmegaMathematicalCompressor(nn.Module):
    """
    Omega-TIB: SRL Physics → FWT Topology → Bottleneck → AttentionPool → Prediction.
    Input: x_2d [B, T, S, 10] + c_friction [B, 1]
    Output: (prediction [B, 1], z_core [B, T, S, hidden//4])
    """
    def __init__(self, hidden_dim: int = 64, window_size: tuple = (32, 10),
                 macro_bypass: bool = False):
        super().__init__()
        self.srl_inverter = AxiomaticSRLInverter()
        self.macro_bypass = macro_bypass
        input_dim = 8 if macro_bypass else 6           # LOB(5) + q(1) [+ V_D(1) + σ_D(1)]
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        self.tda_layer = FiniteWindowTopologicalAttention(hidden_dim, window_size)
        self.tda_pre_ln = nn.LayerNorm(hidden_dim)     # ← Phase 13 B.2: Pre-LN
        self.epiplexity_bottleneck = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim // 4)
        )
        self.intent_decoder = nn.Linear(hidden_dim // 4, 1)
        self.attention_pool = AttentionPooling(hidden_dim // 4)  # ← Phase 13 B.1

    def tda_with_residual(self, x):                    # ← Phase 13 B.2: Pre-LN 残差
        return x + self.tda_layer(self.tda_pre_ln(x))

    def forward(self, x_2d, c_friction):
        B, T, S, C = x_2d.shape
        delta_p = x_2d[:, :, 0, 7]                    # Ch7: 微观价格冲击
        v_d_macro = x_2d[:, :, 0, 8]                  # Ch8: 20日ADV
        sigma_d_macro = x_2d[:, :, 0, 9]              # Ch9: 20日ATR

        # 1. 物理层 (���可学习, fp32)
        with torch.no_grad(), torch.autocast(device_type="cuda", enabled=False):
            q_metaorder = self.srl_inverter(
                delta_p.float(), sigma_d_macro.float(),
                v_d_macro.float(), c_friction.float())
        q_metaorder = q_metaorder.unsqueeze(-1).unsqueeze(-1).expand(B, T, S, 1)

        # 2. 组装流形: LOB(ch0-4) + q_metaorder
        lob_features = x_2d[:, :, :, :5]
        native_manifold = torch.cat([lob_features, q_metaorder], dim=-1)  # [B,T,S,6]
        x = self.input_proj(native_manifold)

        # 3. 拓扑层 (Pre-LN 残差)
        structured_features = self.tda_with_residual(x)

        # 4. 压缩层
        z_core = self.epiplexity_bottleneck(structured_features)

        # 5. 注意力池化 → 预测                          # ← Phase 13: 替代 torch.mean()
        pooled_z = self.attention_pool(z_core)
        main_force_prediction = self.intent_decoder(pooled_z)
        return main_force_prediction, z_core


def compute_ic_loss(prediction, target, ic_epsilon=1e-8):
    """Phase 13 Mandate A: Pearson IC Loss. Loss = -IC. FP32 强制."""
    pred = prediction.float().view(-1)
    tgt = target.float().view(-1)
    if pred.numel() < 2:
        return torch.tensor(0.0, device=pred.device, requires_grad=True)
    pred_centered = pred - pred.mean()
    tgt_centered = tgt - tgt.mean()
    cov = (pred_centered * tgt_centered).mean()
    pred_std = torch.sqrt((pred_centered ** 2).mean() + ic_epsilon)
    tgt_std = torch.sqrt((tgt_centered ** 2).mean() + ic_epsilon)
    ic = cov / (pred_std * tgt_std)
    return -ic
```

### 2.2 训练时特征工���：FRT (Financial Relativity Transform)

这段代码在 `train.py` L:188-217 的 `OmegaTIBWithMasking.forward()` 中执行，**不��� core 文件中**。ETL 输出的原�� LOB 值在此被转换��才进入模型：

```python
# === FRT: 在 GPU 上实时执��，不��� ETL 中 ===
lob = x_2d[:, :, :, :5].float()  # fp32 精度
bid_p, bid_v, ask_p, ask_v, close_p = lob[..., 0], lob[..., 1], lob[..., 2], lob[..., 3], lob[..., 4]

# (1) 微观结��: Bid/Ask 价格 → ��对中间价的 BP 偏差
mid_p = ((bid_p + ask_p) / 2.0).clamp(min=1e-6)
lob[..., 0] = (bid_p - mid_p) / mid_p * 10000.0   # Bid spread ~[-10, -0.5] BP
lob[..., 2] = (ask_p - mid_p) / mid_p * 10000.0   # Ask spread ~[+0.5, +10] BP

# (2) 宏��趋势: Close → 从 t=0 的累计对数收益率 (百分比)
anchor = close_p[:, 0:1, ...].clamp(min=1e-6)
lob[..., 4] = torch.log(close_p.clamp(min=1e-6) / anchor) * 100.0

# (3) 成交量: log1p 压缩 (幂律安全, 范围 [0, ~15])
lob[..., 1] = torch.log1p(bid_v.clamp(min=0.0))
lob[..., 3] = torch.log1p(ask_v.clamp(min=0.0))

# SRL 输出 q_metaorder 经 overflow clamp + symlog 压缩后拼入:
q_metaorder = torch.clamp(q_metaorder, min=-1e12, max=1e12)
q_metaorder = torch.sign(q_metaorder) * torch.log1p(torch.abs(q_metaorder))
native_manifold = torch.cat([lob_features, q_metaorder], dim=-1)  # [B,T,S,6]
```

### 2.3 损失函数 (Phase 13 实际使用)

```python
# train.py L:86-100 — IC Loss wrapper
def compute_ic_loss_wrapper(pred, target, z_core, ic_epsilon=1e-8):
    ic_loss = compute_ic_loss(pred, target, ic_epsilon=ic_epsilon)  # = -Pearson(pred, target)
    # s_t 仅监控，不��与 loss (lambda_s=0, INS-069)
    with torch.no_grad():
        z_core_safe = torch.clamp(z_core.float(), min=-20.0, max=20.0)
        s_t = torch.norm(z_core_safe, p=1, dim=-1).mean()
    return ic_loss, s_t
```

### 2.4 训练循环关键���径 (Phase 13)

```python
# train.py L:351-369 — 核心��向+反向 (no_amp 模式, Phase 13 实际使用)
optimizer.zero_grad(set_to_none=True)
prediction, z_core = model(manifold, c_friction)      # OmegaTIBWithMasking.forward()
total_loss, s_t = compute_ic_loss_wrapper(prediction, target, z_core)
total_loss.backward()
torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)  # grad_clip=1.0
optimizer.step()
scheduler.step()  # OneCycleLR, per-batch stepping

# train.py L:648-655 — 优化器配置
optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-5)
# betas=(0.9, 0.999), eps=1e-8 — 全部 PyTorch 默认值，未显式设置
scheduler = OneCycleLR(optimizer, max_lr=3e-4, total_steps=75000,
                       pct_start=0.05, anneal_strategy='cos', div_factor=100)

# train.py L:598-604 — 训练/验证���割
all_shards = sorted(glob.glob("omega_shard_*.tar"))   # 字母排序
n_train = int(len(all_shards) * 0.8)                  # 前 80%
train_shards = all_shards[:n_train]                    # ~1594 shards
val_shards = all_shards[n_train:]                      # ~398 shards

# train.py L:732-741 — 最佳模型选择
if val_rank_ic > best_rank_ic:                         # Spearman Rank IC 最大化
    best_rank_ic = val_rank_ic
    save_checkpoint(best_path, ...)                     # 保存 best.pt
```

---

## 三、参数计数 (逐层精确计算)

| 组件 | 计算 | ��数�� | 占比 |
|------|------|--------|------|
| input_proj | 6×64 + 64(bias) | 448 | 1.8% |
| post_proj_norm (在wrapper中) | 64×2 (γ+β) | 128 | 0.5% |
| **FWT qkv** | **64��192 (no bias)** | **12,288** | **50.0%** |
| FWT proj | 64×64 + 64(bias) | 4,160 | 16.9% |
| **RPB 表** | **(2×32-1)×(2×10-1)×4 = 63×19×4** | **4,788** | **19.5%** |
| tda_pre_ln | 64×2 | 128 | 0.5% |
| bottleneck L1 | 64×32 + 32 | 2,080 | 8.5% |
| bottleneck L2 | 32×16 + 16 | 528 | 2.1% |
| AttentionPooling W_pool | 16 | 16 | 0.1% |
| IntentDecoder | 16×1 + 1 | 17 | 0.1% |
| **总计** | | **24,581** | 100% |

**注: SRL 物理层 0 参数 (不可学习)**

RPB 表大小验证: (2×32-1)=63, (2×10-1)=19, 63×19=1197 行 × 4 头 = 4,788 ✅

---

## 四、创世→当前 架构��异对照

| 组件 | 创世版 (f7ccde9) | 当前版 (fd3b041) | 变更 Phase |
|------|----------------|-----------------|-----------|
| SRL c | 全���硬编码 0.842 | per-stock c_friction 输入 | Phase 0.5 |
| FWT 窗口 | (4, 4) | (32, 10) | Phase 6 HPO + 65e34d7 |
| FWT RPB | 无 | Swin-style 相对位置偏置 | 8105a08 (+17min) |
| 池化 | `torch.mean(dim=[1,2])` | `AttentionPooling(W_pool)` | Phase 13 B |
| Pre-LN | 无 | `x + tda(LayerNorm(x))` | Phase 13 B |
| post_proj_norm | 无 | `LayerNorm(hd)` 在 wrapper 中 | Phase 12+ |
| 损失 | MSE + λ_s=1e-3 × L1 | IC Loss, λ_s=0 | Phase 13 A |
| FRT | 无 (原始特���直入) | BP偏差/logReturn/log1p | Phase 12+ |
| `.squeeze()` | 用于输出 | 全部替换为 `.view(-1)` | C-050 |
| 模型层数 | **1 层注意力** | **仍然 1 层注意力** | **从未变过** |
| hidden_dim | 未锁定 | 64 (Phase 6 HPO 选出) | Phase 6 |

---

## 五、训练���参数 (Phase 13 精确配置)

| 参数 | 值 | 代码位置 |
|------|-----|---------|
| optimizer | AdamW | train.py L:649 |
| lr | 3e-4 | gcp/phase13_train_config.yaml |
| weight_decay | 1e-5 | train.py L:649 (硬编码) |
| betas | (0.9, 0.999) | PyTorch 默认，未显式设置 |
| eps | 1e-8 | PyTorch 默认，未显式设置 |
| scheduler | OneCycleLR | train.py L:652-654 |
| pct_start | 0.05 (5% warmup) | train.py L:654 |
| anneal_strategy | cos | train.py L:654 |
| div_factor | 100 (起始 LR = 3e-6) | train.py L:654 |
| batch_size | 256 | 无梯度累积 |
| epochs | 15 | steps/epoch = 5000 |
| total_steps | 75,000 | 15 × 5000 |
| grad_clip | 1.0 | train.py L:509 |
| lambda_s | **0** (L1 禁��) | INS-069 |
| mask_prob | **0.0** (masking 禁用) | Phase 13 config |
| AMP | **关闭** (--no_amp) | Phase 13 config |
| dropout | **不存在** | 模型中无任何 dropout 层 |
| seed | 42 | train.py L:524 |
| 硬��� | T4 GPU, Spot | Vertex AI |
| loss precision | FP32 | compute_ic_loss 内强制 .float() |

---

## 六、数据管线

### 6.1 原始数据
- **来源**: A 股 L1 ���笔 + 10 ��� LOB
- **格式**: Parquet, 每文件含 symbol/date/price/vol_tick + 40 �� LOB
- **总量**: 2.2 TB, 743 文件
- **时间**: 20230103 - 20260130 (约 551 交易日)
- **标的**: 沪深全 A 股 (000/001/002/003/300/301/600/601/603/605/688/689)

### 6.2 ETL 关键参数
| 参数 | 值 | 来源 |
|------|-----|------|
| MACRO_WINDOW | 160 bars | omega_etl_v3_topo_forge.py L:52 |
| STRIDE | 20 bars | L:53 |
| ADV_FRACTION | 0.02 | L:54 |
| SPATIAL_DEPTH | 10 | L:55 |
| FEATURE_DIM | 10 | L:56 |
| PAYOFF_HORIZON | 20 bars | L:58 |
| SHARD_MAX_COUNT | 5000 | L:57 |

### 6.3 Target 计算
```
target_bp = (VWAP[N+1+20] - VWAP[N+1]) / VWAP[N+1] × 10000
```
- N+1 延迟: 信号在 bar N 产生���bar N+1 才能执行
- 20 bars ≈ 0.4 交易日

### 6.4 Target 分布 (Phase 14 Step 0 实测, 1,904,747 验证集样本)
| 统计量 | 值 |
|--------|-----|
| Mean | 6.93 BP |
| Std | 189.60 BP |
| Skew | 11.78 |
| **Kurtosis** | **2006.46** |
| Range | [-9035, +42671] BP |
| Data SNR | 6.93/189.60 = 3.655% |

### 6.5 c_friction 摩擦系数
- **标定方法**: OLS ��截距���归 Y=c_i×X, X=√(Q/V_D), Y=ΔP/σ_D
- **c_default**: 0.842 (TSE 文献回退值)
- **__GLOBAL_A_SHARE_C__**: 存于 `a_share_c_registry.json`
- **注意**: registry 文件在 linux1 节点上，omega-vm 上不存在。ETL 运行时找不到文件会 fallback 到 c_default=0.842

### 6.6 数据集规模
| 指标 | 值 |
|------|-----|
| 总 shards | 1,992 |
| 总样本 | ~9.96M |
| 总大小 | ~556 GB |
| 训��� shards | ~1594 (前80%) |
| 验证 shards | ~398 (后20%) |
| 验证样本 | 1,904,747 (精确) |

---

## 七、全 Phase 结果�����册

| Phase | 日期 | Loss | hd | Window | Params | Rank IC | D9-D0 (BP) | pred_std (BP) | 判定 |
|-------|------|------|-----|--------|--------|---------|-----------|-------------|------|
| 3 | 03-24 | Huber+MDL(λ=1e-3) | 128 | (4,4) | ~50K | N/A | N/A | N/A | FVU≈1.0 |
| 5 | ~03-27 | IC | ~20K | (4,4) | ~20K | N/A | -1.67 | — | FAIL 方向错 |
| 6 | 03-29 | IC (70试HPO) | 64 | (32,10)* | 19.7K | +0.0023† | +11.16† | 790† | †复测值 |
| 7 | 03-30 | IC (回测) | 64 | (32,10) | 19.7K | — | +18.08‡ | IQR=20.5 | ‡daily CS |
| 8 | 03-30 | IC (模拟优化) | 64 | (32,10) | 19.7K | — | +18.08 | — | Sharpe=0.66 |
| 9 | 03-30 | Asym Pearson | 64 | (32,10) | ~20K | — | — | 50+ | 7 job 全败 |
| 10 | 03-31 | Softmax PF | 64 | (32,?) | 21.4K | — | +18.42 | 5055 | Beta走私 |
| 11a | 04-01 | Softmax+Zscore | 64 | (32,4) | ~21K | — | — | NaN | 灾难 |
| 11c | 04-01 | Huber(50) | 64 | (32,4) | 21.4K | +0.016§ | +8.90§ | 5.64 | §5shard |
| 11d | 04-01 | Huber(200) | 64 | (32,4) | 21.4K | **-0.026** | +2.91 | 17.33 | 负Rank IC |
| 12 | 04-03 | Unbounded MSE | 64 | (32,10) | 24.4K | **-0.021** | +4.51 | 26.61 | 29σ反转 |
| **13** | **04-04** | **IC Loss** | **64** | **(32,10)** | **24.6K** | **+0.029** | **+7.00** | varied | **✅ PASS** |
| 14 S1 | 04-05 | Phase 6 复测 | 64 | (32,10) | 19.7K | +0.0023 | +11.16 | 790 | Phase 6 死 |

### Phase 13 详细十分位表 (1,904,748 ���本)

| 十分位 | 样本数 | mean_pred | mean_target (BP) | hit_rate | payoff_ratio |
|--------|--------|-----------|-----------------|----------|-------------|
| D0 (最低) | 190,475 | 19,513 | 1.85 | 46.9% | 1.151 |
| D1 | 190,475 | 28,982 | 6.31 | 48.3% | 1.150 |
| D2 | 190,474 | 31,797 | 7.11 | 48.8% | 1.160 |
| D3 | 190,475 | 33,215 | 6.22 | 49.5% | 1.132 |
| D4 | 190,475 | 34,156 | 7.14 | 50.0% | 1.142 |
| D5 | 190,475 | 34,930 | 7.05 | 50.4% | 1.132 |
| D6 | 190,474 | 35,664 | 7.89 | 50.6% | 1.147 |
| D7 | 190,475 | 36,452 | 8.49 | 50.8% | 1.155 |
| D8 | 190,474 | 37,445 | 8.38 | 50.7% | 1.160 |
| D9 (最高) | 190,476 | 39,579 | **8.85** | **50.4%** | **1.190** |

### Phase 7 回测 (Phase 6 T29 checkpoint, 551 交易日, 成本=25BP)
- 年化收益: +4.58% (board_cap 后 +6.31%)
- Sharpe: 0.49 (0.66)
- Max Drawdown: -26.50%
- 不对称比: 1.20 (目标 >3.0, 未达标)
- Daily CS-IC: 0.028, ICIR: 0.38
- 理论极限: IC=0.028 时不对称比 3.0 数学不可达

---

## 八、决��溯源

### 8.1 hd=64 的决策 (INS-019, 2026-03-29)

**原始证据** (来自 2026-03-29 directive):
> "hd=64 (T29, 19.7K params): IC=+0.0661, 单调性 8/9"
> "hd=128 (T36, 77K params): IC=+0.0667, 单调性 7/9"
> "hd=256 (305K params): 未进入 Top-3"

**现状**: INS-072 宣布 Phase 6 基线全部作废 (C-062 torch.compile bug)。Phase 14 复测 T29: Rank IC=0.0023。**hd=64 的唯一实证已失效。**

### 8.2 单层注意力 — 从未被讨论

**事实**: 整个 74 �� INS + 23 个 directive 中���**层数从未出现在 HPO 搜索空���或讨论中**。原始 directive (2026-03-18) 说 "TDA 维度永远锁定 2D (不需要搜索)"——指的是 2D vs 1D，被执��为"层数也不搜索"。

### 8.3 跨窗口通信 — 讨论过���推迟

**INS-070** (2026-04-04, `Shatter Window Isolation`):
> "当前 5 个隔离的 32-bar 窗口将模型感受野限制在 0.64 天内。必须实现跨窗注意力或滑动窗口重叠。"

**架构师裁决**: ���迟到 Phase 14。理由: "Phase 13 已同时动了 Loss+Target+拓扑，再加跨窗口 → 归因灾难"。

### 8.4 lambda_s=0 锁定

**证据**: Phase 3 (λ=1e-3): MDL 杀信号 → Phase 6 (λ=1e-7): 近零 → Phase 11c (λ=1e-3): 脑死亡 → Phase 11d (λ=1e-4 vs 1e-5): 无差异 → Phase 12 (λ=1e-4): L1 从 2.09→1.16 同时 D9-D0 从 4.48→1.28 → **Phase 13 (λ=0): 首次��功**

---

## 九、Codex GPT-5.4 复核结果

### 9.1 已验证 ✅
- 7 个关键 directive/INS 文件全部存在
- 6 个核心 commit hash 匹配 (1 个 typo: `f578614` → `f57861a`)
- 参数计数 24,581 逐层验证通过
- 代码演化链 16 次 commit 完整
- 74 个 INS 文档全部存在

### 9.2 修���项 ⚠️
1. Commit hash `f578614` 应为 `f57861a` (末位)
2. 原数据包称"跨窗口通信从未被讨论过" → 不准确。INS-070 已讨论，被有意推迟

### 9.3 本地不可获取��数据

| 缺失项 | 位置 | 重要性 |
|--------|------|--------|
| Phase 13 epoch-by-epoch 训练曲线 | GCS 训练日志 | 高 |
| c_friction registry 完整统计 | linux1 节点 | 高 |
| Phase 6 ��部 70 trial HPO 结果 | GCP Vizier | 中 |
| Shard 命名是否严格按时间排序 | 需检查 linux1 数据 | 中 |
| Train/val 边界 embargo gap | 需分析 shard 时间覆盖 | 中 |

---

## 十、Phase 13 训练曲线 (15 Epoch 逐轮数据)

Job `6005517512886714368`, T4 Spot, 10.5h, 零次 Spot 中断。

| Epoch | Val Rank IC | Val D9-D0 (BP) | Pearson IC | 备注 |
|-------|-------------|----------------|------------|------|
| 0 | +0.0074 | -3.25 | -0.0041 | 冷启动 |
| 1 | +0.0187 | +5.98 | +0.0083 | |
| 2 | +0.0135 | +2.20 | +0.0034 | |
| 3 | +0.0121 | +0.84 | +0.0023 | |
| 4 | +0.0054 | +6.96 | +0.0099 | |
| 5 | +0.0025 | +4.48 | +0.0061 | |
| 6 | +0.0175 | +9.04 | +0.0110 | |
| 7 | +0.0128 | +3.12 | +0.0056 | |
| 8 | +0.0239 | +1.90 | +0.0050 | |
| **9** | **+0.0292** | **+7.00** | **+0.0101** | **← Best (saved)** |
| 10 | +0.0209 | +4.81 | +0.0065 | |
| 11 | +0.0124 | +9.35 | +0.0118 | |
| 12 | +0.0178 | +4.60 | +0.0071 | |
| 13 | +0.0172 | +7.76 | +0.0114 | |
| 14 | +0.0180 | +8.49 | +0.0122 | |

**关键观察**: 15 个 epoch 全部 Rank IC 为正（Phase 12 是 -0.0206 的系统性反转）。E10-E14 稳定在 ~0.017 附近，确认收敛。

---

## 十一、Phase 13 Crucible 过拟合测试原始曲线

### Crucible #1: Mandate B (拓扑疏通验证, L4 GPU, Unbounded Spear MSE Loss)
64 样本, 2000 步, batch=64, lr=1e-3

| Step | Loss | Std_yhat | 备注 |
|------|------|----------|------|
| 0 | 5.213 | 0.008239 | |
| 200 | 2.217 | 0.005805 | |
| 400 | 1.737 | 0.006588 | |
| 600 | 1.454 | 0.007412 | |
| 800 | 1.270 | 0.008056 | |
| 1000 | 1.114 | 0.008668 | |
| 1600 | 0.802 | 0.010031 | |
| **2000** | **0.674** | — | **Std_yhat 上升 1.3x, 无方差坍缩** |

### Crucible #2: Mandate A (IC Loss 验证, T4 GPU)
64 样本, 2000 步, batch=64, lr=1e-3

| Step | IC Loss | ≈ Pearson IC | 备注 |
|------|---------|-------------|------|
| 0 | 0.036 | ~-0.04 | 随机 |
| 200 | -0.534 | ~0.53 | |
| 400 | -0.673 | ~0.67 | |
| 600 | -0.740 | ~0.74 | |
| 800 | -0.779 | ~0.78 | |
| 1000 | -0.805 | ~0.81 | |
| 1400 | -0.841 | ~0.84 | |
| **2000** | **-0.875** | **~0.88** | **24.6K 参数拟合 77% 方差** |

架构师裁决: **PASS** — "24.4K 参数的小模型在噪声微观特征上拟合 64 样本 Pearson 到 0.88，证明非线性特征表述能力已达物理极限"。

---

## 十二、Phase 14 验证实验原始数据

### Step 0: 数据侧基线 (模型无关)

来源: `reports/phase14/phase14_step0_step1.json`

| 统计量 | 值 | 意义 |
|--------|-----|------|
| N (验证样本) | 1,904,747 | |
| Mean | 6.93 BP | 正偏 (A 股整体正漂移) |
| Std | 189.60 BP | 噪声 |
| Skew | 11.78 | 严重右偏 |
| **Kurtosis** | **2,006.46** | 极端肥尾 |
| Range | [-9,035, +42,671] BP | |
| Data SNR | 3.655% | 替代已证伪的 "2.4%" (C-077) |

### Step 1: Phase 6 T29 Checkpoint 复测 (Oracle Test)

来源: `reports/phase14/phase14_step0_step1.json`, `tools/phase6_oracle_test.py`

使用 `Phase6Inference` 忠实复现 Phase 6 前向逻辑 (无 Pre-LN, 无 AttentionPooling, 全局均值池化)。

| 指标 | Phase 6 T29 复测 | Phase 13 对照 |
|------|-----------------|-------------|
| Rank IC | **+0.0023** | +0.0292 |
| Pearson IC | +0.0144 | +0.0101 |
| D9-D0 | +11.16 BP | +7.00 BP |
| **pred_std** | **790.42 BP** | 受控 |
| D9 hit_rate | 50.2% | 50.4% |
| D0 hit_rate | 49.2% | 46.9% |
| 单调性 | 7/9 | 6/9 |
| N 样本 | 1,904,747 | 1,904,748 |

**判定**: BRANCH A (信号死亡)。pred_std=790 BP = 方差爆炸噪声发生器。D9-D0=11.16 BP 是由极端预测值驱动的伪信号（波动率排序），非真实信号。

Phase 6 T29 完整十分位表:

| Decile | N | Mean Target (BP) | Hit Rate | Payoff Ratio |
|--------|------|-----------------|----------|-------------|
| D0 | 190,476 | 3.06 | 49.2% | 1.089 |
| D1 | 190,474 | 5.16 | 50.2% | 1.104 |
| D2 | 190,475 | 5.43 | 50.1% | 1.110 |
| D3 | 190,474 | 5.99 | 49.8% | 1.129 |
| D4 | 190,476 | 6.45 | 49.8% | 1.131 |
| D5 | 190,473 | 6.96 | 49.7% | 1.138 |
| D6 | 190,475 | 6.93 | 49.4% | 1.140 |
| D7 | 190,474 | 6.91 | 49.2% | 1.143 |
| D8 | 190,477 | 8.18 | 48.9% | 1.169 |
| D9 | 190,476 | 14.22 | 50.2% | 1.179 |

### Step 2: 宏观旁路 A/B 实验

Vertex AI Jobs: Arm A `2184063695481470976`, Arm B `5988585033818963968`

两臂配置完全相同，唯一区别:
- Arm A: `--macro_bypass=False` (6 维输入: LOB(5) + q_metaorder(1))
- Arm B: `--macro_bypass=True` (8 维输入: +log1p(V_D) + log1p(σ_D))

| 指标 | Arm A (基线, 6维) | Arm B (旁路, 8维) |
|------|-----------------|------------------|
| **Best Rank IC** | **+0.0122** | +0.0064 |
| Best D9-D0 | +5.09 BP | +9.06 BP* |

*Arm B 的 D9-D0=9.06 出现在 E4，但同时 Rank IC 仅 0.005，说明是少数极端预测拉高了尾部，整体排序能力弱。

**注意**: Step 2 的逐 epoch 数据未持久化到本地，仅存于 Vertex AI 日志中。两个 Job 均未录入 manifest.jsonl。

**结论**: Arm A (基线) 以 90% 优势胜出。SRL 信息压缩正确，宏观旁路不增加增量价值。`macro_bypass=False` 永久锁定。

---

## 十三、致审计师：数据对数学核心的验证意义

以下是 Phase 13+14 数据对 Omega-TIB 各数学组件的验证状态。**仅列事实和数据对应关系，不做定性判断。**

### 13.1 SRL 物理反演层

| 验证 | 证据 | 数据来源 |
|------|------|---------|
| SRL 压缩是否丢失信息? | Step 2 Arm A (仅 SRL 输出) Rank IC=+0.0122 > Arm B (SRL + 原始宏观) +0.0064 | Phase 14 Step 2 |
| c_friction per-stock 标定 vs 全局常数 | 创世版 c=0.842 固定, 当前版 per-stock; Phase 13 用当前版成功 | 创世版 vs 当前版对比 |
| δ=0.5 (平方根法则) | 从未被修改, 所有成功/失败 Phase 均使用 δ=0.5 | 全部 16 次 commit |

### 13.2 有限窗口拓扑注意力 (FWT)

| 验证 | 证据 | 数据来源 |
|------|------|---------|
| RPB (相对位置偏置) 是否必要? | 创世版无 RPB, 17 分钟后添加; Phase 12 发现 RPB grad=0.08 vs decoder=4811 (60000x 弱), Pre-LN 残差修复后信号恢复 | commit 8105a08, Phase 12 审计 |
| 窗口 (32,10) vs (4,4) | Phase 6 HPO 70 试选出 wt=32; Phase 3 用 (4,4) FVU≈1.0; Phase 11d 用 (32,4) Rank IC=-0.026 | HPO 结果 + 各 Phase 对比 |
| 单层 vs 多层 | **从未实验过** | 无数据 |
| 跨窗口通信 | **从未实验过** (INS-070 提出, 推迟至 Phase 14, 尚未执行) | INS-070 |

### 13.3 信息瓶颈 (Bottleneck 64→32→16)

| 验证 | 证据 | 数据来源 |
|------|------|---------|
| hd=64 vs 128 vs 256 | Phase 6 HPO: 64≈128 (IC差0.0006), 256 未进 Top-3; **但 Phase 6 基线已作废 (INS-072, C-062)** | Phase 6 HPO (已失效) |
| hd=64 在修复后管线上 | **从未实验过** — Phase 13 直接用 hd=64, 未对比其他 | 无数据 |
| lambda_s (L1 稀疏化) | Phase 3 λ=1e-3 杀信号; Phase 12 λ=1e-4 D9-D0 从 4.48→1.28; **Phase 13 λ=0 首次成功** | 6 Phase 实证 |

### 13.4 池化层

| 验证 | 证据 | 数据来源 |
|------|------|---------|
| AttentionPooling vs GlobalMeanPool | Phase 6 T29 (GMP): pred_std=790 方差爆炸; Phase 13 (AttentionPool): 方差受控, Rank IC 从 0.0023→0.0292 | Phase 14 Step 1 vs Phase 13 post-flight |
| Pre-LN 残差 | Crucible #1 Std_yhat 上升 1.3x (健康) vs Phase 12 (无残差) 5x 衰减 | Crucible 测试 |

### 13.5 损失函数

| 验证 | 证据 | 数据来源 |
|------|------|---------|
| IC Loss vs MSE 变种 | Phase 9/10/11/12 全部 MSE 变种均失败; Phase 13 恢复 IC Loss 首次成功 | 12 Phase 对比 |
| Leaky Blinding 有害 | Phase 12 D9 hit_rate(49%) < D0(51.4%); Phase 13 移除后 D9(50.4%) > D0(46.9%) | 十分位表对比 |
| IC Loss 在 kurtosis=2006 下的行为 | Phase 13 成功, 但 IC Loss 对每个样本等权处理 — 是否最优尚无对照实验 | 无对照 |

### 13.6 整体训练科学

| 验证 | 证据 | 数据来源 |
|------|------|---------|
| Batch size=256 对 IC 的影响 | 采样标准误差 ≈ 1/√256 = 6.25% > 信号 2.9% | 统计理论, 无实验对照 |
| Weight decay=1e-5 | 从未实验过其他值 | 无数据 |
| Dropout | 模型中不存在 dropout | 源码确认 |
| Mask_prob=0.0 | Phase 13 禁用了 VolumeBlockInputMasking | 配置确认 |
| EMA / SWA | 从未实现 | 无代码 |
| Early stopping | 仅有阈值检查, 无 patience-based | 源码确认 |
| AdamW betas | 默认 (0.9, 0.999), 从未调优 | 源码确认 |

---

## 十四、Phase 13 架构师 5 项裁决原文摘要

| INS | 裁决 | 原始证据 | Phase 13 验证 |
|-----|------|---------|-------------|
| 065 | 删除 Leaky Blinding | Gemini 证明: 0.1 系数压缩负回报梯度 100x → 模型变波动率预测器 | D9 hit_rate 从 49%→50.4%, D0 从 51.4%→46.9% |
| 066 | 弃 MSE → 恢复 IC Loss | MSE 在 190BP std 下退化为条件均值预测器 | Phase 13 首次正向 Rank IC |
| 067 | 评估改为截面 Rank IC | 全局排序混淆跨日波动率差异 | Rank IC=+0.029 (p=0.0) |
| 068 | Pre-LN 残差 + AttentionPooling | RPB 梯度比 decoder 弱 60000x; GMP 摧毁序列信息 | Crucible IC 0.88; 方差不坍缩 |
| 069 | lambda_s=0 (L1 永久禁用) | 6 Phase 实证: L1 在 kurtosis=2006 下是"尾部信号绞肉机" | Phase 13 λ=0 唯一成功 |

**5/5 裁决均被后续实验数据支持。**

---

*End of Self-Contained Audit Workpapers — 2026-04-06*
