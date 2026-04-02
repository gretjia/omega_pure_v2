import os
import sys
import glob
import torch
import numpy as np
from torch.optim import AdamW

# Add parent directory to path to import train.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from train import compute_spear_loss
from omega_epiplexity_plus_core import OmegaMathematicalCompressor
from omega_webdataset_loader import create_dataloader

def main():
    print("="*60)
    print("Autoresearch Sandbox: 5-Minute Evaluation Loop")
    print("="*60)
    
    # 1. Data Source Discovery
    shard_dir = "/omega_pool/wds_shards_v3_full"
    shards = []
    
    if os.path.exists(shard_dir):
        shards = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
        
    if not shards:
        shard_dir = "/omega_pool"
        if os.path.exists(shard_dir):
            shards = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
            
    if not shards:
        print(f"[WARN] No shards found in standard paths. Trying local fallback...")
        # Get absolute path to tests/data
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shard_dir = os.path.join(base_dir, "tests", "data")
        shards = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
        
    if not shards:
        # Generate a dummy batch just to test compilation if no shards exist locally
        print("[WARN] No shards found in workspace. Using synthetic data for local agent testing.")
        use_synthetic = True
    else:
        wds_url = shards[0]
        print(f"[INFO] Using real shard: {wds_url}")
        use_synthetic = False
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Device: {device}")
    
    # 2. Init Model & Config
    model = OmegaMathematicalCompressor(hidden_dim=64).to(device)
    optimizer = AdamW(model.parameters(), lr=1e-4)
    
    lambda_s = float(os.environ.get("LAMBDA_S", "1e-4"))
    print(f"[INFO] Using lambda_s = {lambda_s} (Config {'A' if lambda_s >= 1e-4 else 'B'})")
    
    # 3. Train Loop
    model.train()
    train_batches = 30
    print(f"[INFO] Training for {train_batches} batches...")
    
    if use_synthetic:
        # Synthetic loop
        for i in range(train_batches):
            x_2d = torch.randn(128, 160, 10, 10, device=device)
            c_friction = torch.ones(128, device=device)
            target = torch.randn(128, device=device) * 100 # ~100 BP std
            
            optimizer.zero_grad()
            pred, z_core = model(x_2d, c_friction.unsqueeze(-1))
            total_loss, _, _ = compute_spear_loss(
                pred, target, z_core, lambda_s=lambda_s, epoch=5, warmup_epochs=0, huber_delta=200.0
            )
            total_loss.backward()
            optimizer.step()
    else:
        # Real data loop
        loader = create_dataloader(wds_url, batch_size=256, macro_window=160, num_workers=2)
        for i, batch in enumerate(loader):
            if i >= train_batches: break
            
            x_2d = batch["manifold_2d"].to(device)
            c_friction = batch["c_friction"].to(device)
            target = batch["target"].to(device)
            
            optimizer.zero_grad()
            pred, z_core = model(x_2d, c_friction.unsqueeze(-1))
            total_loss, _, _ = compute_spear_loss(
                pred, target, z_core, lambda_s=lambda_s, epoch=5, warmup_epochs=0, huber_delta=200.0
            )
            total_loss.backward()
            optimizer.step()

    # 4. Eval Loop
    model.eval()
    val_batches = 20
    print(f"[INFO] Evaluating for {val_batches} batches...")
    
    val_pf_rets = []
    val_preds = []
    val_targets = []
    
    with torch.no_grad():
        if use_synthetic:
            for i in range(val_batches):
                x_2d = torch.randn(256, 160, 10, 10, device=device)
                c_friction = torch.ones(256, device=device)
                target = torch.randn(256, device=device) * 100
                
                pred, z_core = model(x_2d, c_friction.unsqueeze(-1))
                _, pf_ret, _ = compute_spear_loss(
                    pred, target, z_core, lambda_s=lambda_s, epoch=5, warmup_epochs=0, huber_delta=200.0
                )
                val_pf_rets.append(pf_ret.item())
                val_preds.extend(pred.cpu().numpy())
                val_targets.extend(target.cpu().numpy())
        else:
            for i, batch in enumerate(loader):
                if i < train_batches: continue # Skip train batches roughly
                if i >= train_batches + val_batches: break
                
                x_2d = batch["manifold_2d"].to(device)
                c_friction = batch["c_friction"].to(device)
                target = batch["target"].to(device)
                
                pred, z_core = model(x_2d, c_friction.unsqueeze(-1))
                _, pf_ret, _ = compute_spear_loss(
                    pred, target, z_core, lambda_s=lambda_s, epoch=5, warmup_epochs=0, huber_delta=200.0
                )
                val_pf_rets.append(pf_ret.item())
                val_preds.extend(pred.cpu().numpy())
                val_targets.extend(target.cpu().numpy())

    if not val_pf_rets or len(val_preds) == 0:
        print("FINAL_REWARD=0.0")
        return
        
    avg_pf_ret = sum(val_pf_rets) / len(val_pf_rets)
    
    # --- Data-Driven Spread Calculation (No arbitrary 30 BP hardcode) ---
    preds = np.array(val_preds).flatten()
    targets = np.array(val_targets).flatten()
    std_yhat = np.std(preds)
    
    # Calculate D9 (Top 10%) and D0 (Bottom 10%) Returns
    p90 = np.percentile(preds, 90)
    p10 = np.percentile(preds, 10)
    
    mask_d9 = preds >= p90
    mask_d0 = preds <= p10
    
    ret_d9 = targets[mask_d9].mean() if mask_d9.any() else 0.0
    ret_d0 = targets[mask_d0].mean() if mask_d0.any() else 0.0
    
    spread = ret_d9 - ret_d0
    
    # 5. Composite North Star Metric
    # We target medium/long-term accumulation, so we only care about the Spread overcoming friction (25 BP).
    # If the model achieves a good spread with low variance, that's fine. We penalize ONLY if spread < 25 BP.
    cost_threshold = 25.0
    penalty = 2.0 * max(0.0, cost_threshold - spread)
    reward = spread - penalty
    
    print("-"*60)
    print(f"[RESULTS] Val_PfRet:   {avg_pf_ret:.4f}")
    print(f"[RESULTS] Val_Std_yhat:  {std_yhat:.4f} BP")
    print(f"[RESULTS] D9 Return:   {ret_d9:.4f}")
    print(f"[RESULTS] D0 Return:   {ret_d0:.4f}")
    print(f"[RESULTS] D9-D0 Spread: {spread:.4f} BP")
    print(f"[RESULTS] Penalty:     {penalty:.4f} (Target Spread > {cost_threshold} BP)")
    print(f"FINAL_REWARD={reward:.4f}")
    print("="*60)

if __name__ == "__main__":
    main()
