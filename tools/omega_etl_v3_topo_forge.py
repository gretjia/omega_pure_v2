"""
OMEGA-TIB V3: The Volume-Clocked Topo-Forge (Phase 1A — Performance Optimized)
-------------------------------------------------------------------------------
Single-pass streaming with bounded per-symbol buffers.
Columnar batch processing (no to_pylist). Cross-file state continuity.

Tensor: [160, 10, 10] — Time × Spatial × Features
Target: Forward VWAP return in BP (H=20 bars, N+1 entry delay)

Performance design (Bitter Lessons compliance):
  - No gc.collect() in loops (#4)
  - No unconditional use_threads=True (#4)
  - OMP_NUM_THREADS=1 (no oversubscription)
  - Must run via systemd-run --slice=heavy-workload.slice (#3)
  - fcntl single-instance lock (#6)
  - Bounded memory: ~200 bars/symbol × 5000 symbols ≈ 400MB (#2)
  - Columnar batch extraction (avoids to_pylist dict creation overhead)
"""

import os
import sys
import json
import time
import numpy as np
import pyarrow.parquet as pq
import webdataset as wds
from collections import deque
import logging

if sys.platform != "win32":
    import fcntl

# Force thread count to 1 — prevents oversubscription (Bitter Lesson #4)
# Use direct assignment, not setdefault, to override any inherited env
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
            spatial_bar = self._collapse_fast(price)
            vwap_num = sum(p * v for p, v in zip(self.bar_ticks_prices, self.bar_ticks_vols))
            vwap_den = sum(self.bar_ticks_vols)
            bar_vwap = vwap_num / (vwap_den + 1e-8)

            self.cum_vol -= self.vol_threshold
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


def _load_c_registry(path: str) -> dict:
    if path and os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    logging.warning(f"c_registry not found at {path}, using c_default=0.842")
    return {}


def _extract_bid_ask_snapshot(batch, row_idx: int) -> np.ndarray:
    """Extract [10, 4] LOB snapshot from a single row, using columnar access."""
    snapshot = np.zeros((SPATIAL_DEPTH, 4), dtype=np.float32)
    for i in range(SPATIAL_DEPTH):
        level = i + 1
        snapshot[i, 0] = batch.column(f'bid_p{level}')[row_idx].as_py() or 0.0
        snapshot[i, 1] = batch.column(f'bid_v{level}')[row_idx].as_py() or 0.0
        snapshot[i, 2] = batch.column(f'ask_p{level}')[row_idx].as_py() or 0.0
        snapshot[i, 3] = batch.column(f'ask_v{level}')[row_idx].as_py() or 0.0
    return snapshot


def topo_forge_pipeline(raw_parquet_dir: str, output_tar_dir: str,
                        symbols: list = None, c_registry_path: str = None,
                        batch_size: int = 100000):
    """
    Single-pass streaming ETL with bounded per-symbol buffers.
    Cross-file state continuity. Columnar batch processing.
    """
    lock_fd = _acquire_single_instance_lock()
    os.makedirs(output_tar_dir, exist_ok=True)
    abs_output_dir = os.path.abspath(output_tar_dir).replace("\\", "/")
    pattern = f"file:///{abs_output_dir}/omega_shard_%05d.tar"
    sink = wds.ShardWriter(pattern, maxcount=SHARD_MAX_COUNT)

    c_registry = _load_c_registry(c_registry_path)
    c_default = c_registry.get('__GLOBAL_A_SHARE_C__', 0.842)
    target_symbols = set(symbols) if symbols else None

    all_files = []
    for root, dirs, files in os.walk(raw_parquet_dir):
        for f in files:
            if f.endswith('.parquet'):
                all_files.append(os.path.join(root, f))
    all_files.sort()

    # Cross-file state
    global_states = {}  # symbol → {sm, curr_date, daily_vol}
    global_sample_idx = 0
    total_ticks = 0
    start_time = time.time()

    logging.info(f"[FORGE] {len(all_files)} files, batch_size={batch_size}, streaming mode")

    for file_idx, fpath in enumerate(all_files):
        file_start = time.time()
        parquet_file = pq.ParquetFile(fpath)

        for batch in parquet_file.iter_batches(batch_size=batch_size):
            n_rows = batch.num_rows
            # Columnar extraction (avoid to_pylist)
            sym_col = batch.column('symbol')
            price_col = batch.column('price')
            vol_col = batch.column('vol_tick')
            date_col = batch.column('date')

            for row_idx in range(n_rows):
                symbol = sym_col[row_idx].as_py()
                if not symbol:
                    continue
                if target_symbols and symbol not in target_symbols:
                    continue

                price = price_col[row_idx].as_py() or 0.0
                vol_tick = vol_col[row_idx].as_py() or 0.0
                tick_date = date_col[row_idx].as_py()

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

                # Extract LOB snapshot only when volume threshold is close
                # (optimization: avoid expensive snapshot for every tick)
                if sm.cum_vol + vol_tick >= sm.vol_threshold * 0.8:
                    snapshot = _extract_bid_ask_snapshot(batch, row_idx)
                else:
                    snapshot = sm.bar_last_tick if sm.bar_last_tick is not None else np.zeros((SPATIAL_DEPTH, 4), dtype=np.float32)

                spatial_bar, bar_vwap = sm.push_tick_fast(price, vol_tick, snapshot)
                if spatial_bar is not None:
                    emissions = sm.add_bar_and_try_emit(spatial_bar, bar_vwap)
                    for manifold, target_val in emissions:
                        sink.write({
                            "__key__": f"{symbol}_{global_sample_idx:09d}",
                            "manifold_2d.npy": manifold,
                            "target.npy": np.array([target_val], dtype=np.float32),
                            "c_friction.npy": np.array([sm.c_friction], dtype=np.float32),
                            "meta.json": {"symbol": symbol, "timestamp": str(global_sample_idx)}
                        })
                        global_sample_idx += 1

            total_ticks += n_rows

        file_elapsed = time.time() - file_start
        total_elapsed = time.time() - start_time
        files_done = file_idx + 1
        files_remaining = len(all_files) - files_done
        avg_per_file = total_elapsed / files_done
        eta_seconds = avg_per_file * files_remaining
        eta_hours = eta_seconds / 3600

        if files_done % 10 == 0 or files_done == 1:
            logging.info(
                f"[FORGE] {files_done}/{len(all_files)} files | "
                f"{global_sample_idx} samples | {total_ticks/1e6:.1f}M ticks | "
                f"{file_elapsed:.1f}s/file | ETA: {eta_hours:.1f}h"
            )

            # 15-hour warning threshold
            if eta_hours > 15.0 and files_done >= 5:
                logging.warning(
                    f"⚠️ ETA {eta_hours:.1f}h exceeds 15h threshold! "
                    f"Consider adding second node or optimizing batch_size."
                )

    # Flush final day
    for sym, ctx in global_states.items():
        ctx['sm'].update_daily_macro(ctx['daily_vol'])

    sink.close()
    total_time = time.time() - start_time
    logging.info(
        f"[FORGE] Complete. {global_sample_idx} tensors | "
        f"{len(global_states)} symbols | {total_ticks/1e6:.0f}M ticks | "
        f"{total_time/3600:.1f}h total"
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Omega-TIB V3 Topo-Forge ETL")
    parser.add_argument("--base_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--symbols", type=str, nargs='+', help="Target symbols")
    parser.add_argument("--c_registry", type=str, default=None)
    parser.add_argument("--batch_size", type=int, default=100000,
                        help="PyArrow batch size (default 100000)")
    args = parser.parse_args()

    topo_forge_pipeline(args.base_dir, args.output_dir, args.symbols,
                        args.c_registry, args.batch_size)
