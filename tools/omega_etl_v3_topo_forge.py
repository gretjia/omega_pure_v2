"""
OMEGA PURE V3: The Volume-Clocked Topo-Forge
-------------------------------------------
Implements the Chief Architect's "Relative Capacity Clock" and "Spatial Axis Restoration".
Transforms 2.2TB raw L1 Ticks into WebDataset .tar shards [160, 10, 7].
"""

import os
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import webdataset as wds
from collections import deque
import logging
import sys

# Optimized for 64GB RAM limit and 32-core CPU
os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ==========================================
# 物理常数与超参数锁定 (Physical Constants)
# ==========================================
MACRO_WINDOW = 160         # 宏观拓扑高度：160个容量步长 (Volume Time Axis)
STRIDE = 20                # 环形缓冲区步长：每滑动20步截取一个张量 (重叠采样)
ADV_FRACTION = 1 / 50.0    # 动态容量阈值：单日平均成交量的 2%
SPATIAL_DEPTH = 10         # 盘口空间深度：买卖各 10 档
FEATURE_DIM = 7            # 特征通道: [Bid_P, Bid_V, Ask_P, Ask_V, Close, SRL_Res, Epiplexity]
SHARD_MAX_COUNT = 5000     # WebDataset 每个 .tar 碎片最大存放张量数 (约 1GB/shard)

class OmegaVolumeClockStateMachine:
    """
    第一性原理状态机：将无序的 Wall-Clock 物理时间，重铸为绝对几何等价的 Volume-Clock 2D 拓扑。
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.rolling_adv = deque(maxlen=20)
        self.vol_threshold = 50000.0  # 初始冷启动值
        self.cum_vol = 0.0
        self.current_bar_ticks = []
        self.ring_buffer = deque(maxlen=MACRO_WINDOW)
        self.stride_counter = 0

    def update_daily_adv(self, daily_vol: float):
        """每日收盘后触发：更新该股的动态换手率容量时钟阈值"""
        if daily_vol > 0:
            self.rolling_adv.append(daily_vol)
            self.vol_threshold = max(np.mean(self.rolling_adv) * ADV_FRACTION, 1000.0)

    def push_tick(self, tick: dict) -> np.ndarray | None:
        self.current_bar_ticks.append(tick)
        self.cum_vol += tick.get('vol_tick', 0.0)

        if self.cum_vol >= self.vol_threshold:
            spatial_bar = self._collapse_to_spatial_bar()
            self.ring_buffer.append(spatial_bar)
            
            self.cum_vol -= self.vol_threshold
            self.current_bar_ticks = []
            self.stride_counter += 1

            if len(self.ring_buffer) == MACRO_WINDOW and self.stride_counter >= STRIDE:
                self.stride_counter = 0 
                return np.stack(list(self.ring_buffer), axis=0) 
        return None

    def _collapse_to_spatial_bar(self) -> np.ndarray:
        last_tick = self.current_bar_ticks[-1]
        price_close = last_tick.get('price', 0.0)
        srl_residual = last_tick.get('srl_residual', 0.0)
        epiplexity = last_tick.get('epiplexity', 0.0)
        
        spatial_matrix = np.zeros((SPATIAL_DEPTH, FEATURE_DIM), dtype=np.float32)
        
        for i in range(SPATIAL_DEPTH):
            level = i + 1
            spatial_matrix[i, 0] = last_tick.get(f'bid_p{level}', 0.0)
            spatial_matrix[i, 1] = last_tick.get(f'bid_v{level}', 0.0)
            spatial_matrix[i, 2] = last_tick.get(f'ask_p{level}', 0.0)
            spatial_matrix[i, 3] = last_tick.get(f'ask_v{level}', 0.0)
            spatial_matrix[i, 4] = price_close
            spatial_matrix[i, 5] = srl_residual
            spatial_matrix[i, 6] = epiplexity
            
        return spatial_matrix

def topo_forge_pipeline(raw_parquet_dir: str, output_tar_dir: str, symbols: list = None):
    os.makedirs(output_tar_dir, exist_ok=True)
    abs_output_dir = os.path.abspath(output_tar_dir).replace("\\", "/")
    pattern = f"file:///{abs_output_dir}/omega_shard_%05d.tar"
    sink = wds.ShardWriter(pattern, maxcount=SHARD_MAX_COUNT)
    
    global_sample_idx = 0
    
    # Discovery mode: If no symbols provided, scan filenames
    if not symbols:
        logging.info(f"No symbols provided. Scanning {raw_parquet_dir} for parquet files...")
        all_files = []
        for root, dirs, files in os.walk(raw_parquet_dir):
            for f in files:
                if f.endswith('.parquet'):
                    all_files.append(os.path.join(root, f))
        
        # Extract unique symbols from filenames (assuming format: date_hash.parquet or similar)
        # For our specific data, each file contains multiple symbols, so we actually
        # should just iterate through each FILE once and process all symbols within it.
        # Let's pivot to a file-centric iteration for the full-scale run.
        
        all_files.sort()
        for fpath in all_files:
            logging.info(f"[FORGE] Processing File: {os.path.basename(fpath)}...")
            parquet_file = pq.ParquetFile(fpath)
            
            # Use a local cache of state machines for this file
            file_symbol_states = {}
            
            # Since one file has many symbols, we iterate through the whole file in batches
            for batch in parquet_file.iter_batches(batch_size=100000):
                records = batch.to_pylist()
                for tick in records:
                    symbol = tick.get('symbol')
                    if not symbol: continue
                    
                    if symbol not in file_symbol_states:
                        file_symbol_states[symbol] = {
                            'sm': OmegaVolumeClockStateMachine(symbol),
                            'curr_date': None,
                            'daily_vol': 0.0
                        }
                    
                    ctx = file_symbol_states[symbol]
                    sm = ctx['sm']
                    tick_date = tick.get('date')
                    
                    if ctx['curr_date'] is not None and tick_date != ctx['curr_date']:
                        sm.update_daily_adv(ctx['daily_vol'])
                        ctx['daily_vol'] = 0.0
                    
                    ctx['curr_date'] = tick_date
                    ctx['daily_vol'] += tick.get('vol_tick', 0.0)
                    
                    manifold_tensor = sm.push_tick(tick)
                    if manifold_tensor is not None:
                        target_tensor = np.array([0.0], dtype=np.float32)
                        sink.write({
                            "__key__": f"{symbol}_{global_sample_idx:09d}",
                            "manifold_2d.npy": manifold_tensor,
                            "target.npy": target_tensor,
                            "meta.json": {"symbol": symbol, "timestamp": str(tick.get('time'))}
                        })
                        global_sample_idx += 1
                        if global_sample_idx % 1000 == 0:
                            logging.info(f"  -> Forged {global_sample_idx} topological manifolds...")
    else:
        # Targeted symbol mode (Trial Run logic)
        for symbol in symbols:
            logging.info(f"[FORGE] Processing Targeted Symbol: {symbol}...")
            # ... (rest of previous logic) ...
            state_machine = OmegaVolumeClockStateMachine(symbol)
            current_date = None
            daily_cum_vol = 0.0
            
            all_parquet_files = []
            for root, dirs, files in os.walk(raw_parquet_dir):
                for f in files:
                    if f.endswith('.parquet'):
                        all_parquet_files.append(os.path.join(root, f))
            all_parquet_files.sort()

            for fpath in all_parquet_files:
                logging.info(f"  -> Processing file: {os.path.basename(fpath)}")
                try:
                    table = pq.read_table(fpath, filters=[('symbol', '==', symbol)])
                    if table.num_rows == 0: continue
                    records = table.to_pylist()
                    for tick in records:
                        tick_date = tick.get('date')
                        if current_date is not None and tick_date != current_date:
                            state_machine.update_daily_adv(daily_cum_vol)
                            daily_cum_vol = 0.0
                        current_date = tick_date
                        daily_cum_vol += tick.get('vol_tick', 0.0)
                        manifold_tensor = state_machine.push_tick(tick)
                        if manifold_tensor is not None:
                            target_tensor = np.array([0.0], dtype=np.float32)
                            sink.write({
                                "__key__": f"{symbol}_{global_sample_idx:09d}",
                                "manifold_2d.npy": manifold_tensor,
                                "target.npy": target_tensor,
                                "meta.json": {"symbol": symbol, "timestamp": str(tick.get('time'))}
                            })
                            global_sample_idx += 1
                            if global_sample_idx % 1000 == 0:
                                logging.info(f"  -> Forged {global_sample_idx} topological manifolds...")
                except Exception as e:
                    logging.warning(f"Error processing {fpath}: {e}")

    sink.close()
    logging.info(f"[FORGE] Complete. {global_sample_idx} Tensors Generated.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--symbols", type=str, nargs='+', help="Space separated symbol list")
    args = parser.parse_args()
    
    topo_forge_pipeline(args.base_dir, args.output_dir, args.symbols)
