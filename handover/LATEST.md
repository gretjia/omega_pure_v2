# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-18 (Wednesday) - **STATUS: HALTED**

## 1. 🚨 CURRENT EMERGENCY STATUS: ALL CALCULATIONS STOPPED
*   **Action**: All ETL and Topo-Forge processes on `Windows1` and `linux1-lx` have been terminated by user directive.
*   **System State**: Idle. No data is being generated. Residual V3 shards exist in local directories but the pipeline is frozen.

## 2. 🏛️ ARCHITECTURAL EVOLUTION (V1 -> V2 -> V3)

### Phase 1: Wall-Clock Genesis (V1 - Deprecated)
*   Used physical time (e.g., 1-minute bars).
*   Failed due to "Topological Tearing": High liquidity stocks had too much data, low liquidity stocks had too little, creating inconsistent 2D geometry for the neural network.

### Phase 2: Volume-Clock Genesis (V2 - Produced & Deleted)
*   **Principle**: Turnover-based sampling (event-based).
*   **Result**: 188GB produced with shape `[160, 7]` (OHLC + Volume + SRL + Epi).
*   **Audit Failure**: Recursive audit by Chief Architect (Doc ID 1) revealed "Dimensionality Collapse". It lacked the spatial axis (LOB depth) necessary for the `FiniteWindowTopologicalAttention` core.

### Phase 3: Topo-Forge Restoration (V3 - In Progress/Halted)
*   **Restored Spatial Axis**: Tensor shape upgraded to `[160, 10, 7]`.
*   **Relative Capacity Clock**: `vol_threshold` is now dynamic (2% of Rolling ADV per symbol).
*   **Translation Invariance**: Ring Buffer implementation with `STRIDE=20`.
*   **Cloud Native**: Direct WebDataset `.tar` sharding for GCP high-bandwidth I/O.

## 📊 EMPIRICAL CONSTANTS (MARCH 16-17 EXPERIMENTS)
*   **`vol_threshold`**: Determined via 1% uniform sample of 2.2TB. Target: ~50 bars/day. Result: 2% of ADV.
*   **`window_size`**: Determined via ACF (Autocorrelation Function) decay. Result: 160 lags (Market memory limit).

## 🛠️ INFRASTRUCTURE & POST-MORTEM (ENGINEERING TRAPS)
*   **SSH OOM Trap**: SSH session inheritance of `-1000` OOM score caused kernel deadlocks. Fix: Use `systemd-run` + `ManagedOOM`.
*   **cgroup Throttling**: `user.slice` was hard-clamped to `CPUQuota=80%`. Fix: Use `heavy-workload.slice` (`CPUQuota=2400%`).
*   **Python Anti-Patterns**: Explicit `gc.collect()` and `use_threads=True` in small tabular loops caused 56% performance regression. Fix: Removed `gc.collect()`, aligned `batch_size=500000`.

## 📈 PROJECT PROGRESS & FRICTION
*   **Windows1**: Produced 693/743 files (V2 logic) before pivot; produced ~20 V3 shards before halt.
*   **Linux1**: Produced 552/552 files (V2 logic) before pivot; produced ~100 V3 shards before halt.
*   **The V3 Bottle Neck**: V3 data density is ~80x higher than V2. ETA for full 2.2TB collapse is ~100 hours on current single-threaded logic.

## 🚀 IMMEDIATE NEXT STEPS FOR NEXT AGENT
1.  **Specification Decision**: Confirm with user if V3 `[160, 10, 7]` is the absolute requirement or if a lower-density V2.5 is acceptable.
2.  **Multi-Process Forge**: If V3 proceeds, rewrite `tools/omega_etl_v3_topo_forge.py` to use `ProcessPoolExecutor` (targeting 10+ cores on Linux1).
3.  **GCS Sync**: Initiate `gsutil -m rsync` to move generated shards to `gs://omega-pure-data/wds_shards_v3/`.
4.  **Vertex HPO**: Trigger 100x L4 Bayesian search once >100GB of V3 data is on cloud.
