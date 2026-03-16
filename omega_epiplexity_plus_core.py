import torch
import torch.nn as nn
import torch.nn.functional as F
import math

class AxiomaticSRLInverter(nn.Module):
    """
    第一性原理模块一：严格普适的物理常数反演层 (SRL Axiom Decrypter)
    文献支持: Strict universality of the square-root law...
    公式: I(Q) = c * \sigma_D * (Q / V_D)^{0.5} 
    我们不让模型浪费算力去学习量价关系，而是直接逆向解码出隐藏的主力 Metaorder 真实体积: 
    Q_hidden = ( \Delta P / (c * \sigma_D) )^2 * V_D
    """
    def __init__(self, c_constant: float = 0.842):
        super().__init__()
        # c_constant 取自 TSE 普查文献的全局平均预估无量纲系数
        self.c = c_constant
        # 物理常数 delta = 0.5，逆运算即为平方 (2.0)。严禁设为可学习参数！
        self.power_constant = 2.0 

    def forward(self, delta_p: torch.Tensor, sigma_d: torch.Tensor, v_d: torch.Tensor) -> torch.Tensor:
        eps = 1e-8
        # 1. 剥离异方差与物理常数，提取无量纲化的冲击力度
        dimensionless_impact = torch.abs(delta_p) / (self.c * sigma_d + eps)
        
        # 2. 严格执行平方物理反演，榨取绝对量能
        q_magnitude = torch.pow(dimensionless_impact, self.power_constant) * (v_d + eps)
        
        # 3. 还原主力买卖意图的方向 (sign)
        q_hidden_directed = torch.sign(delta_p) * q_magnitude
        return q_hidden_directed


class FiniteWindowTopologicalAttention(nn.Module):
    """
    第一性原理模块二：有限窗口拓扑算子 (Finite Window Theory Engine)
    文献支持: Epiplexity plus: Finite Window Theory
    绝对禁止将 2D 拓扑展平为 1D 序列！
    强制在原生多维流形上实施严格有界 (Space-bounded) 的局部窗口注意力，规避 Embedding Dilation。
    """
    def __init__(self, dim: int, window_size: tuple = (4, 4), num_heads: int = 4):
        super().__init__()
        self.dim = dim
        self.window_t, self.window_s = window_size
        self.num_heads = num_heads
        
        self.qkv = nn.Linear(dim, dim * 3, bias=False)
        self.proj = nn.Linear(dim, dim)
        self.scale = (dim // num_heads) ** -0.5

    def forward(self, x_nd: torch.Tensor) -> torch.Tensor:
        """
        x_nd: Shape (Batch, Time, Spatial, Features) - 原生2D网格拓扑
        Spatial 可以是资产截面网络，也可以是订单簿深度网络。
        """
        B, T, S, D = x_nd.shape
        
        # 强制实施 Space-bounded 空间掩蔽：将全局切分为局部 Finite Windows
        pad_t = (self.window_t - T % self.window_t) % self.window_t
        pad_s = (self.window_s - S % self.window_s) % self.window_s
        if pad_t > 0 or pad_s > 0:
            x_nd = F.pad(x_nd, (0, 0, 0, pad_s, 0, pad_t))
            
        _, T_pad, S_pad, _ = x_nd.shape
        
        # 划分为不可逾越的物理视域窗口: [B, T_win, S_win, W_t, W_s, Dim]
        x_win = x_nd.view(B, T_pad // self.window_t, self.window_t, 
                          S_pad // self.window_s, self.window_s, D)
                          
        # 局部窗口折叠，严密维持拓扑相邻关系，寻址复杂度锁定为 O(1): [B * Num_Win, W_t * W_s, Dim]
        x_win = x_win.permute(0, 1, 3, 2, 4, 5).contiguous().view(-1, self.window_t * self.window_s, D)
        
        # 局域拓扑内进行特征聚合 (Epiplexity Extraction)
        qkv = self.qkv(x_win).chunk(3, dim=-1)
        q, k, v = map(lambda t: t.view(-1, self.window_t * self.window_s, self.num_heads, D // self.num_heads).transpose(1, 2), qkv)
        
        # 注意力严格限制在局域拓扑内，斩断无限上下文带来的拓扑撕裂与随机相关性
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)
        
        out = (attn @ v).transpose(1, 2).reshape(-1, self.window_t * self.window_s, D)
        out = self.proj(out)
        
        # 完美还原原生 2D 拓扑结构
        out = out.view(B, T_pad // self.window_t, S_pad // self.window_s, self.window_t, self.window_s, D)
        out = out.permute(0, 1, 3, 2, 4, 5).contiguous().view(B, T_pad, S_pad, D)
        
        if pad_t > 0 or pad_s > 0:
            out = out[:, :T, :S, :].contiguous()
            
        return out


class OmegaMathematicalCompressor(nn.Module):
    """
    第一性原理模块三：完美数学压缩器核心 (The Perfect Mathematical Compressor)
    组装 SRL 物理反演, Finite Window TDA 与 Epiplexity 提纯引擎
    """
    def __init__(self, raw_feature_dim: int, hidden_dim: int, window_size: tuple = (4, 4)):
        super().__init__()
        self.srl_inverter = AxiomaticSRLInverter()
        
        # 特征映射: 原始高阶特征 + 解码出的主力量能(1维)
        self.input_proj = nn.Linear(raw_feature_dim + 1, hidden_dim)
        self.tda_layer = FiniteWindowTopologicalAttention(hidden_dim, window_size)
        
        # Epiplexity 信息瓶颈层 (Bottleneck)
        # 用极其有限的参数逼迫模型去“压缩”信息，榨取真实的结构化代码
        self.epiplexity_bottleneck = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim // 4) 
        )
        self.intent_decoder = nn.Linear(hidden_dim // 4, 1)

    def forward(self, price_impact_2d: torch.Tensor, raw_features_2d: torch.Tensor, 
                sigma_d: torch.Tensor, v_d: torch.Tensor):
        
        # 1. 物理层解码：抛弃瞎猜，通过宇宙常数反向暴漏主力真实隐藏体积
        with torch.no_grad(): # 停止梯度，SRL是确定的物理法则
            q_metaorder_intent = self.srl_inverter(price_impact_2d, sigma_d, v_d).unsqueeze(-1)
        
        # 2. 拼接原生拓扑流形
        native_manifold = torch.cat([raw_features_2d, q_metaorder_intent], dim=-1)
        x = self.input_proj(native_manifold)
        
        # 3. 拓扑层压缩：穿透受限二维感知窗口，无损捕获局域连通性
        structured_features = self.tda_layer(x)
        
        # 4. 认知层提纯：进入信息瓶颈
        # z_core 即为主力行为的纯粹可压缩结构表示 (The Epiplexity Core)
        z_core = self.epiplexity_bottleneck(structured_features)
        
        # 时空维度全局池化以得出宏观意图
        pooled_z = torch.mean(z_core, dim=[1, 2])
        main_force_prediction = self.intent_decoder(pooled_z)
        
        return main_force_prediction, z_core

def compute_epiplexity_mdl_loss(prediction: torch.Tensor, target: torch.Tensor, 
                                z_core: torch.Tensor, lambda_s: float = 1e-3):
    """
    第一性原理模块四：Two-Part Minimum Description Length (MDL) 损失函数
    Total_MDL = H_T (Time-bounded Entropy 预测残差) + S_T (Epiplexity 结构复杂度)
    """
    # 1. H_T: 无法预测的随机市场噪音 (时间有界熵)
    # 代表市场中布朗运动的随机摩擦部分
    h_t = F.mse_loss(prediction.squeeze(), target)
    
    # 2. S_T: 模型为了解释数据而提取的结构化信息复杂度 (Epiplexity)
    # 我们使用内部提取拓扑特征 z_core 的 L1 稀疏范数来代理编码长度 |P|。
    # 这一项会强烈逼迫模型摒弃高熵的随机假象，寻找具有最短描述长度(Shortest Description Length)的主力规则。
    s_t = torch.norm(z_core, p=1, dim=-1).mean()
    
    # 3. 压缩即智能：用最低的认知代价(S_T)，去瓦解最大的时空混沌(H_T)
    total_mdl = h_t + lambda_s * s_t
    return total_mdl, h_t, s_t