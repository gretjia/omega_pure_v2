"""
OMEGA-TIB V3: The Volume-Clocked Topo-Forge (Multi-Core Edition)
-----------------------------------------------------------------
Single-pass streaming with bounded per-symbol buffers.
Batch column extraction (to_numpy, no .as_py()). Cross-file state continuity.
Symbol-level parallelism: each worker processes a subset of symbols across all files.

Tensor: [160, 10, 10] — Time × Spatial × Features
Target: Forward VWAP return in BP (H=20 bars, N+1 entry delay)

Performance design (Bitter Lessons compliance):
  - No gc.collect() in loops (#4)
  - No unconditional use_threads=True (#4)
  - OMP_NUM_THREADS=1 (no oversubscription)
  - Must run via systemd-run --slice=heavy-workload.slice (#3)
  - fcntl single-instance lock (#6)
  - Bounded memory: ~344MB/worker × 12 workers = 4.1GB / 61GB = 6.7%
  - Batch column extraction: 350M .as_py() → ~44 to_numpy() per batch
  - PyArrow-level symbol filtering: 100K rows → ~8K rows per worker
"""

import os
import sys
import json
import time
import glob
import shutil
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import webdataset as wds
from collections import deque
from multiprocessing import Process, Queue
import logging

if sys.platform != "win32":
    import fcntl

# Force thread count to 1 — prevents oversubscription (Bitter Lesson #4)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================
# Physical Constants (from current_spec.yaml)
# ==========================================
MACRO_WINDOW = 160
STRIDE = 20
ADV_FRACTION = 1 / 50.0
SPATIAL_DEPTH = 10
FEATURE_DIM = 10
SHARD_MAX_COUNT = 5000
PAYOFF_HORIZON = 20
# Minimum bars needed before we can emit a window with valid target
MIN_BUFFER_FOR_EMIT = MACRO_WINDOW + 1 + PAYOFF_HORIZON  # 181

# LOB column names (pre-computed to avoid f-string overhead in loops)
_LOB_COLUMNS = []
for _lvl in range(1, SPATIAL_DEPTH + 1):
    _LOB_COLUMNS.extend([f'bid_p{_lvl}', f'bid_v{_lvl}', f'ask_p{_lvl}', f'ask_v{_lvl}'])


class OmegaVolumeClockStateMachine:
    """
    Volume-Clock state machine with bounded streaming buffer.
    Emits windows as soon as forward target data is available.
    Memory per symbol: ~350 bars max × 400 bytes = 140KB (hard capped).
    Total for 5000 symbols: ~700MB worst case.
    """
    MAX_BUFFER_SIZE = MACRO_WINDOW + PAYOFF_HORIZON + STRIDE + 50  # ~350 bars hard cap

    def __init__(self, symbol: str, c_friction: float = 0.842):
        self.symbol = symbol
        self.c_friction = c_friction

        # Macro anchors (20-day rolling)
        self.rolling_adv = deque(maxlen=20)
        self.rolling_sigma = deque(maxlen=20)
        self.vol_threshold = 50000.0
        self.macro_v_d = 5000000.0
        self.macro_sigma_d = 0.50

        # Volume bar accumulation
        self.cum_vol = 0.0
        self.bar_ticks_prices = []
        self.bar_ticks_vols = []
        self.bar_last_tick = None
        self.bar_first_price = 0.0

        # Streaming bounded buffer: (spatial_bar, vwap) pairs
        self.bar_buffer = []       # list of spatial_bar arrays
        self.vwap_buffer = []      # list of vwap floats
        self.emit_cursor = 0       # next window start index

        # Daily tracking
        self.daily_high = -np.inf
        self.daily_low = np.inf

    def update_daily_macro(self, daily_vol: float):
        """End-of-day: update rolling ADV and rolling ATR."""
        if daily_vol > 0:
            self.rolling_adv.append(daily_vol)
        daily_atr = max(self.daily_high - self.daily_low, 1e-4) if self.daily_high > self.daily_low else 1e-4
        self.rolling_sigma.append(daily_atr)

        self.macro_v_d = float(np.mean(self.rolling_adv)) if self.rolling_adv else 5000000.0
        self.macro_sigma_d = float(np.mean(self.rolling_sigma)) if self.rolling_sigma else 0.50
        self.vol_threshold = max(self.macro_v_d * ADV_FRACTION, 1000.0)

        self.daily_high = -np.inf
        self.daily_low = np.inf

    def push_tick_fast(self, price: float, vol_tick: float, bid_ask_snapshot: np.ndarray):
        """Fast tick push using pre-extracted columnar values.
        Returns (spatial_bar, vwap) if a volume bar completes, else (None, None).
        """
        self.bar_ticks_prices.append(price)
        self.bar_ticks_vols.append(vol_tick)
        self.bar_last_tick = bid_ask_snapshot
        if not self.bar_first_price:
            self.bar_first_price = price
        self.cum_vol += vol_tick

        if price > 0:
            if price > self.daily_high:
                self.daily_high = price
            if price < self.daily_low:
                self.daily_low = price

        if self.cum_vol >= self.vol_threshold:
            vwap_den = sum(self.bar_ticks_vols)
            if vwap_den <= 0:
                # Phantom bar from carryover with zero-vol ticks — drain and skip
                self.cum_vol -= self.vol_threshold
                self.bar_ticks_prices = []
                self.bar_ticks_vols = []
                self.bar_first_price = 0.0
                return None, None

            spatial_bar = self._collapse_fast(price)
            vwap_num = sum(p * v for p, v in zip(self.bar_ticks_prices, self.bar_ticks_vols))
            bar_vwap = vwap_num / vwap_den

            # Cap carryover to prevent cascading phantom bars
            self.cum_vol = min(self.cum_vol - self.vol_threshold, self.vol_threshold)
            self.bar_ticks_prices = []
            self.bar_ticks_vols = []
            self.bar_first_price = 0.0
            return spatial_bar, bar_vwap

        return None, None

    def add_bar_and_try_emit(self, spatial_bar: np.ndarray, bar_vwap: float):
        """Add bar to buffer. Yield (manifold, target) for each emittable window."""
        self.bar_buffer.append(spatial_bar)
        self.vwap_buffer.append(bar_vwap)

        results = []
        n = len(self.bar_buffer)

        # Emit all possible windows from emit_cursor
        while self.emit_cursor + MACRO_WINDOW <= n:
            last_bar_idx = self.emit_cursor + MACRO_WINDOW - 1
            # Need vwap at last_bar_idx+1 (entry) and last_bar_idx+1+H (exit)
            target_exit_idx = last_bar_idx + 1 + PAYOFF_HORIZON
            if target_exit_idx >= n:
                break  # Not enough future data yet

            manifold = np.stack(self.bar_buffer[self.emit_cursor:self.emit_cursor + MACRO_WINDOW], axis=0)
            entry_vwap = self.vwap_buffer[last_bar_idx + 1]
            exit_vwap = self.vwap_buffer[target_exit_idx]
            target = (exit_vwap - entry_vwap) / (entry_vwap + 1e-8) * 10000.0

            results.append((manifold, target))
            self.emit_cursor += STRIDE

        # Trim consumed bars to bound memory (hard cap: MAX_BUFFER_SIZE)
        if self.emit_cursor > MACRO_WINDOW or len(self.bar_buffer) > self.MAX_BUFFER_SIZE:
            trim = max(self.emit_cursor - MACRO_WINDOW, len(self.bar_buffer) - self.MAX_BUFFER_SIZE)
            if trim > 0:
                self.bar_buffer = self.bar_buffer[trim:]
                self.vwap_buffer = self.vwap_buffer[trim:]
                self.emit_cursor = max(0, self.emit_cursor - trim)

        return results

    def _collapse_fast(self, price_close: float) -> np.ndarray:
        """Fast spatial bar collapse using pre-stored snapshot."""
        snapshot = self.bar_last_tick  # [SPATIAL_DEPTH, 4] = bid_p, bid_v, ask_p, ask_v
        delta_p = price_close - self.bar_first_price

        spatial_matrix = np.zeros((SPATIAL_DEPTH, FEATURE_DIM), dtype=np.float32)
        spatial_matrix[:, 0:4] = snapshot  # Ch 0-3: LOB depth
        spatial_matrix[:, 4] = price_close  # Ch 4: Close
        # Ch 5-6: reserved (0.0)
        spatial_matrix[:, 7] = delta_p  # Ch 7: ΔP
        spatial_matrix[:, 8] = self.macro_v_d  # Ch 8: macro V_D
        spatial_matrix[:, 9] = self.macro_sigma_d  # Ch 9: macro σ_D

        return spatial_matrix


# ==========================================
# Helper Functions
# ==========================================

def _acquire_single_instance_lock():
    if sys.platform == "win32":
        return None
    lock_path = "/tmp/omega_etl_v3_topo_forge.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logging.error("Another ETL instance is already running. Exiting.")
        sys.exit(1)
    return lock_fd


_A_SHARE_PREFIXES = frozenset([
    '000', '001', '002', '003', '300', '301',  # SZSE main + SME + ChiNext
    '600', '601', '603', '605',                 # SSE main
    '688', '689',                               # STAR Market (科创板)
])


def _is_a_share(symbol: str) -> bool:
    """Check if symbol is a valid A-share stock (excludes bonds, ETFs, funds, repos)."""
    code = symbol.split('.')[0]
    return len(code) == 6 and code[:3] in _A_SHARE_PREFIXES


def _load_c_registry(path: str) -> dict:
    if path and os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    logging.warning(f"c_registry not found at {path}, using c_default=0.842")
    return {}


def _safe_col_to_numpy(col, dtype=np.float64):
    """Safely convert PyArrow column to numpy, handling nulls and type issues."""
    try:
        arr = col.to_numpy(zero_copy_only=False)
    except Exception:
        arr = col.to_pandas().values
    # np.array() always makes a writable copy + casts dtype in one step
    arr = np.array(arr, dtype=dtype)
    np.nan_to_num(arr, copy=False, nan=0.0)
    return arr


def _discover_symbols(all_files):
    """Scan all files to discover unique A-share symbols (column-only read, fast).
    Excludes bonds, ETFs, funds, repos — only valid A-share stock codes.
    """
    symbols = set()
    for fpath in all_files:
        pf = pq.ParquetFile(fpath)
        for batch in pf.iter_batches(batch_size=500000, columns=['symbol']):
            uniq = pc.unique(batch.column('symbol')).to_pylist()
            symbols.update(s for s in uniq if s and _is_a_share(s))
    return sorted(symbols)


def _merge_shards(output_dir, num_workers):
    """Merge worker shard directories into a single numbered sequence."""
    shard_idx = 0
    for w in range(num_workers):
        worker_dir = os.path.join(output_dir, f"worker_{w:02d}")
        if not os.path.exists(worker_dir):
            continue
        worker_shards = sorted(glob.glob(os.path.join(worker_dir, "omega_shard_*.tar")))
        for src in worker_shards:
            dst = os.path.join(output_dir, f"omega_shard_{shard_idx:05d}.tar")
            shutil.move(src, dst)
            shard_idx += 1
        # Remove empty worker dir
        try:
            os.rmdir(worker_dir)
        except OSError:
            pass
    logging.info(f"[MERGE] {shard_idx} shards merged and renumbered")
    return shard_idx


# ==========================================
# Worker ETL Process
# ==========================================

def _worker_etl(worker_id, target_symbols, all_files, shard_dir,
                c_registry, c_default, batch_size, result_queue=None):
    """
    Single worker ETL process with batch column extraction.
    Processes all files for a subset of symbols (or all symbols if target_symbols is None).

    Batch optimization: replaces 350M .as_py() calls with ~44 to_numpy() calls per batch.
    PyArrow-level symbol filtering reduces effective rows from 100K to ~8K per worker.
    """
    os.makedirs(shard_dir, exist_ok=True)
    abs_dir = os.path.abspath(shard_dir).replace("\\", "/")
    pattern = f"file:///{abs_dir}/omega_shard_%05d.tar"
    sink = wds.ShardWriter(pattern, maxcount=SHARD_MAX_COUNT)

    # Pre-compute PyArrow filter array for symbol-level filtering
    target_pa = pa.array(sorted(target_symbols)) if target_symbols else None

    global_states = {}  # symbol → {sm, curr_date, daily_vol}
    sample_idx = 0
    total_ticks = 0
    start_time = time.time()

    for file_idx, fpath in enumerate(all_files):
        file_start = time.time()
        parquet_file = pq.ParquetFile(fpath)

        for batch in parquet_file.iter_batches(batch_size=batch_size):
            n_rows_raw = batch.num_rows

            # ========== PYARROW-LEVEL SYMBOL FILTER ==========
            # Filter entire batch at C level before any numpy conversion.
            # For 12 workers: 100K rows → ~8K rows (420/5000 symbols ≈ 8%)
            if target_pa is not None:
                sym_filter = pc.is_in(batch.column('symbol'), value_set=target_pa)
                batch = batch.filter(sym_filter)

            n_rows = batch.num_rows
            if n_rows == 0:
                total_ticks += n_rows_raw
                continue

            # ========== BATCH COLUMN EXTRACTION ==========
            # Replaces 4 × n_rows .as_py() calls with 2 to_pandas() + 2 to_numpy()
            sym_arr = batch.column('symbol').to_pandas().values     # object array
            price_arr = _safe_col_to_numpy(batch.column('price'))   # float64
            vol_arr = _safe_col_to_numpy(batch.column('vol_tick'))  # float64
            date_arr = batch.column('date').to_pandas().values      # object array

            # ========== LOB BATCH PRE-BUILD ==========
            # Replaces up to 40 × n_triggered_rows .as_py() calls with
            # 40 to_numpy() calls (4 cols × 10 levels), amortized over entire batch.
            # For filtered batch (~8K rows): 8K × 10 × 4 × 4B = 1.3MB
            lob_data = np.zeros((n_rows, SPATIAL_DEPTH, 4), dtype=np.float32)
            for level_idx in range(SPATIAL_DEPTH):
                level = level_idx + 1
                lob_data[:, level_idx, 0] = _safe_col_to_numpy(
                    batch.column(f'bid_p{level}'), dtype=np.float32)
                lob_data[:, level_idx, 1] = _safe_col_to_numpy(
                    batch.column(f'bid_v{level}'), dtype=np.float32)
                lob_data[:, level_idx, 2] = _safe_col_to_numpy(
                    batch.column(f'ask_p{level}'), dtype=np.float32)
                lob_data[:, level_idx, 3] = _safe_col_to_numpy(
                    batch.column(f'ask_v{level}'), dtype=np.float32)

            # ========== TICK PROCESSING LOOP ==========
            for idx in range(n_rows):
                raw_sym = sym_arr[idx]
                # Guard against null/NaN symbols: to_pandas() converts nulls to NaN (float)
                if raw_sym is None or (isinstance(raw_sym, float) and np.isnan(raw_sym)):
                    continue
                symbol = str(raw_sym)
                if not symbol or not _is_a_share(symbol):
                    continue

                price = float(price_arr[idx])
                vol_tick = float(vol_arr[idx])
                tick_date = date_arr[idx]

                if symbol not in global_states:
                    c_i = c_registry.get(symbol, c_default)
                    global_states[symbol] = {
                        'sm': OmegaVolumeClockStateMachine(symbol, c_friction=c_i),
                        'curr_date': None,
                        'daily_vol': 0.0,
                    }

                ctx = global_states[symbol]
                sm = ctx['sm']

                # Day boundary
                if ctx['curr_date'] is not None and tick_date != ctx['curr_date']:
                    sm.update_daily_macro(ctx['daily_vol'])
                    ctx['daily_vol'] = 0.0

                ctx['curr_date'] = tick_date
                ctx['daily_vol'] += vol_tick

                # LOB snapshot: O(1) numpy slice from pre-built array
                if sm.cum_vol + vol_tick >= sm.vol_threshold * 0.8:
                    snapshot = lob_data[idx]  # [10, 4] — O(1) view
                else:
                    snapshot = (sm.bar_last_tick if sm.bar_last_tick is not None
                                else np.zeros((SPATIAL_DEPTH, 4), dtype=np.float32))

                spatial_bar, bar_vwap = sm.push_tick_fast(price, vol_tick, snapshot)
                if spatial_bar is not None:
                    emissions = sm.add_bar_and_try_emit(spatial_bar, bar_vwap)
                    for manifold, target_val in emissions:
                        sink.write({
                            "__key__": f"{symbol.replace('.', '_')}_{sample_idx:09d}",
                            "manifold_2d.npy": manifold,
                            "target.npy": np.array([target_val], dtype=np.float32),
                            "c_friction.npy": np.array([sm.c_friction], dtype=np.float32),
                            "meta.json": {"symbol": symbol, "timestamp": str(sample_idx)}
                        })
                        sample_idx += 1

            total_ticks += n_rows_raw

        # Progress logging
        file_elapsed = time.time() - file_start
        files_done = file_idx + 1
        files_remaining = len(all_files) - files_done

        if files_done % 10 == 0 or files_done == 1:
            total_elapsed = time.time() - start_time
            avg_per_file = total_elapsed / files_done
            eta_hours = (avg_per_file * files_remaining) / 3600
            logging.info(
                f"[Worker {worker_id}] {files_done}/{len(all_files)} files | "
                f"{sample_idx} samples | {total_ticks/1e6:.1f}M ticks | "
                f"{file_elapsed:.1f}s/file | ETA: {eta_hours:.1f}h"
            )

            if eta_hours > 15.0 and files_done >= 5:
                logging.warning(
                    f"⚠️ Worker {worker_id}: ETA {eta_hours:.1f}h exceeds 15h threshold! "
                    f"Consider adding workers or second node."
                )

    # Flush final day for all symbols
    for sym, ctx in global_states.items():
        ctx['sm'].update_daily_macro(ctx['daily_vol'])

    sink.close()
    total_time = time.time() - start_time
    logging.info(
        f"[Worker {worker_id}] Complete. {sample_idx} samples | "
        f"{len(global_states)} symbols | {total_ticks/1e6:.0f}M ticks | "
        f"{total_time/3600:.1f}h total"
    )

    if result_queue is not None:
        result_queue.put((worker_id, sample_idx, len(global_states), total_time))

    return sample_idx, len(global_states), total_time


# ==========================================
# Main Pipeline
# ==========================================

def topo_forge_pipeline(raw_parquet_dir: str, output_tar_dir: str,
                        symbols: list = None, c_registry_path: str = None,
                        batch_size: int = 100000, file_list_path: str = None,
                        workers: int = 1):
    """
    Single-pass streaming ETL with bounded per-symbol buffers.
    Cross-file state continuity. Batch column extraction.
    Symbol-level parallelism with --workers N.

    Args:
        raw_parquet_dir: Directory containing raw parquet files.
        output_tar_dir: Output directory for WebDataset tar shards.
        symbols: Optional list of target symbols to process.
        c_registry_path: Path to a_share_c_registry.json.
        batch_size: PyArrow batch size (default 100000).
        file_list_path: Optional text file with parquet paths (for split execution).
        workers: Number of parallel workers (1 = single-core, N = symbol-level parallel).
    """
    lock_fd = _acquire_single_instance_lock()
    os.makedirs(output_tar_dir, exist_ok=True)

    c_registry = _load_c_registry(c_registry_path)
    c_default = c_registry.get('__GLOBAL_A_SHARE_C__', 0.842)
    target_symbols = set(symbols) if symbols else None

    # Gather file list
    if file_list_path and os.path.exists(file_list_path):
        with open(file_list_path) as f:
            all_files = [line.strip() for line in f if line.strip()]
        logging.info(f"[FORGE] Using file list: {file_list_path} ({len(all_files)} files)")
    else:
        all_files = []
        for root, dirs, files in os.walk(raw_parquet_dir):
            for f in files:
                if f.endswith('.parquet'):
                    all_files.append(os.path.join(root, f))
    all_files.sort(key=lambda p: os.path.basename(p)[:8])  # chronological by date

    logging.info(f"[FORGE] {len(all_files)} files, batch_size={batch_size}, workers={workers}")

    if workers <= 1:
        # ========== SINGLE-WORKER MODE ==========
        # Batch-optimized but no parallelism. Writes directly to output_tar_dir.
        _worker_etl(0, target_symbols, all_files, output_tar_dir,
                     c_registry, c_default, batch_size)
    else:
        # ========== MULTI-WORKER MODE ==========
        # 1. Discover all symbols
        logging.info("[FORGE] Discovering symbols for partitioning...")
        if target_symbols:
            all_syms = sorted(target_symbols)
        else:
            all_syms = _discover_symbols(all_files)
        logging.info(f"[FORGE] {len(all_syms)} symbols discovered, splitting across {workers} workers")

        # 2. Round-robin split for even distribution
        groups = [[] for _ in range(workers)]
        for i, sym in enumerate(all_syms):
            groups[i % workers].append(sym)

        for w in range(workers):
            logging.info(f"  Worker {w}: {len(groups[w])} symbols")

        # 3. Launch worker processes
        result_queue = Queue()
        processes = []
        for w in range(workers):
            worker_dir = os.path.join(output_tar_dir, f"worker_{w:02d}")
            p = Process(
                target=_worker_etl,
                args=(w, set(groups[w]), all_files, worker_dir,
                      c_registry, c_default, batch_size, result_queue),
                name=f"etl-worker-{w}"
            )
            p.start()
            processes.append(p)
            logging.info(f"[FORGE] Worker {w} started (PID {p.pid})")

        # 4. Wait for all workers
        for p in processes:
            p.join()
            if p.exitcode != 0:
                logging.error(f"[FORGE] Worker {p.name} exited with code {p.exitcode}")

        # 5. Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        total_samples = sum(r[1] for r in results)
        total_symbols = sum(r[2] for r in results)
        max_time = max(r[3] for r in results) if results else 0
        logging.info(
            f"[FORGE] All {workers} workers done. "
            f"{total_samples} total samples, {total_symbols} symbols, "
            f"wall time: {max_time/3600:.1f}h"
        )

        # 6. Merge worker shards into single numbered sequence
        _merge_shards(output_tar_dir, workers)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Omega-TIB V3 Topo-Forge ETL (Multi-Core)")
    parser.add_argument("--base_dir", type=str, required=True,
                        help="Directory containing raw parquet files")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="Output directory for WebDataset tar shards")
    parser.add_argument("--symbols", type=str, nargs='+',
                        help="Target symbols (optional, processes all if omitted)")
    parser.add_argument("--c_registry", type=str, default=None,
                        help="Path to a_share_c_registry.json")
    parser.add_argument("--batch_size", type=int, default=100000,
                        help="PyArrow batch size (default 100000)")
    parser.add_argument("--file_list", type=str, default=None,
                        help="Path to text file with parquet paths (for split execution)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of parallel workers (1=single-core, N=symbol-level parallel)")
    args = parser.parse_args()

    topo_forge_pipeline(args.base_dir, args.output_dir, args.symbols,
                        args.c_registry, args.batch_size, args.file_list,
                        args.workers)
