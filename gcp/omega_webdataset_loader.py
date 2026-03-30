"""
WebDataset Loader for Omega-TIB V3 (Phase 0.5 Rewrite)
-------------------------------------------------------
10-channel tensor [160, 10, 10] with c_friction and forward target.

Channels: [Bid_P, Bid_V, Ask_P, Ask_V, Close, reserved, reserved, ΔP, macro_V_D, macro_σ_D]

Loader outputs dict with:
  - manifold_2d: [T, S, 10] full tensor
  - c_friction: scalar (per-stock SRL friction coefficient)
  - target: scalar (forward VWAP return in BP)
"""

import io

import webdataset as wds
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
import numpy as np


def fast_npy_decoder(sample):
    """Bypass WDS generic decode, strictly parse .npy bytes.
    Gemini GCS audit: ~15% CPU savings vs wds.decode() which probes
    all registered decoders (PIL, JSON, etc) for each file.
    """
    result = {}
    for key, value in sample.items():
        if key.endswith(".npy"):
            result[key] = np.load(io.BytesIO(value))
        else:
            result[key] = value
    return result


def dynamic_processor(macro_window, coarse_graining_factor):
    """
    Returns a WebDataset map function implementing dynamic slicing and pooling
    for the Omega-TIB 10-channel [Time, Spatial, Features] topology.
    """
    def process(sample):
        matrix = sample["manifold_2d.npy"]
        tensor = torch.tensor(matrix, dtype=torch.float32)  # [160, 10, 10]

        # 1. GPU-side dynamic slicing (no CPU re-ETL per HPO trial)
        if macro_window < tensor.shape[0]:
            tensor = tensor[-macro_window:, :, :]

        # 2. Dynamic temporal pooling (coarse graining)
        if coarse_graining_factor > 1:
            tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # [1, 10, T, S]
            kernel = (coarse_graining_factor, 1)
            tensor = F.avg_pool2d(tensor, kernel_size=kernel, stride=kernel)
            tensor = tensor.squeeze(0).permute(1, 2, 0)  # [T', S, 10]

        # 3. Extract c_friction (per-stock, from ETL)
        c_friction_val = float(sample.get("c_friction.npy", np.array([0.842]))[0])
        c_friction = torch.tensor(c_friction_val, dtype=torch.float32)

        # 4. Extract target (forward VWAP return in BP)
        target_val = float(sample.get("target.npy", np.array([0.0]))[0])
        target = torch.tensor(target_val, dtype=torch.float32)

        return {
            "manifold_2d": tensor,      # [T, S, 10]
            "c_friction": c_friction,    # scalar
            "target": target,            # scalar
        }

    return process


def create_dataloader(wds_url, batch_size=256, macro_window=160,
                      coarse_graining_factor=1, num_workers=4):
    preprocess_fn = dynamic_processor(macro_window, coarse_graining_factor)

    dataset = (
        wds.WebDataset(wds_url, resampled=True)
        .shuffle(1000)
        .map(fast_npy_decoder)  # Gemini GCS audit: bypass generic decode, -15% CPU
        .map(preprocess_fn)
        .batched(batch_size)
    )

    loader_kwargs = dict(
        batch_size=None,
        num_workers=num_workers,
        pin_memory=True,
    )
    # prefetch_factor requires num_workers > 0 (PyTorch >= 2.0)
    if num_workers > 0:
        loader_kwargs["prefetch_factor"] = 4  # Gemini: 4 > 2 for NVMe throughput

    loader = DataLoader(dataset, **loader_kwargs)

    return loader
