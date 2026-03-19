# OMEGA PURE V2 - ETL Engineering Post-Mortem & Best Practices

## 1. The "False OOM" & SSH Inheritance Trap
**Symptom:** Linux worker node appeared to "hang" or disconnect SSH during heavy ETL processing, while `uptime` showed no system reboot.
**Root Cause:** The `tmux` session or background script inherited the `-1000` `oom_score_adj` from the parent SSH daemon. When the ETL process hit the `user.slice` memory limits, the system's OOM killer was triggered but was *forbidden* from killing the very process causing the memory pressure. This resulted in an endless "Out of memory and no killable processes" kernel loop, locking up the system.
**Resolution:** 
1. Ensure SSH daemon does not propagate `-1000` to user sessions.
2. Always wrap heavy workloads in systemd slices with explicit `ManagedOOMMemoryPressure=kill` to guarantee clean termination.

## 2. The cgroup CPU Throttling Trap
**Symptom:** A 32-core AMD AI Max machine was processing data significantly slower than a comparably spec'd Windows machine, despite low I/O wait.
**Root Cause:** Running background tasks via raw `tmux` or `nohup` places them in the default `user-1000.slice`. On our specific Linux nodes, this slice is persistently clamped to `CPUQuota=80%` (less than 1 CPU core) for safety.
**Resolution:** NEVER run heavy data processing via raw `tmux`. Always "launch" the workload into the dedicated `heavy-workload.slice` (which has `CPUQuota=2400%`) using:
```bash
sudo systemd-run --slice=heavy-workload.slice --uid=1000 --description='Heavy ETL' --unit=my-etl-job python3 script.py
```

## 3. Python Data-Processing Anti-Patterns
**Symptom:** Even within the `heavy-workload.slice`, the Linux script was ~56% slower than the Windows baseline.
**Root Cause:** Well-intentioned "optimizations" introduced severe overhead.
*   **Explicit `gc.collect()` in tight loops:** Calling garbage collection explicitly after every 300k row batch forces Python to scan its entire object graph, destroying throughput. *Lesson: Trust Python's generational GC for short-lived chunked variables.*
*   **`to_pandas(use_threads=True)` overhead:** For simple tabular conversions without complex nested types, the thread context-switching overhead of Arrow's multithreading was higher than the conversion cost itself. *Lesson: Always benchmark threaded conversion; it is not a guaranteed speedup.*

## 4. The Limits of Parameter Tuning
**Observation:** After aligning `batch_size`, removing `gc.collect()`, and disabling `use_threads`, performance increased by ~56%. However, it still hit a hard ceiling where CPU usage hovered around ~100% (1 core).
**Architectural Truth:** The remaining bottleneck is `df.groupby('symbol')`. Pandas `groupby` iteration is fundamentally single-threaded. To breach this ceiling in the future, the algorithm must be horizontally sharded (e.g., using `joblib` or multiprocessing to process distinct groups of Parquet files concurrently), rather than trying to optimize the single-threaded Pandas loop further.

## 5. Batch Column Extraction (2026-03-19)
**Problem:** V3 ETL used `.as_py()` per cell — 350M Python↔C bridge calls per 73M-row file. 762s/file.
**Fix:** Replace with `to_numpy(zero_copy_only=False)` + `np.nan_to_num()` for bulk column extraction. Pre-build LOB array `[n_rows, 10, 4]` once per batch.
**Result:** 235s/file — **3.2x speedup**. Bottleneck shifted from `.as_py()` bridge to Python tick loop itself.
**Caveats:**
- `to_numpy()` can return read-only arrays (zero-copy view). Must use `np.array(arr, dtype=...)` to force writable copy.
- Null values in PyArrow become NaN in numpy. Use `np.nan_to_num(copy=False)` to clean in-place.
- Symbol column (`large_string`) should use `to_pandas().values` not `to_numpy()` for reliable string handling.

## 6. Symbol-Level Parallelism is a Dead End on Single Node (2026-03-19)
**Problem:** With cross-file state continuity (rolling 20-day ADV/ATR), each symbol must see ALL files in chronological order. Symbol-level parallelism splits symbols across N workers, but every worker still reads every file.
**Tested:** 12 workers × 743 files × 73M rows = 12× I/O for same data.
**Result:** 580s/file per worker (vs 235s single worker). 12 workers SLOWER than 1 worker. ZFS NVMe throughput wasted on 12 concurrent readers hitting the same blocks.
**Root Cause:** I/O is the bottleneck, not CPU. Single worker uses 80% of 1 core (2.5% of 32-core machine). Adding workers doesn't help CPU but destroys I/O locality.
**Conclusion:** For this ETL architecture, **single worker + batch optimization is optimal on single node**. True parallelism requires file-level split (different workers read different files), which breaks cross-file state. Future optimization: two-pass architecture (pass 1: parallel daily stats collection, pass 2: single-pass state machine with pre-computed macros).

## 7. Non-A-Share Symbols in c_registry (2026-03-19)
**Problem:** c_registry contained 8366 entries, but 3054 were bonds (1xxxxx), ETFs (159xxx/51xxxx), funds (16xxxx/501xxx), repos (204xxx).
**Impact:** Bond repos (204001.SZ) have interest-rate "prices" (~1.8), producing VWAP target values of 2.55×10¹⁶ BP. ETFs/funds have completely different LOB dynamics.
**Fix:** Added `_is_a_share()` filter matching valid A-share prefixes: 000/001/002/003/300/301/600/601/603/605/688/689. Applied at discovery, PyArrow filter, and tick loop levels. Reduces to 5312 valid stocks.

## 8. Phantom VWAP Bars from Volume Carryover (2026-03-19)
**Problem:** When a single tick has very large `vol_tick` (block trade), `cum_vol -= vol_threshold` leaves massive carryover. Subsequent ticks with `vol_tick=0` (order book updates, ~56% of all ticks) trigger bar emission with `sum(bar_ticks_vols) == 0`, producing VWAP=0. Target formula `(exit - entry) / (entry + 1e-8) * 10000` then explodes.
**Fix:** Skip bar emission when `vwap_den <= 0` (drain carryover without emitting). Cap `cum_vol` carryover to `min(cum_vol - threshold, threshold)` to prevent cascading phantom bars.
**Validation:** Target range recovered from `[-10000, 2.55e16]` to `[-328, +110]` BP after fix.