"""
WebDataset Loader for Omega Pure v3
-----------------------------------
Implements:
1. GPU Slicing: Dynamically slices the 160-row window to `macro_window` during HPO.
2. Dynamic Pooling: Uses F.avg_pool2d dynamically based on `coarse_graining_factor`.
3. Spatial Awareness: Handles the restored [160, 10, 7] Topo-Forge matrix.
"""

import webdataset as wds
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
import numpy as np

def dynamic_processor(macro_window, coarse_graining_factor):
    """
    Returns a WebDataset map function that implements dynamic slicing and pooling
    for the OMEGA V3 [Time, Spatial, Features] topology.
    Shape: [160, 10, 7]
    Features: 0:Bid_P, 1:Bid_V, 2:Ask_P, 3:Ask_V, 4:Close, 5:SRL_Res, 6:Epiplexity
    """
    def process(sample):
        # sample["manifold_2d.npy"] contains the [160, 10, 7] matrix
        matrix = sample["manifold_2d.npy"]
        tensor = torch.tensor(matrix, dtype=torch.float32) # Already [160, 10, 7]
        
        # 1. Max-Receptive-Field GPU Slicing
        if macro_window < tensor.shape[0]:
            tensor = tensor[-macro_window:, :, :]
            
        # 2. Min-Resolution Dynamic Pooling (Temporal only)
        if coarse_graining_factor > 1:
            # Reshape for avg_pool2d: (batch, channels, height, width)
            # Treat features as channels: (1, 7, time, spatial)
            tensor = tensor.permute(2, 0, 1).unsqueeze(0)
            kernel = (coarse_graining_factor, 1)
            tensor = F.avg_pool2d(tensor, kernel_size=kernel, stride=kernel)
            # Restore to (pooled_time, spatial, features)
            tensor = tensor.squeeze(0).permute(1, 2, 0)
            
        # 3. Feature Extraction & Routing for Mathematic Core
        # Price Impact (Top of book Bid1 price change)
        # Feature 0 is Bid_P1
        price_impact_2d = torch.diff(tensor[:, :, 0], dim=0, prepend=tensor[0:1, :, 0])
        
        # Volume (Sum of BidV and AskV across all depths as a proxy for liquidity density)
        # Features 1 and 3 are BidV and AskV
        v_d = (tensor[:, :, 1] + tensor[:, :, 3]).unsqueeze(-1) + 1e-8
        
        # Rolling volatility from price changes (window=20 bars)
        # SRL formula I(Q) = c·σ_D·(Q/V_D)^0.5 requires real σ_D
        vol_window = min(20, price_impact_2d.shape[0])
        if vol_window >= 2:
            sigma_d = price_impact_2d.unfold(0, vol_window, 1).std(dim=-1)
            pad_len = price_impact_2d.shape[0] - sigma_d.shape[0]
            sigma_d = F.pad(sigma_d, (0, 0, pad_len, 0), mode='replicate')
        else:
            sigma_d = torch.ones_like(price_impact_2d)
        sigma_d = sigma_d.unsqueeze(-1).clamp(min=1e-8)
        
        # Raw features for Topological Attention: Close, SRL, Epiplexity
        # Features 4, 5, 6
        raw_features_2d = tensor[:, :, [4, 5, 6]]
        
        return {
            "price_impact_2d": price_impact_2d.unsqueeze(-1),
            "raw_features_2d": raw_features_2d,
            "sigma_d": sigma_d,
            "v_d": v_d
        }
        
    return process

def create_dataloader(wds_url, batch_size=256, macro_window=160, coarse_graining_factor=1, num_workers=4):
    preprocess_fn = dynamic_processor(macro_window, coarse_graining_factor)
    
    dataset = (
        wds.WebDataset(wds_url, resampled=True)
        .shuffle(1000)
        .decode()
        .map(preprocess_fn)
        .batched(batch_size)
    )
    
    loader = DataLoader(
        dataset,
        batch_size=None,
        num_workers=num_workers,
        prefetch_factor=2
    )
    
    return loader
