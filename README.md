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
*   **Tensor Geometry**: Produces tensors of shape `[160, 10, 7]`.
*   **Features**: `[Bid_Price, Bid_Vol, Ask_Price, Ask_Vol, Close, SRL_Residual, Epiplexity]`.

### 2. WebDataset Loader (`omega_webdataset_loader.py`)
A stateless, event-driven dataloader designed for distributed training on GCP Vertex AI.
*   **GPU Slicing**: Dynamically crops the 160-row window to an HPO-optimized `macro_window`.
*   **Dynamic Pooling**: Implements temporal coarse-graining on-the-fly.

### 3. Mathematic Core (`omega_epiplexity_plus_core.py`)
The axiomatic engine implementing **Finite Window Topological Attention** and **Epiplexity MDL Loss**.

## 📊 Experimental Constants (Data-Driven)
*   **`vol_threshold`**: Derived as `Rolling_ADV / 50` (Targeting ~50 bars per trading day).
*   **`window_size`**: Locked at `160`, found via Autocorrelation (ACF) decay analysis to be the maximum memory limit of micro-structural signals.

## 🚀 Deployment Roadmap
1.  **Phase 1: The Data Collapse**: TB-scale Parquet to 188GB+ WDS Shards.
2.  **Phase 2: HPO Blitzkrieg**: 100x L4 GPU Bayesian search for optimal spatial-temporal scales.
3.  **Phase 4: The Crucible**: Event-study backtesting with **Asymmetry Payoff Ratio > 3.0**.

---
*For internal AI Agents: Detailed engineering traps and post-mortems are located in `/handover/ETL_ENGINEERING_LESSONS.md`.*
