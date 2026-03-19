"""
OMEGA PURE V3: The Volume-Clocked Topo-Forge (Phase 0.5 Rewrite)
-----------------------------------------------------------------
Implements: Omega-TIB 10-channel tensor, cross-file state continuity,
macro V_D/σ_D anchors, VWAP forward target, per-stock c_friction.

Tensor: [160, 10, 10] — Time × Spatial × Features
Features: [Bid_P, Bid_V, Ask_P, Ask_V, Close, reserved, reserved, ΔP, macro_V_D, macro_σ_D]

Changes from previous version (Codex audit fixes):
  - Cross-file symbol state: global dict persists across all files
  - 10 channels (was 7): added ΔP, macro_V_D, macro_σ_D
  - Rolling sigma_d (20-day ATR) alongside rolling ADV
  - VWAP per volume bar + forward target computation
  - c_friction per-stock lookup from a_share_c_registry.json
"""

import os
import sys
import json
import numpy as np
import pyarrow.parquet as pq
import webdataset as wds
from collections import deque
import logging

if sys.platform != "win32":
    import fcntl

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================
# Physical Constants (from current_spec.yaml)
# ==========================================
MACRO_WINDOW = 160
STRIDE = 20
ADV_FRACTION = 1 / 50.0    # 0.02
SPATIAL_DEPTH = 10
FEATURE_DIM = 10            # 7 base + ΔP + macro_V_D + macro_σ_D
SHARD_MAX_COUNT = 5000
PAYOFF_HORIZON = 20         # H bars for forward target


class OmegaVolumeClockStateMachine:
    """
    Volume-Clock state machine with macro physical anchors.
    Persists across files (cross-file state continuity).
    """
    def __init__(self, symbol: str, c_friction: float = 0.842):
        self.symbol = symbol
        self.c_friction = c_friction

        # Macro anchors (20-day rolling)
        self.rolling_adv = deque(maxlen=20)
        self.rolling_sigma = deque(maxlen=20)
        self.vol_threshold = 50000.0
        self.macro_v_d = 5000000.0
        self.macro_sigma_d = 0.50  # ATR in price units (~50 cents), updated daily

        # Volume bar accumulation
        self.cum_vol = 0.0
        self.current_bar_ticks = []
        self.current_bar_vwap_num = 0.0  # sum(price * vol)
        self.current_bar_vwap_den = 0.0  # sum(vol)

        # Ring buffer + stride
        self.ring_buffer = deque(maxlen=MACRO_WINDOW)
        self.vwap_buffer = deque(maxlen=MACRO_WINDOW + PAYOFF_HORIZON + 10)
        self.stride_counter = 0

        # Daily tracking
        self.daily_high = -np.inf
        self.daily_low = np.inf

    def update_daily_macro(self, daily_vol: float, daily_high: float, daily_low: float):
        """End-of-day: update rolling ADV and rolling ATR (absolute daily range)."""
        if daily_vol > 0:
            self.rolling_adv.append(daily_vol)
        # ATR = absolute daily range (high - low), NOT normalized
        # Must be in price units for SRL dimensional consistency: ΔP / (c · σ_D) → dimensionless
        daily_atr = max(daily_high - daily_low, 1e-4) if daily_high > daily_low else 1e-4
        self.rolling_sigma.append(daily_atr)

        self.macro_v_d = float(np.mean(self.rolling_adv)) if self.rolling_adv else 5000000.0
        self.macro_sigma_d = float(np.mean(self.rolling_sigma)) if self.rolling_sigma else 0.05
        self.vol_threshold = max(self.macro_v_d * ADV_FRACTION, 1000.0)

        self.daily_high = -np.inf
        self.daily_low = np.inf

    def push_tick(self, tick: dict):
        """Push a tick. Returns (spatial_bar, vwap) when volume bar completes, else (None, None)."""
        vol = tick.get('vol_tick', 0.0)
        price = tick.get('price', 0.0)

        self.current_bar_ticks.append(tick)
        self.cum_vol += vol
        self.current_bar_vwap_num += price * vol
        self.current_bar_vwap_den += vol

        if price > 0:
            self.daily_high = max(self.daily_high, price)
            self.daily_low = min(self.daily_low, price)

        if self.cum_vol >= self.vol_threshold:
            spatial_bar = self._collapse_to_spatial_bar()
            bar_vwap = self.current_bar_vwap_num / (self.current_bar_vwap_den + 1e-8)

            self.cum_vol -= self.vol_threshold
            self.current_bar_ticks = []
            self.current_bar_vwap_num = 0.0
            self.current_bar_vwap_den = 0.0
            return spatial_bar, bar_vwap

        return None, None

    def add_bar(self, spatial_bar: np.ndarray, bar_vwap: float):
        """Add completed bar to ring buffer. Returns manifold tensor if ready."""
        self.ring_buffer.append(spatial_bar)
        self.stride_counter += 1

        if len(self.ring_buffer) == MACRO_WINDOW and self.stride_counter >= STRIDE:
            self.stride_counter = 0
            return np.stack(list(self.ring_buffer), axis=0)  # [160, 10, 10]
        return None

    def _collapse_to_spatial_bar(self) -> np.ndarray:
        """Collapse accumulated ticks into [10, 10] spatial matrix."""
        last_tick = self.current_bar_ticks[-1]
        first_tick = self.current_bar_ticks[0]

        price_close = last_tick.get('price', 0.0)
        delta_p = last_tick.get('price', 0.0) - first_tick.get('price', 0.0)

        spatial_matrix = np.zeros((SPATIAL_DEPTH, FEATURE_DIM), dtype=np.float32)

        for i in range(SPATIAL_DEPTH):
            level = i + 1
            # Ch 0-3: LOB depth (static snapshot for TDA)
            spatial_matrix[i, 0] = last_tick.get(f'bid_p{level}', 0.0)
            spatial_matrix[i, 1] = last_tick.get(f'bid_v{level}', 0.0)
            spatial_matrix[i, 2] = last_tick.get(f'ask_p{level}', 0.0)
            spatial_matrix[i, 3] = last_tick.get(f'ask_v{level}', 0.0)
            # Ch 4: Close price
            spatial_matrix[i, 4] = price_close
            # Ch 5-6: Reserved (SRL/Epiplexity computed model-side)
            spatial_matrix[i, 5] = 0.0
            spatial_matrix[i, 6] = 0.0
            # Ch 7-9: SRL inversion inputs (macro physical anchors, broadcast)
            spatial_matrix[i, 7] = delta_p
            spatial_matrix[i, 8] = self.macro_v_d
            spatial_matrix[i, 9] = self.macro_sigma_d

        return spatial_matrix


def _acquire_single_instance_lock():
    """Acquire exclusive lock to prevent concurrent ETL instances."""
    if sys.platform == "win32":
        return None
    lock_path = "/tmp/omega_etl_v3_topo_forge.lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        logging.error("Another omega_etl_v3_topo_forge instance is already running. Exiting.")
        sys.exit(1)
    return lock_fd


def _load_c_registry(path: str) -> dict:
    """Load per-stock c_friction from calibration registry."""
    if path and os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    logging.warning(f"c_registry not found at {path}, using c_default=0.842 for all stocks")
    return {}


def topo_forge_pipeline(raw_parquet_dir: str, output_tar_dir: str,
                        symbols: list = None, c_registry_path: str = None):
    """
    Two-pass pipeline (id5 ruling: shift-based forward target):
      Pass 1: Stream all ticks → accumulate volume bars + VWAPs per symbol
      Pass 2: For each symbol, compute forward target via shift, then window + emit
    """
    lock_fd = _acquire_single_instance_lock()
    os.makedirs(output_tar_dir, exist_ok=True)

    c_registry = _load_c_registry(c_registry_path)
    c_default = c_registry.get('__GLOBAL_A_SHARE_C__', 0.842)

    all_files = []
    for root, dirs, files in os.walk(raw_parquet_dir):
        for f in files:
            if f.endswith('.parquet'):
                all_files.append(os.path.join(root, f))
    all_files.sort()

    target_symbols = set(symbols) if symbols else None

    # ================================================================
    # PASS 1: Stream ticks → collect volume bars per symbol
    # ================================================================
    logging.info(f"[FORGE PASS 1] Streaming {len(all_files)} files → volume bars")
    global_symbol_states = {}
    # Per-symbol: list of (spatial_bar [10,10], vwap float)
    symbol_bars = {}

    for file_idx, fpath in enumerate(all_files):
        if (file_idx + 1) % 50 == 0 or file_idx == 0:
            logging.info(f"  File {file_idx+1}/{len(all_files)}: {os.path.basename(fpath)}")
        parquet_file = pq.ParquetFile(fpath)

        for batch in parquet_file.iter_batches(batch_size=100000):
            records = batch.to_pylist()
            for tick in records:
                symbol = tick.get('symbol')
                if not symbol:
                    continue
                if target_symbols and symbol not in target_symbols:
                    continue

                if symbol not in global_symbol_states:
                    c_i = c_registry.get(symbol, c_default)
                    global_symbol_states[symbol] = {
                        'sm': OmegaVolumeClockStateMachine(symbol, c_friction=c_i),
                        'curr_date': None,
                        'daily_vol': 0.0,
                    }
                    symbol_bars[symbol] = []

                ctx = global_symbol_states[symbol]
                sm = ctx['sm']
                tick_date = tick.get('date')

                if ctx['curr_date'] is not None and tick_date != ctx['curr_date']:
                    sm.update_daily_macro(ctx['daily_vol'], sm.daily_high, sm.daily_low)
                    ctx['daily_vol'] = 0.0

                ctx['curr_date'] = tick_date
                ctx['daily_vol'] += tick.get('vol_tick', 0.0)

                spatial_bar, bar_vwap = sm.push_tick(tick)
                if spatial_bar is not None:
                    symbol_bars[symbol].append((spatial_bar, bar_vwap))

    # Flush final day
    for sym, ctx in global_symbol_states.items():
        sm = ctx['sm']
        sm.update_daily_macro(ctx['daily_vol'], sm.daily_high, sm.daily_low)

    total_bars = sum(len(v) for v in symbol_bars.values())
    logging.info(f"[FORGE PASS 1] Done. {len(symbol_bars)} symbols, {total_bars} volume bars total.")

    # ================================================================
    # PASS 2: Compute forward targets via shift, then window + emit
    # ================================================================
    logging.info(f"[FORGE PASS 2] Computing targets + windowing → shards")
    abs_output_dir = os.path.abspath(output_tar_dir).replace("\\", "/")
    pattern = f"file:///{abs_output_dir}/omega_shard_%05d.tar"
    sink = wds.ShardWriter(pattern, maxcount=SHARD_MAX_COUNT)
    global_sample_idx = 0

    for sym, bars_list in symbol_bars.items():
        if len(bars_list) < MACRO_WINDOW + 1 + PAYOFF_HORIZON:
            continue  # Not enough bars for even one sample with target

        sm = global_symbol_states[sym]['sm']
        spatial_bars = [b[0] for b in bars_list]
        vwaps = np.array([b[1] for b in bars_list], dtype=np.float64)

        # Step 2a: Compute forward target for each bar via vectorized shift
        # For bar i: entry = vwap[i+1], exit = vwap[i+1+H]
        # target[i] = (exit - entry) / entry * 10000
        n_bars = len(vwaps)
        targets = np.zeros(n_bars, dtype=np.float32)
        for i in range(n_bars - 1 - PAYOFF_HORIZON):
            entry = vwaps[i + 1]
            exit_v = vwaps[i + 1 + PAYOFF_HORIZON]
            if entry > 1e-8:
                targets[i] = (exit_v - entry) / entry * 10000.0

        # Step 2b: Sliding window (size=160, stride=20) + bind target from last bar
        for start in range(0, n_bars - MACRO_WINDOW + 1, STRIDE):
            end = start + MACRO_WINDOW
            last_bar_idx = end - 1

            # Only emit if target is valid (not 0.0 from insufficient future)
            if last_bar_idx >= n_bars - 1 - PAYOFF_HORIZON:
                break  # No valid future target beyond this point

            manifold = np.stack(spatial_bars[start:end], axis=0)  # [160, 10, 10]
            target_val = targets[last_bar_idx]

            sink.write({
                "__key__": f"{sym}_{global_sample_idx:09d}",
                "manifold_2d.npy": manifold,
                "target.npy": np.array([target_val], dtype=np.float32),
                "c_friction.npy": np.array([sm.c_friction], dtype=np.float32),
                "meta.json": {"symbol": sym, "timestamp": str(global_sample_idx)}
            })
            global_sample_idx += 1
            if global_sample_idx % 1000 == 0:
                logging.info(f"  -> Emitted {global_sample_idx} samples...")

    sink.close()
    logging.info(f"[FORGE] Complete. {global_sample_idx} tensors from {len(symbol_bars)} symbols.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Omega-TIB V3 Topo-Forge ETL")
    parser.add_argument("--base_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--symbols", type=str, nargs='+', help="Target symbols (omit for all)")
    parser.add_argument("--c_registry", type=str, default=None,
                        help="Path to a_share_c_registry.json")
    args = parser.parse_args()

    topo_forge_pipeline(args.base_dir, args.output_dir, args.symbols, args.c_registry)
