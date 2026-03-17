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