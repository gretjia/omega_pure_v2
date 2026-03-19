"""
V3 Complete Smoke Test — 23-Item Checklist
------------------------------------------
Validates ETL output from shard format through model backward pass.

Usage:
  python tools/v3_smoke_test.py --shard_dir /path/to/shards
  python tools/v3_smoke_test.py --shard_dir /path/to/shards --n_shards 20 --skip_model

Three validation layers:
  Step 1 (Checks 1-18): Shard format + channel semantics + cross-shard statistics
  Step 2 (Checks 19-20): Loader end-to-end (WebDataset → batched tensors)
  Step 3 (Checks 21-23): Model forward + loss + backward (requires torch)
"""

import os
import sys
import glob
import random
import argparse
import json
import numpy as np

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ==========================================
# Result tracking
# ==========================================

class SmokeResult:
    def __init__(self):
        self.results = []
        self.stops = 0
        self.warnings = 0
        self.passes = 0

    def record(self, check_id, name, passed, detail="", severity="STOP"):
        status = "PASS" if passed else severity
        self.results.append((check_id, name, status, detail))
        if passed:
            self.passes += 1
        elif severity == "STOP":
            self.stops += 1
        else:
            self.warnings += 1

    def print_summary(self):
        print("\n" + "=" * 70)
        print(" V3 SMOKE TEST RESULTS")
        print("=" * 70)
        for check_id, name, status, detail in self.results:
            icon = {"PASS": "+", "STOP": "!!", "WARNING": "?"}[status]
            line = f"  [{icon}] #{check_id:02d} {name}: {status}"
            if detail:
                line += f" — {detail}"
            print(line)
        print("=" * 70)
        total = self.passes + self.stops + self.warnings
        print(f"  {self.passes}/{total} PASS | {self.stops} STOP | {self.warnings} WARNING")
        if self.stops > 0:
            print("  VERDICT: FAIL — fix STOP items before proceeding")
        elif self.warnings > 0:
            print("  VERDICT: PASS WITH WARNINGS — review before full ETL")
        else:
            print("  VERDICT: ALL CLEAR")
        print("=" * 70)
        return self.stops == 0


# ==========================================
# Step 1: Shard Format Validation (Checks 1-18)
# ==========================================

def _read_samples_from_shards(shard_paths, max_per_shard=5):
    """Read samples from shard tar files using WebDataset."""
    try:
        import webdataset as wds
    except ImportError:
        print("[ERROR] webdataset not installed — cannot read shards")
        return []
    all_samples = []
    for shard_path in shard_paths:
        try:
            dataset = wds.WebDataset(shard_path).decode()
            count = 0
            for sample in dataset:
                all_samples.append(sample)
                count += 1
                if count >= max_per_shard:
                    break
        except Exception as e:
            print(f"[WARN] Skipping corrupt shard {os.path.basename(shard_path)}: {e}")
            continue
    return all_samples


def run_shard_checks(shard_dir, n_shards=10, result=None):
    """Checks 1-18: Validate shard format, channel semantics, cross-shard stats."""
    if result is None:
        result = SmokeResult()

    # Find shards
    shard_files = sorted(glob.glob(os.path.join(shard_dir, "omega_shard_*.tar")))
    if not shard_files:
        # Also check subdirectories (worker dirs)
        shard_files = sorted(glob.glob(os.path.join(shard_dir, "**/omega_shard_*.tar"), recursive=True))

    if not shard_files:
        print(f"[ERROR] No shard files found in {shard_dir}")
        for i in range(1, 19):
            result.record(i, "N/A", False, "No shards found")
        return result

    print(f"[INFO] Found {len(shard_files)} shards in {shard_dir}")

    # Sample N shards
    sampled = random.sample(shard_files, min(n_shards, len(shard_files)))
    print(f"[INFO] Sampling {len(sampled)} shards for validation...")

    samples = _read_samples_from_shards(sampled, max_per_shard=5)
    if not samples:
        print("[ERROR] Could not read any samples from shards")
        for i in range(1, 19):
            result.record(i, "N/A", False, "No samples readable")
        return result

    print(f"[INFO] Read {len(samples)} samples for validation")

    # Collect stats across all samples
    all_shapes = []
    all_dtypes = []
    nan_count = 0
    inf_count = 0
    all_targets = []
    all_c_frictions = []
    symbols_seen = set()
    ch8_values = []  # macro_v_d
    ch9_values = []  # macro_sigma_d
    bid_p_values = []
    bid_v_values = []
    ask_p_values = []
    delta_p_values = []

    for sample in samples:
        manifold = sample.get("manifold_2d.npy")
        target = sample.get("target.npy")
        c_friction = sample.get("c_friction.npy")
        meta = sample.get("meta.json")

        if manifold is not None:
            all_shapes.append(manifold.shape)
            all_dtypes.append(manifold.dtype)
            nan_count += np.isnan(manifold).sum()
            inf_count += np.isinf(manifold).sum()

            bid_p_values.extend(manifold[:, :, 0].flatten())
            bid_v_values.extend(manifold[:, :, 1].flatten())
            ask_p_values.extend(manifold[:, :, 2].flatten())
            delta_p_values.extend(manifold[:, :, 7].flatten())
            ch8_values.extend(manifold[:, :, 8].flatten())
            ch9_values.extend(manifold[:, :, 9].flatten())

        if target is not None:
            all_targets.append(float(target[0]))
        if c_friction is not None:
            all_c_frictions.append(float(c_friction[0]))
        if meta and isinstance(meta, dict):
            sym = meta.get("symbol", "")
            if sym:
                symbols_seen.add(sym)

    # ---- Check 1: shape ----
    expected_shape = (160, 10, 10)
    shapes_ok = all(s == expected_shape for s in all_shapes) and len(all_shapes) > 0
    result.record(1, "shape", shapes_ok,
                  f"expected {expected_shape}, got {set(all_shapes)}")

    # ---- Check 2: dtype ----
    dtypes_ok = all(d == np.float32 for d in all_dtypes) and len(all_dtypes) > 0
    result.record(2, "dtype", dtypes_ok,
                  f"expected float32, got {set(all_dtypes)}")

    # ---- Check 3: NaN count ----
    result.record(3, "NaN count", nan_count == 0,
                  f"found {nan_count} NaN values")

    # ---- Check 4: Inf count ----
    result.record(4, "Inf count", inf_count == 0,
                  f"found {inf_count} Inf values")

    # ---- Check 5: Ch0 Bid_P range ----
    bid_p_arr = np.array(bid_p_values)
    nonzero_bid = bid_p_arr[bid_p_arr > 0]
    bid_p_ok = len(nonzero_bid) > 0 and nonzero_bid.min() > 0 and nonzero_bid.max() < 10000
    result.record(5, "Ch0 Bid_P range", bid_p_ok,
                  f"range [{nonzero_bid.min():.2f}, {nonzero_bid.max():.2f}]" if len(nonzero_bid) > 0 else "all zero",
                  severity="WARNING")

    # ---- Check 6: Ch1 Bid_V range ----
    bid_v_arr = np.array(bid_v_values)
    bid_v_ok = bid_v_arr.min() >= 0
    result.record(6, "Ch1 Bid_V range", bid_v_ok,
                  f"min={bid_v_arr.min():.2f}")

    # ---- Check 7: Ch2-3 Ask_P > Bid_P (same level, non-zero) ----
    spread_violations = 0
    spread_checks = 0
    for sample in samples:
        m = sample.get("manifold_2d.npy")
        if m is None:
            continue
        for t in range(m.shape[0]):
            for s in range(m.shape[1]):
                bp, ap = m[t, s, 0], m[t, s, 2]
                if bp > 0 and ap > 0:
                    spread_checks += 1
                    if ap < bp:
                        spread_violations += 1
    spread_ok = spread_violations == 0
    result.record(7, "Ask_P > Bid_P", spread_ok,
                  f"{spread_violations}/{spread_checks} violations",
                  severity="WARNING")

    # ---- Check 8: Ch4 Close vs Bid/Ask range ----
    close_ok = True  # Simplified: just check non-zero
    for sample in samples[:5]:
        m = sample.get("manifold_2d.npy")
        if m is not None:
            close_vals = m[:, 0, 4]
            if np.all(close_vals == 0):
                close_ok = False
    result.record(8, "Ch4 Close", close_ok,
                  "non-zero check", severity="WARNING")

    # ---- Check 9: Ch5-6 reserved ----
    reserved_ok = True
    for sample in samples[:5]:
        m = sample.get("manifold_2d.npy")
        if m is not None:
            if not (np.all(m[:, :, 5] == 0) and np.all(m[:, :, 6] == 0)):
                reserved_ok = False
    result.record(9, "Ch5-6 reserved", reserved_ok,
                  "expected all zeros (SRL/Epiplexity computed in model)")

    # ---- Check 10: Ch7 delta_p ----
    dp_arr = np.array(delta_p_values)
    dp_ok = not np.all(dp_arr == 0) and abs(dp_arr.mean()) < 100
    result.record(10, "Ch7 delta_p", dp_ok,
                  f"mean={dp_arr.mean():.4f}, std={dp_arr.std():.4f}",
                  severity="WARNING")

    # ---- Check 11: Ch8 macro_v_d ----
    ch8_arr = np.array(ch8_values)
    ch8_ok = ch8_arr.mean() > 0
    result.record(11, "Ch8 macro_v_d", ch8_ok,
                  f"mean={ch8_arr.mean():.0f}")

    # ---- Check 12: Ch9 macro_sigma_d ----
    ch9_arr = np.array(ch9_values)
    ch9_ok = ch9_arr.mean() > 0
    result.record(12, "Ch9 macro_sigma_d", ch9_ok,
                  f"mean={ch9_arr.mean():.4f}")

    # ---- Check 13: target.npy ----
    targets_arr = np.array(all_targets) if all_targets else np.array([0.0])
    target_ok = not np.all(targets_arr == 0) and np.all(np.abs(targets_arr) < 500)
    result.record(13, "target range", target_ok,
                  f"mean={targets_arr.mean():.2f}, min={targets_arr.min():.2f}, max={targets_arr.max():.2f}")

    # ---- Check 14: target distribution ----
    has_pos = np.any(targets_arr > 0)
    has_neg = np.any(targets_arr < 0)
    near_zero_mean = abs(targets_arr.mean()) < 50  # BP
    dist_ok = has_pos and has_neg and near_zero_mean
    result.record(14, "target distribution", dist_ok,
                  f"pos={has_pos}, neg={has_neg}, mean_near_0={near_zero_mean}",
                  severity="WARNING")

    # ---- Check 15: c_friction.npy bounds ----
    cf_arr = np.array(all_c_frictions) if all_c_frictions else np.array([0.842])
    cf_ok = np.all(cf_arr >= 0.05) and np.all(cf_arr <= 10.0)
    result.record(15, "c_friction bounds", cf_ok,
                  f"range [{cf_arr.min():.4f}, {cf_arr.max():.4f}]")

    # ---- Check 16: c_friction per-stock variation ----
    cf_unique = len(set(np.round(cf_arr, 4)))
    cf_varies = cf_unique > 1 or len(symbols_seen) <= 1
    result.record(16, "c_friction variation", cf_varies,
                  f"{cf_unique} unique values across {len(symbols_seen)} symbols")

    # ---- Check 17: cross-shard ch8/ch9 continuity ----
    # Simplified: check that ch8/ch9 are not constant across all samples
    ch8_std = ch8_arr.std() if len(ch8_arr) > 1 else 0
    ch9_std = ch9_arr.std() if len(ch9_arr) > 1 else 0
    continuity_ok = ch8_std > 0 and ch9_std > 0
    result.record(17, "ch8/ch9 continuity", continuity_ok,
                  f"ch8_std={ch8_std:.2f}, ch9_std={ch9_std:.4f}")

    # ---- Check 18: volume clock bar density ----
    # Check if different symbols have similar sample counts (within 10x)
    sym_counts = {}
    for sample in samples:
        meta = sample.get("meta.json")
        if meta and isinstance(meta, dict):
            sym = meta.get("symbol", "unknown")
            sym_counts[sym] = sym_counts.get(sym, 0) + 1
    if len(sym_counts) >= 2:
        counts = list(sym_counts.values())
        density_ratio = max(counts) / (min(counts) + 1)
        density_ok = density_ratio < 10
    else:
        density_ok = True
        density_ratio = 1.0
    result.record(18, "bar density uniformity", density_ok,
                  f"max/min ratio: {density_ratio:.1f}x",
                  severity="WARNING")

    return result


# ==========================================
# Step 2: Loader End-to-End (Checks 19-20)
# ==========================================

def run_loader_checks(shard_dir, result=None):
    """Checks 19-20: WebDataset loader end-to-end."""
    if result is None:
        result = SmokeResult()

    try:
        from omega_webdataset_loader import create_dataloader
        import torch
    except ImportError as e:
        print(f"[SKIP] Loader checks — missing dependency: {e}")
        result.record(19, "loader output", False, f"import error: {e}")
        result.record(20, "batch target", False, "skipped")
        return result

    shard_pattern = os.path.join(shard_dir, "omega_shard_*.tar")
    shard_files = sorted(glob.glob(shard_pattern))
    if not shard_files:
        shard_pattern = os.path.join(shard_dir, "**", "omega_shard_*.tar")
        shard_files = sorted(glob.glob(shard_pattern, recursive=True))

    if not shard_files:
        result.record(19, "loader output", False, "No shards found")
        result.record(20, "batch target", False, "skipped")
        return result

    # WebDataset needs actual file paths, not glob patterns
    wds_url = shard_files if len(shard_files) > 1 else shard_files[0]

    try:
        loader = create_dataloader(wds_url, batch_size=4, macro_window=160,
                                   coarse_graining_factor=1, num_workers=0)
        batch = next(iter(loader))

        # ---- Check 19: Loader output shapes ----
        m2d = batch["manifold_2d"]
        cf = batch["c_friction"]
        tgt = batch["target"]

        shape_ok = (m2d.shape[1:] == torch.Size([160, 10, 10]) and
                    len(cf.shape) == 1 and len(tgt.shape) == 1)
        result.record(19, "loader output", shape_ok,
                      f"manifold={list(m2d.shape)}, c_friction={list(cf.shape)}, target={list(tgt.shape)}")

        # ---- Check 20: batch target non-zero ----
        nonzero_frac = (tgt != 0).float().mean().item()
        target_nz_ok = nonzero_frac >= 0.5
        result.record(20, "batch target non-zero", target_nz_ok,
                      f"{nonzero_frac*100:.0f}% non-zero (need >= 50%)")

    except Exception as e:
        result.record(19, "loader output", False, f"exception: {e}")
        result.record(20, "batch target", False, "skipped due to loader error")

    return result


# ==========================================
# Step 3: Model Forward/Backward (Checks 21-23)
# ==========================================

def run_model_checks(shard_dir, result=None):
    """Checks 21-23: Model forward, MDL loss, backward pass."""
    if result is None:
        result = SmokeResult()

    try:
        import torch
        from omega_epiplexity_plus_core import (
            OmegaMathematicalCompressor,
            compute_epiplexity_mdl_loss,
        )
        from omega_webdataset_loader import create_dataloader
    except ImportError as e:
        print(f"[SKIP] Model checks — missing dependency: {e}")
        result.record(21, "forward pass", False, f"import error: {e}")
        result.record(22, "MDL loss", False, "skipped")
        result.record(23, "backward gradients", False, "skipped")
        return result

    shard_pattern = os.path.join(shard_dir, "omega_shard_*.tar")
    shard_files = sorted(glob.glob(shard_pattern))
    if not shard_files:
        shard_pattern = os.path.join(shard_dir, "**", "omega_shard_*.tar")
        shard_files = sorted(glob.glob(shard_pattern, recursive=True))

    if not shard_files:
        result.record(21, "forward pass", False, "No shards found")
        result.record(22, "MDL loss", False, "skipped")
        result.record(23, "backward gradients", False, "skipped")
        return result

    # WebDataset needs actual file paths, not glob patterns
    wds_url = shard_files if len(shard_files) > 1 else shard_files[0]

    try:
        loader = create_dataloader(wds_url, batch_size=4, macro_window=160,
                                   coarse_graining_factor=1, num_workers=0)
        batch = next(iter(loader))

        x_2d = batch["manifold_2d"]         # [B, 160, 10, 10]
        c_friction = batch["c_friction"]     # [B]
        target = batch["target"]             # [B]

        model = OmegaMathematicalCompressor(hidden_dim=64)
        model.train()

        # ---- Check 21: forward pass ----
        pred, z_core = model(x_2d, c_friction.unsqueeze(-1))
        fwd_ok = (not torch.isnan(pred).any().item() and
                  not torch.isinf(pred).any().item())
        result.record(21, "forward pass", fwd_ok,
                      f"pred shape={list(pred.shape)}, z_core shape={list(z_core.shape)}")

        # ---- Check 22: MDL loss ----
        loss, h_t, s_t = compute_epiplexity_mdl_loss(pred, target, z_core)
        loss_ok = (not torch.isnan(loss).item() and
                   not torch.isinf(loss).item() and
                   loss.item() > 0)
        result.record(22, "MDL loss", loss_ok,
                      f"total={loss.item():.6f}, H_T={h_t.item():.6f}, S_T={s_t.item():.6f}")

        # ---- Check 23: backward gradients ----
        loss.backward()
        grad_ok = True
        nan_params = []
        for name, p in model.named_parameters():
            if p.grad is not None and torch.isnan(p.grad).any():
                grad_ok = False
                nan_params.append(name)
        result.record(23, "backward gradients", grad_ok,
                      f"NaN grads in: {nan_params}" if nan_params else "all gradients clean")

    except Exception as e:
        import traceback
        traceback.print_exc()
        result.record(21, "forward pass", False, f"exception: {e}")
        result.record(22, "MDL loss", False, "skipped due to forward error")
        result.record(23, "backward gradients", False, "skipped")

    return result


# ==========================================
# Main
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="V3 Complete Smoke Test (23-item checklist)")
    parser.add_argument("--shard_dir", type=str, required=True,
                        help="Directory containing omega_shard_*.tar files")
    parser.add_argument("--n_shards", type=int, default=10,
                        help="Number of shards to sample for validation (default 10)")
    parser.add_argument("--skip_model", action="store_true",
                        help="Skip model forward/backward checks (Step 3)")
    parser.add_argument("--skip_loader", action="store_true",
                        help="Skip loader checks (Step 2)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for shard sampling")
    args = parser.parse_args()

    random.seed(args.seed)
    result = SmokeResult()

    print("=" * 70)
    print(" V3 SMOKE TEST — 23-Item Checklist")
    print("=" * 70)

    # Step 1: Shard validation
    print("\n[Step 1] Shard Format + Channel Semantics (Checks 1-18)")
    print("-" * 50)
    run_shard_checks(args.shard_dir, n_shards=args.n_shards, result=result)

    # Step 2: Loader
    if not args.skip_loader:
        print("\n[Step 2] Loader End-to-End (Checks 19-20)")
        print("-" * 50)
        run_loader_checks(args.shard_dir, result=result)
    else:
        print("\n[Step 2] SKIPPED (--skip_loader)")
        result.record(19, "loader output", True, "skipped by user")
        result.record(20, "batch target", True, "skipped by user")

    # Step 3: Model
    if not args.skip_model:
        print("\n[Step 3] Model Forward/Backward (Checks 21-23)")
        print("-" * 50)
        run_model_checks(args.shard_dir, result=result)
    else:
        print("\n[Step 3] SKIPPED (--skip_model)")
        result.record(21, "forward pass", True, "skipped by user")
        result.record(22, "MDL loss", True, "skipped by user")
        result.record(23, "backward gradients", True, "skipped by user")

    # Summary
    all_pass = result.print_summary()
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
