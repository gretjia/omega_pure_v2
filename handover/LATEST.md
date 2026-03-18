# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-18 (Wednesday)

## 1. STRATEGIC PIVOT: The Volume-Clocked Topo-Forge (V3 ANCHORED)
*   **Status:** Transition to **OMEGA V3** is complete. All legacy "Wall-Clock" and flattened spatial data pipelines are officially deprecated.
*   **Architectural Compliance**: 
    *   **Dynamic ADV Threshold**: Implemented "Relative Capacity Clock" using rolling ADV.
    *   **Spatial Axis Restoration**: Restored 10-level LOB depth. Tensor shape: `[160, 10, 7]`.
    *   **Translation-Invariant Slicing**: Implemented Ring Buffer with `STRIDE=20`.
    *   **Cloud Native Output**: Directly generating WebDataset `.tar` shards for Vertex AI.
*   **Verification**: **TRIAL RUN SUCCESSFUL**. Processed BOE (000725), Moutai (600519), and ST Guonong (000004). Generated 1971 tensors in a 95MB `.tar` shard. Shape and feature mapping verified against `omega_webdataset_loader.py`.

## 2. CURRENT PHASE: Phase 1 - The Data Collapse (V3)
*   **Task:** Launching the full-scale TB-to-Tar collapse.
*   **Forge Nodes**:
    *   **Windows1**: Handling the full 743-shard pool (re-launched with V3 Topo-Forge script).
    *   **Linux1**: Handling `host=linux1` shards.
*   **Output Path**: `gs://omega-pure-data/wds_shards_v3/` (Upload in progress post-generation).

## 3. IMMEDIATE NEXT STEPS
1.  **Full Ignition**: Run `tools/omega_etl_v3_topo_forge.py` on the entire dataset across both nodes.
2.  **WebDataset Upload**: Periodically sync generated `.tar` shards to GCS.
3.  **Phase 2 HPO**: Once 188GB is on cloud, trigger the 100x L4 Bayesian search.
4.  **Smoke Test Phase 3.2**: Execute the cloud integrity check on a single node before the full training.

## 🛡️ ENGINEERING LESSONS INTEGRATED
*   Used `ShardWriter` for automatic sharding.
*   Fixed Windows path compatibility with `file:///` protocol.
*   Enforced `iter_batches` + `pylist` conversion for O(1) RAM.
