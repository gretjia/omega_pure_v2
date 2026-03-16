# OMEGA PURE V2 (Epiplexity Plus)

This project directory houses the **Epiplexity Plus** architecture, an axiomatic rewrite of the Omega mathematical core based on the principles of **Finite Window Theory** and **Two-Part MDL Loss**.

## Distinctions from V1 (`omega_pure`)
* **V1:** Utilized 2D Spatio-Temporal matrices but treated SRL and Epiplexity as external data features extracted via ETL (`omega_tensor_materializer.py`).
* **V2:** Integrates SRL directly into the PyTorch network as a non-learnable physical inverter layer (`AxiomaticSRLInverter`), and forces the extraction of Epiplexity directly through the network's loss function (`compute_epiplexity_mdl_loss`) rather than pre-calculating it on disk.

## Core Mathematics
* `omega_epiplexity_plus_core.py`: The fundamental physical compressor module.