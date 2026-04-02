"""
OMEGA-TIB: Topological Information Bottleneck (Phase 0.5 Update)
----------------------------------------------------------------
Mathematical core: SRL Physics → FWT Topology → MDL Compression → Intent Prediction

Changes from previous version:
  - AxiomaticSRLInverter: accepts c_friction tensor (per-stock, id4 ruling)
  - OmegaMathematicalCompressor: new forward(x_2d, c_friction) signature
    extracts ΔP/V_D/σ_D from x_2d channels 7/8/9 (id6 ruling)
  - Architecture renamed from SpatioTemporal2DMAE to Omega-TIB (id5 ruling)
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
    def __init__(self):
        super().__init__()
        self.power_constant = 2.0  # 1/δ = 1/0.5 = 2.0 (eternal, never modify)

    def forward(self, delta_p: torch.Tensor, sigma_d: torch.Tensor,
                v_d: torch.Tensor, c_friction: torch.Tensor) -> torch.Tensor:
        """
        Args:
            delta_p: [B, T] micro price impact
            sigma_d: [B, T] macro 20-day rolling ATR
            v_d: [B, T] macro 20-day rolling ADV
            c_friction: [B, 1] per-stock friction coefficient
        Returns:
            q_hidden: [B, T] directed hidden metaorder volume
        """
        eps = 1e-8
        # Broadcast c_friction [B, 1] to [B, T]
        c = c_friction.expand_as(delta_p)
        dimensionless_impact = torch.abs(delta_p) / (c * sigma_d + eps)
        q_magnitude = torch.pow(dimensionless_impact, self.power_constant) * (v_d + eps)
        return torch.sign(delta_p) * q_magnitude


class FiniteWindowTopologicalAttention(nn.Module):
    """
    Layer 2 Topology: Finite Window 2D attention on native manifold.
    Absolutely NO 1D flattening. O(1) addressing per window.
    """
    def __init__(self, dim: int, window_size: tuple = (4, 4), num_heads: int = 4):
        super().__init__()
        self.dim = dim
        self.window_t, self.window_s = window_size
        self.num_heads = num_heads

        self.qkv = nn.Linear(dim, dim * 3, bias=False)
        self.proj = nn.Linear(dim, dim)
        self.scale = (dim // num_heads) ** -0.5

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

        x_win = x_nd.view(B, T_pad // self.window_t, self.window_t,
                          S_pad // self.window_s, self.window_s, D)
        x_win = x_win.permute(0, 1, 3, 2, 4, 5).contiguous().view(
            -1, self.window_t * self.window_s, D)

        qkv = self.qkv(x_win).chunk(3, dim=-1)
        q, k, v = map(lambda t: t.view(
            -1, self.window_t * self.window_s, self.num_heads,
            D // self.num_heads).transpose(1, 2), qkv)

        attn = (q @ k.transpose(-2, -1)) * self.scale

        rpb = self.relative_position_bias_table[
            self.relative_position_index.view(-1)
        ].view(self.window_t * self.window_s, self.window_t * self.window_s, -1)
        rpb = rpb.permute(2, 0, 1).contiguous()
        attn = attn + rpb.unsqueeze(0)

        attn = attn.softmax(dim=-1)

        out = (attn @ v).transpose(1, 2).reshape(
            -1, self.window_t * self.window_s, D)
        out = self.proj(out)

        out = out.view(B, T_pad // self.window_t, S_pad // self.window_s,
                       self.window_t, self.window_s, D)
        out = out.permute(0, 1, 3, 2, 4, 5).contiguous().view(B, T_pad, S_pad, D)

        if pad_t > 0 or pad_s > 0:
            out = out[:, :T, :S, :].contiguous()

        return out


class OmegaMathematicalCompressor(nn.Module):
    """
    Omega-TIB: Topological Information Bottleneck.
    SRL Physics → FWT Topology → Epiplexity Bottleneck → Intent Prediction.

    Input: x_2d [B, T, S, 10] + c_friction [B, 1]
    Output: (prediction [B, 1], z_core [B, T, S, hidden//4])
    """
    def __init__(self, hidden_dim: int = 64, window_size: tuple = (4, 4)):
        super().__init__()
        self.srl_inverter = AxiomaticSRLInverter()

        # LOB features (ch 0-4) + q_metaorder (1) = 6 input dims
        self.input_proj = nn.Linear(6, hidden_dim)
        self.tda_layer = FiniteWindowTopologicalAttention(hidden_dim, window_size)

        self.epiplexity_bottleneck = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim // 4)
        )
        self.intent_decoder = nn.Linear(hidden_dim // 4, 1)

    def forward(self, x_2d: torch.Tensor, c_friction: torch.Tensor):
        """
        Args:
            x_2d: [B, T, S, 10] — 10-channel Omega-TIB tensor
            c_friction: [B, 1] — per-stock friction coefficient
        """
        B, T, S, C = x_2d.shape

        # Extract macro physical anchors from channels 7/8/9
        # Use spatial depth 0 (broadcast-identical across all depths)
        delta_p = x_2d[:, :, 0, 7]         # [B, T]
        v_d_macro = x_2d[:, :, 0, 8]       # [B, T]
        sigma_d_macro = x_2d[:, :, 0, 9]   # [B, T]

        # 1. Physics layer: SRL inversion (non-learnable, torch.no_grad)
        with torch.no_grad():
            q_metaorder = self.srl_inverter(
                delta_p, sigma_d_macro, v_d_macro, c_friction
            )  # [B, T]
        # Expand to [B, T, S, 1] for manifold concatenation
        q_metaorder = q_metaorder.unsqueeze(-1).unsqueeze(-1).expand(B, T, S, 1)

        # 2. Build native manifold: LOB features (ch 0-4) + q_metaorder
        lob_features = x_2d[:, :, :, :5]  # [B, T, S, 5]
        native_manifold = torch.cat([lob_features, q_metaorder], dim=-1)  # [B, T, S, 6]
        x = self.input_proj(native_manifold)

        # 3. Topology layer: finite window 2D attention
        structured_features = self.tda_layer(x)

        # 4. Compression layer: information bottleneck
        z_core = self.epiplexity_bottleneck(structured_features)

        # 5. Prediction layer: global pooling → scalar intent
        pooled_z = torch.mean(z_core, dim=[1, 2])
        main_force_prediction = self.intent_decoder(pooled_z)

        return main_force_prediction, z_core


def compute_epiplexity_mdl_loss(prediction: torch.Tensor, target: torch.Tensor,
                                z_core: torch.Tensor, lambda_s: float = 1e-3):
    """
    Two-Part MDL Loss: Total = H_T + λ_s × S_T
    H_T = MSE(prediction, target) — time-bounded entropy (unpredictable noise)
    S_T = ||z_core||₁ — structure description length (Epiplexity)
    """
    h_t = F.mse_loss(prediction.view(-1), target)
    s_t = torch.norm(z_core, p=1, dim=-1).mean()
    total_mdl = h_t + lambda_s * s_t
    return total_mdl, h_t, s_t


def compute_fvu(predictions: torch.Tensor, targets: torch.Tensor) -> float:
    """FVU = MSE / Var(target). Scale-invariant HPO metric (id5 ruling)."""
    predictions = predictions.view(-1)
    targets = targets.view(-1)
    mse = F.mse_loss(predictions, targets).item()
    target_var = torch.var(targets, unbiased=False).item()
    if target_var < 1e-8:
        return 1.0
    return mse / target_var

def compute_spear_loss_moment_matched(raw_logits, target, z_core, lambda_s=1e-4, huber_delta=200.0):
    pred = raw_logits.float().view(-1)
    tgt = target.float().view(-1)
    z_core = z_core.float()
    
    target_acc = torch.clamp(tgt, min=0.0)
    loss_err = F.huber_loss(pred, target_acc, delta=huber_delta)
    
    if pred.numel() > 1:
        pred_std = torch.std(pred) + 1e-8
        target_std = torch.std(target_acc) + 1e-8
        loss_var = F.mse_loss(pred_std, target_std)
    else:
        loss_var = torch.tensor(0.0, device=pred.device)
        
    z_core_safe = torch.clamp(z_core, min=-20.0, max=20.0)
    s_t = torch.norm(z_core_safe, p=1, dim=-1).mean()
    
    total_loss = loss_err + loss_var + lambda_s * s_t
    
    return total_loss, loss_err, s_t, pred

