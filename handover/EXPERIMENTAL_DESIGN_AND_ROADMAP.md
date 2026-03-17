# Omega Pure V2 - Experimental Design & Strategic Roadmap

This document outlines the foundational experiments that established the physical constants for the Omega Pure V2 architecture, details the current heavy-compute execution, and defines the criteria for success in the upcoming mathematical proving phases.

---

## 1. The Genesis Experiment: Empirical Calibration

**Objective:** To abandon human-guessed hyperparameters and empirically derive the foundational physical constants of the A-share market's micro-structure using a data-driven approach ("Science, evidence, and data over intuition").

### 1.1 Experimental Design
The experiment was designed to compute two strictly physical parameters for the new **Volume Clock (Turnover Clock)** architecture:
1.  **`vol_threshold` (The Minimal Resolution):** How much cumulative trading volume constitutes a single, meaningful "tick" or "bar" in our 2D matrix?
2.  **`window_size` (The Maximum Receptive Field):** How long does the market "remember" a micro-structural break? What is the maximum physical height of our 2D tensor?

### 1.2 Data Sampling Strategy (Why 1%?)
*   **The Constraint:** The raw L1 dataset is 2.2TB. Loading even a fraction of this into Pandas `df.collect()` triggers catastrophic OOM failures on our worker nodes.
*   **The Statistical Justification:** Market micro-structure rules (like the distribution of daily volume and the decay of autocorrelation in returns) are macro-statistical properties. A **1% uniform random sample** across the 743 raw Parquet shards provides a statistically significant representation of the market across various regimes (bull, bear, volatile, flat) without exceeding the 4GB RAM safety threshold during stream processing.

### 1.3 Execution & Core Logic

**Phase 1: Deriving `vol_threshold` (ADV Distribution)**
*   **Method:** Stream the 1% sample. Group data by `(Symbol, Date)` and sum the `vol_tick` to find the Average Daily Volume (ADV) for every stock-day pair.
*   **Calculation:** We calculate the **median** daily volume across the entire sample. To ensure we capture high-frequency structural breaks without drowning in noise, we target a resolution of approximately **50 bars per day**.
*   **Formula:** `vol_threshold = median(all_daily_volumes) / 50`
*   **Result:** The empirical calculation yielded exactly **50,000** (5万手).

**Phase 2: Deriving `window_size` (Autocorrelation Decay)**
*   **Method:** Using the newly derived `vol_threshold=50000`, we logically slice the sample data into Volume Bars in memory. For each symbol, we compute the Square Root Law (SRL) Residual and Epiplexity.
*   **Calculation:** We calculate the Autocorrelation Function (ACF) of these micro-structural signals across various lags (1 to 150). We are looking for the exact lag where the signal decays into pure white noise (i.e., the ACF value drops below statistical significance, `< 0.05`).
*   **Core Code (Zero-Dependency ACF):**
    ```python
    def simple_acf(x, nlags):
        n = len(x)
        variance = np.var(x)
        if variance == 0: return np.zeros(nlags)
        x = x - np.mean(x)
        result = np.correlate(x, x, mode='full')[-n:]
        result /= (variance * n)
        return result[:nlags+1]
    ```
*   **Result:** The memory decay consistently flatlined well within 160 lags. To provide the HPO engine with the maximum possible search space covering a ~3-day macro-accumulation cycle, the physical ceiling was locked at **160**.

---

## 2. Current Execution: The Data Collapse

**What are we doing right now?**
We are executing a dual-node (Windows1 + Linux1) heavy ETL process (`etl_lazy_sink_linux_optimized.py`).
*   **The Computation:** We are streaming the entire **2.2TB** raw Level-1 tick data lake. For every single stock, we maintain an isolated state machine. Every time a stock's cumulative volume hits `50,000`, we snapshot the OHLC, total volume, SRL Residual, and Epiplexity into a row. Once a stock accumulates 160 rows, it is flattened and written to disk as a complete 2D matrix.
*   **Expected Result:** The irreversible compression of 2.2TB of noisy, uneven Wall-Clock data into **188GB** of pristine, uniformly shaped `[160, 7]` Volume-Clocked tensors, saved as Snappy-compressed Parquet shards.

---

## 3. The Future Roadmap & Success Criteria

Once the 188GB of "pure fuel" is generated, we enter the proving grounds.

### Phase 2: Cloud Blind Test (HPO Blitzkrieg)
*   **Action:** Package the 188GB shards into `.tar` files (WebDataset format) and upload to GCP. Launch Google Vizier across 100x L4 GPUs.
*   **The Search:** The Bayesian optimizer will search for the optimal `macro_window` (e.g., slicing the 160 rows down to 40, 60, or 120) and `coarse_graining_factor` (dynamic pooling) to find the "sweet spot" of institutional invisibility cloaks.
*   **Expected Result Format:** A set of converged hyperparameters.
*   **Success Criterion:** The model's validation loss (Fraction of Variance Unexplained - **FVU**) must show a distinct, sharp minimum at a specific spatial-temporal scale, proving that the "Topological Break" exists at a specific, discoverable mathematical depth, rather than being random noise.

### Phase 3: The Forge (Full Scale Training)
*   **Action:** Lock in the optimal hyperparameters discovered in Phase 2. Train the full `SpatioTemporal2DMAE` (with the Finite Window Topological Attention core) on the 8x A100 cluster over the entire dataset.
*   **Expected Result Format:** The final weights file: `omega_2d_oracle.pth`.
*   **Success Criterion:** The model must successfully reconstruct masked SRL residuals and Epiplexity gradients with high fidelity (low MSE) on completely unseen out-of-sample data, proving it has learned the underlying physics of institutional execution.

### Phase 4: The Crucible (Embarrassingly Parallel Event Study)
*   **Action:** Deploy the trained `omega_2d_oracle.pth` to the Mac Studio. Run `omega_parallel_crucible.py` to scan historical data, firing "signals" whenever the model detects a massive mathematical anomaly (high Epiplexity + specific SRL divergence).
*   **Expected Result Format:** A generated backtest ledger (CSV/Parquet) detailing hypothetical entry/exit points and returns.
*   **Ultimate Success Criterion:** The **Asymmetry Payoff Ratio**. The ratio of the average win to the average loss must be strictly **> 3.0**. This is the final, irrefutable proof that the mathematical core has successfully isolated non-random, exploitable institutional accumulation patterns.

---

## 4. Architect's Supplementary Note
The shift from 1D Time-Series to a 2D Volume-Clocked Matrix is not just an engineering optimization to prevent OOMs. It is a fundamental philosophical shift. We have mathematically smoothed out the heterogeneity of the market. In this new space, a $100B mega-cap and a $1B micro-cap look geometrically identical to the Neural Network, allowing the attention mechanism to focus purely on the *physics of the order flow* rather than the arbitrary speed of the clock on the wall.