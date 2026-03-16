"""
WebDataset Loader for Omega Pure v2
-----------------------------------
Implements:
1. GPU Slicing: Dynamically slices the 160-row window to `macro_window` during HPO.
2. Dynamic Pooling: Uses F.avg_pool2d dynamically based on `coarse_graining_factor`.
3. Stateless Event-Driven Loop compatibility: O(1) loading from tar shards.
"""

import webdataset as wds
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

def identity(x):
    return x

def dynamic_processor(macro_window, coarse_graining_factor):
    """
    Returns a WebDataset map function that implements dynamic slicing and pooling
    per the Architect's instructions.
    """
    def process(sample):
        # sample contains the full 160xN receptive field matrix
        matrix = sample["data.npy"]
        tensor = torch.tensor(matrix, dtype=torch.float32)
        
        # 1. Max-Receptive-Field GPU Slicing
        # Slice from the end (most recent steps) if macro_window < max field
        if macro_window < tensor.shape[0]:
            tensor = tensor[-macro_window:, :]
            
        # 2. Min-Resolution Dynamic Pooling
        # Average pool over the sequence dimension (dim=0).
        if coarse_graining_factor > 1:
            # Reshape for avg_pool2d: (batch, channels, height, width)
            # Treat as (1, 1, seq_len, features)
            tensor = tensor.unsqueeze(0).unsqueeze(0)
            
            # Pool along the time dimension (stride=coarse_graining_factor)
            kernel = (coarse_graining_factor, 1)
            tensor = F.avg_pool2d(tensor, kernel_size=kernel, stride=kernel)
            
            # Squeeze back to (pooled_seq_len, features)
            tensor = tensor.squeeze(0).squeeze(0)
            
        # Return tuple format (features, target) or single dict based on trainer needs
        # Assuming last column or next step is target. Yielding tensor for now.
        return tensor
        
    return process

def create_dataloader(wds_url, batch_size=256, macro_window=160, coarse_graining_factor=1, num_workers=4):
    """
    Creates a stateless O(1) WebDataset dataloader.
    Absolutely no global .collect() or in-memory array loading.
    """
    preprocess_fn = dynamic_processor(macro_window, coarse_graining_factor)
    
    # The Ironclad Anti-OOM Architecture Datapipe
    dataset = (
        wds.WebDataset(wds_url, resampled=True)
        .shuffle(1000)
        .decode()
        .map(preprocess_fn)
        .batched(batch_size)
    )
    
    loader = DataLoader(
        dataset,
        batch_size=None, # wds.batched handles it
        num_workers=num_workers,
        prefetch_factor=2
    )
    
    return loader

if __name__ == '__main__':
    # Usage Example:
    # url = "/data/wds_shards/shard-{000000..000100}.tar"
    # hpo_loader = create_dataloader(url, macro_window=120, coarse_graining_factor=2)
    # for batch in hpo_loader:
    #     print(batch.shape) # e.g. [256, 60, 7]
    #     break
    pass
