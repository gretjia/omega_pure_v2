# Omega Pure V3: Full-Pipeline Smoke Test & Vertex AI Ignition Plan

## 1. Objective
To construct a rigorous, end-to-end "Smoke Test" that validates the integrity of the V3 Volume-Clocked Parquet shards as they transition through WebDataset packaging (`The Chrono-Forge`), GCP ingestion, and finally, into the memory of a Vertex AI GPU cluster. This test must intentionally provoke and rule out historical failure modes (OOMs, dimensionality collapse, format mismatch).

## 2. The Legacy Failure Modes (What we must prove is fixed)
*   **The "OOM on DDP" Trap:** Previous attempts to load Parquet directly in a Distributed Data Parallel (DDP) environment caused CPU RAM to explode as multiple worker processes copied the entire dataset into shared memory.
*   **The Dimensionality Mismatch:** The core math engine expects `[Batch, Time, Spatial, Features]`. Previous pipelines accidentally flattened the spatial depth (LOB).
*   **The Quota/Resource Starvation:** Submitting jobs with unverified resource requests caused Vertex AI to hang indefinitely or crash on startup.

## 3. The End-to-End Smoke Test Execution Plan

### Step 3.1: The Chrono-Forge (Local Sharding to WebDataset)
**Goal:** Convert the raw V3 Parquet output into streaming `.tar` shards.
*   **Action:** Run a strictly bounded `tar` creation script locally on `omega-vm` or `mac-studio`.
*   **Validation:** 
    *   Do the generated `.tar` files open correctly?
    *   Do they contain the expected internal structure (`.cls`, `.data.npy`, etc.)?
    *   *Code:* We will write and execute a `test_wds_local.py` script that attempts to read a single `.tar` file using the exact `dynamic_processor` logic from `omega_webdataset_loader.py`.
*   **Success Metric:** The local dataloader successfully yields a PyTorch tensor of shape `[Batch, 160, 20, 4]` without throwing schema or `npy` decoding errors.

### Step 3.2: GCP Ingestion & Integrity Check
**Goal:** Safely move the WebDataset shards to Google Cloud Storage.
*   **Action:** Upload the validated `.tar` shards to `gs://omega-pure-data/wds_shards_v3/`.
*   **Validation:**
    *   Perform a `gcloud storage ls` and check the total byte size to ensure no truncation occurred during upload.
    *   *Code:* Execute a lightweight, single-node Vertex AI Custom Job (e.g., using an inexpensive `n1-standard-4` or `e2-standard-4` machine) that purely runs the `create_dataloader` function pointing to the `gs://` URI.
*   **Success Metric:** The cloud job successfully downloads the stream and prints the tensor shapes to Cloud Logging without running out of memory.

### Step 3.3: The "Mini-Forge" (Vertex AI GPU OOM Stress Test)
**Goal:** Prove that the Iterable WebDataset prevents OOMs when scaled to a GPU instance, and that the tensor mapping aligns with the `FiniteWindowTopologicalAttention` core.
*   **Action:** Submit a Vertex AI Custom Training Job requesting **1x L4 GPU** (`g2-standard-4`).
*   **Payload:** A stripped-down version of `vertex_mae_blitz_v5.py`. It will instantiate the `SpatioTemporal2DMAE` model and run exactly **5 forward passes** and **1 backward pass** (loss calculation).
*   **Validation (The "Crash-Test"):**
    *   Does the DDP `DataLoader` initialization cause host RAM to spike? (It shouldn't, thanks to WDS).
    *   Do the keys (`price_impact_2d`, `v_d`, etc.) extracted by the loader perfectly map to the `forward()` signature of the model?
    *   Does the model compute a valid loss (not `NaN`)?
*   **Success Metric:** The job completes with `Status: SUCCEEDED`. Cloud Monitoring shows Host RAM usage stable at `< 4GB`, and GPU VRAM usage stable. The log prints a numerical Loss value.

## 4. Post-Smoke Test Decision Gate
Once Step 3.3 passes, the mathematical, engineering, and cloud infrastructure pipelines are formally verified as sound. 

At that precise moment, we are cleared to execute the **100x L4 HPO Blitzkrieg (Phase 2)**. Any failure during the smoke test will trigger the `Recursive Auditor` agent to intervene before we burn expensive cloud quota.