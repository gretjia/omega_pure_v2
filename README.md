# OMEGA PURE V3: The Topological Volume-Clock Forge

This repository houses the **Omega Pure V3** architecture, a fundamental paradigm shift in high-frequency financial modeling. It moves beyond physical time ("Wall-Clock") to a pure **Volume-Clock (Turnover Clock)** topology, resolving the spatial-temporal tearing between high and low liquidity assets.

## 🏛️ Core Philosophy: The Volume Clock Genesis
The clock on the wall is a human illusion; the tape is the only truth. In V3, we reject uniform time-based sampling (e.g., 1-minute bars) in favor of **Event-Based Sampling**.

*   **Relative Capacity Clock**: Every data point ("Bar") in our 2D matrix represents a fixed percentage of a stock's daily liquidity (typically 2% of Rolling ADV).
*   **Geometric Equivalence**: By using a dynamic `vol_threshold`, a $100B mega-cap and a $1B micro-cap look **geometrically identical** to the neural network. Both occupy the same "Volume-Time" space.
*   **Spatial Axis Restoration**: We preserve the full 10-level Limit Order Book (LOB) depth (Bid/Ask) at each volume step, enabling true Topological Data Analysis (TDA) of order-flow connectivity.

## 🛠️ System Components

### 1. The Topo-Forge (`tools/omega_etl_v3_topo_forge.py`)
A heavy-duty, anti-OOM ETL engine that transforms TB-scale raw L1 Ticks into WebDataset `.tar` shards.
*   **Dynamic Thresholding**: Computes `vol_threshold` per symbol based on rolling ADV.
*   **Ring Buffer Slicing**: Uses a sliding window (`MACRO_WINDOW=160`, `STRIDE=20`) to capture continuous causal manifolds without tumbling-window truncation.
*   **Tensor Geometry**: Produces tensors of shape `[160, 10, 10]`.
*   **Features**: `[Bid_P, Bid_V, Ask_P, Ask_V, Close, reserved, reserved, ΔP, macro_V_D, macro_σ_D]`.

### 2. WebDataset Loader (`omega_webdataset_loader.py`)
A stateless, event-driven dataloader designed for distributed training on GCP Vertex AI.
*   **GPU Slicing**: Dynamically crops the 160-row window to an HPO-optimized `macro_window`.
*   **Dynamic Pooling**: Implements temporal coarse-graining on-the-fly.

### 3. Mathematic Core (`omega_epiplexity_plus_core.py`)
The axiomatic engine implementing **Finite Window Topological Attention** and **Epiplexity MDL Loss**.

## 📊 Experimental Constants (Data-Driven)
*   **`vol_threshold`**: Derived as `Rolling_ADV / 50` (Targeting ~50 bars per trading day).
*   **`window_size`**: Locked at `160`, found via Autocorrelation (ACF) decay analysis to be the maximum memory limit of micro-structural signals.

## 🚀 Phase History
| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Done | TB-scale Parquet → 1992 WDS Shards (556GB) |
| 2-4 | Done | HPO Blitzkrieg — Bayesian search on L4/A100 |
| 6 | Done | IC Loss HPO — T29 flagship (hd=64, IC=0.066, OOS/IS=1.00) |
| 7 | Done | Full inference + diagnostic (17-test) |
| 8 | Done | Backtest simulate — board_loss_cap Sharpe +34% |
| 9 | Failed | Asymmetric Pearson Loss — 7 jobs, all Reward Hacking |
| **10** | **Complete** | **Softmax Portfolio Loss — Val PfRet=0.210, pending backtest** |

## 📁 Key Scripts
| Script | Purpose |
|--------|---------|
| `train.py` | Training loop (Softmax Portfolio Loss, Phase 10) |
| `omega_epiplexity_plus_core.py` | Math core (SRL + FWT + MDL) |
| `omega_webdataset_loader.py` | WebDataset streaming loader |
| `tools/omega_etl_v3_topo_forge.py` | ETL: Parquet → WebDataset shards |
| `tools/phase7_inference.py` | Full inference (exports predictions + z_sparsity) |
| `tools/phase7_simulate.py` | T+1 overnight swing backtest simulator |
| `gcp/safe_build_and_canary.sh` | Docker build + 1-shard canary |
| `gcp/safe_submit.sh` | Full job submission with manifest tracking |

---
*For internal AI Agents: Start at [`handover/LATEST.md`](handover/LATEST.md). Engineering post-mortems in [`handover/ETL_ENGINEERING_LESSONS.md`](handover/ETL_ENGINEERING_LESSONS.md). Experience library in [`OMEGA_LESSONS.md`](OMEGA_LESSONS.md).*
