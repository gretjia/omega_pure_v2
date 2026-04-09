import numpy as np
import polars as pl
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import linkage
from numpy.lib.stride_tricks import sliding_window_view
import os
import glob
import time
import warnings
import pyarrow.parquet as pq
import pyarrow as pa
import pyarrow.compute as pc

warnings.filterwarnings('ignore')

class OmegaMathCore:
    def __init__(self, pl_res=20, hurst_bounds=(0.45, 0.55), gamma=5.0):
        self.res = pl_res
        self.h_min, self.h_max = hurst_bounds
        self.gamma = gamma 
        
    def patch2_local_hurst(self, ts):
        if len(ts) < 5 or np.std(ts) < 1e-8: return 0.5 
        lags = range(2, min(10, len(ts)//2 + 1))
        if not lags: return 0.5
        tau_vals = [np.sqrt(np.mean((ts[lag:] - ts[:-lag])**2)) for lag in lags]
        valid_lags, valid_taus = [], []
        for l, t in zip(lags, tau_vals):
            if t > 1e-8:
                valid_lags.append(l)
                valid_taus.append(t)
        if len(valid_taus) < 2: return 0.5
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            m = np.polyfit(np.log(valid_lags), np.log(valid_taus), 1)
        return float(np.clip(m[0], 0.0, 1.0))

    def patch3_4_directed_tensor(self, point_cloud):
        N = len(point_cloud)
        if N < 2: return np.zeros((3, self.res))
        
        v = np.diff(point_cloud, axis=0)
        v_pos = np.maximum(0, v)
        v_neg = np.maximum(0, -v)
        
        augmented_pc = np.hstack([
            point_cloud[:-1], 
            v_pos * self.gamma, 
            v_neg * (self.gamma * 0.02) 
        ])
        
        std_dev = augmented_pc.std(axis=0) + 1e-8
        normalized_pc = (augmented_pc - augmented_pc.mean(axis=0)) / std_dev
        
        condensed_D = pdist(normalized_pc)
        if len(condensed_D) == 0: return np.zeros((3, self.res))
        
        Z = linkage(condensed_D, method='single')
        deaths = Z[:, 2]
        
        t_max = np.max(deaths) if len(deaths) > 0 else 1.0
        if t_max <= 0: t_max = 1.0
        
        t_grid = np.linspace(0, t_max, self.res)
        pl_tensor = np.zeros((3, self.res))
        
        for i, t in enumerate(t_grid):
            envs = np.maximum(0, np.minimum(t, deaths - t)) 
            env_sorted = np.sort(envs)[::-1]
            for k in range(min(3, len(env_sorted))):
                pl_tensor[k, i] = env_sorted[k]
                
        return pl_tensor

    def process_window(self, window_data):
        hurst = self.patch2_local_hurst(window_data[:, 0]) 
        if self.h_min <= hurst <= self.h_max:
            return False, np.zeros((3, self.res))
        tensor = self.patch3_4_directed_tensor(window_data)
        return True, tensor


def extract_daily_tda_from_df(df_group):
    try:
        keys, df = df_group
        symbol = str(keys[0])
        date = str(keys[1])
        window_size = 50
        step = 50
        
        if len(df) < window_size: return None
            
        bid_v_cols = [pl.col(f"bid_v{i}") for i in range(1, 11)]
        ask_v_cols = [pl.col(f"ask_v{i}") for i in range(1, 11)]
        
        df = df.with_columns([
            pl.sum_horizontal(bid_v_cols).alias("sum_bid_v"),
            pl.sum_horizontal(ask_v_cols).alias("sum_ask_v")
        ])
        
        df = df.with_columns([
            ((pl.col("sum_bid_v") - pl.col("sum_ask_v")) / (pl.col("sum_bid_v") + pl.col("sum_ask_v") + 1e-8)).alias("m_oim"),
            ((pl.col("bid_p1") * pl.col("sum_ask_v") + pl.col("ask_p1") * pl.col("sum_bid_v")) / (pl.col("sum_bid_v") + pl.col("sum_ask_v") + 1e-8)).alias("m_price"),
            (pl.col("sum_bid_v") + pl.col("sum_ask_v") + 1.0).log().alias("m_depth")
        ])
        
        manifold_data = df.select(["m_price", "m_oim", "m_depth"]).fill_null(0.0).to_numpy()
        prices_arr = df.select("price").to_numpy()
        close_price = prices_arr[-1][0]
        open_price = prices_arr[0][0] # 提取开盘价，用于 T+1 滑点计算
        
        windows = sliding_window_view(manifold_data, window_shape=window_size, axis=0)
        windows = np.swapaxes(windows, 1, 2)
        
        core = OmegaMathCore()
        tensors = []
        triggered_count = 0
        
        for i in range(0, len(windows), step):
            triggered, tensor = core.process_window(windows[i])
            if triggered:
                tensors.append(tensor)
                triggered_count += 1
                
        if not tensors:
            daily_tensor = np.zeros(3 * core.res)
        else:
            # 🚨 审计官强干预指令二：将 np.mean 替换为 np.max，防止幽灵巨手被日频均值暴力抹杀 (Feature Dilution)
            daily_tensor = np.max(tensors, axis=0).flatten() 
            
        return {
            "symbol": symbol,
            "date": date,
            "open_price": float(open_price),
            "close_price": float(close_price),
            "triggered_windows": triggered_count,
            "tda_features": daily_tensor.tolist()
        }
    except Exception as e:
        return f"ERROR extracting {keys[0]} on {keys[1]}: {e}"


def compute_y_labels(df):
    print("Computing Y-labels with Chief System Auditor Patches (Max-Pooling, T+1 Slippage, Log-Modulus Transform)...")
    df = df.sort(["symbol", "date"])
    HORIZON = 20 # 波段操作：20天视窗
    
    symbols = df["symbol"].to_list()
    dates = df["date"].to_list()
    close_prices = df["close_price"].to_numpy()
    open_prices = df["open_price"].to_numpy()
    
    N = len(close_prices)
    y_breakout = np.full(N, np.nan)
    y_sharpe = np.full(N, np.nan)
    y_phase = np.full(N, np.nan)
    
    for i in range(N):
        if i + HORIZON < N and symbols[i] == symbols[i+HORIZON]:
            future_close = close_prices[i+1 : i+HORIZON+1]
            
            # 🚨 审计官强干预指令三：T+1 开盘滑点的“时空穿越幻觉”。必须使用 T+1 日开盘价买入，并附加双边 3‰ 的严苛摩擦惩罚
            entry_price = open_prices[i+1] * 1.003 # 模拟买入冲击与手续费
            
            if entry_price <= 0: continue
            
            # 1. Breakout
            max_p = np.max(future_close)
            y_breakout[i] = 1.0 if (max_p / entry_price - 1) > 0.15 else 0.0
            
            # 2. Sharpe Swing
            # 卖出时扣除 3‰ 滑点摩擦
            exit_price = future_close[-1] * 0.997 
            ret = exit_price / entry_price - 1
            
            # 极值计算最大回撤
            future_drawdowns = (future_close * 0.997) / np.maximum.accumulate(np.insert(future_close, 0, entry_price))[1:] - 1
            max_dd = abs(np.min(future_drawdowns))
            
            raw_sharpe = ret / (max_dd + 1e-4)
            # 🚨 审计官强干预指令一：回归目标的“梯度核爆弹”。必须使用 Log-Modulus Transform！
            y_sharpe[i] = np.sign(raw_sharpe) * np.log1p(np.abs(raw_sharpe))
            
            # 3. Phase Transition (站上 20日线)
            if i >= 19 and symbols[i] == symbols[i-19]:
                ma20 = np.mean(close_prices[i-19:i+1])
                y_phase[i] = 1.0 if np.all(future_close[:5] > ma20) else 0.0
                
    df = df.with_columns([
        pl.Series("y_breakout_20d", y_breakout, dtype=pl.Float32),
        pl.Series("y_log_sharpe_20d", y_sharpe, dtype=pl.Float32),
        pl.Series("y_phase_20d", y_phase, dtype=pl.Float32)
    ])
    return df


def extract_raw_and_run(symbol):
    print(f"🔥 加载原始数据集提取 {symbol} (2025.07.15 - 2025.10.15)...")
    start_t = time.time()
    
    base_dir = "/omega_pool/parquet_data/latest_base_l1_sorted"
    if not os.path.exists(base_dir):
        base_dir = "/omega_pool/parquet_data/latest_base_l1"
        
    all_files = glob.glob(os.path.join(base_dir, "**", "*.parquet"), recursive=True)
    
    # Filter dates 20250715 to 20251015
    target_files = []
    for f in all_files:
        basename = os.path.basename(f)
        date_str = basename[:8]
        if date_str.isdigit():
            if "20250715" <= date_str <= "20251015":
                target_files.append(f)
                
    target_files.sort(key=lambda x: os.path.basename(x)[:8])
    
    if not target_files:
        print("未找到指定日期范围的原始数据文件！")
        return

    print(f"找到 {len(target_files)} 个交易日文件。开始使用 Polars LazyFrame 并行扫描过滤...")
    
    pf = pq.ParquetFile(target_files[0])
    all_cols = pf.schema.names
    lob_cols = []
    for lvl in range(1, 11):
        lob_cols.extend([f'bid_p{lvl}', f'bid_v{lvl}', f'ask_p{lvl}', f'ask_v{lvl}'])
    core_cols = ['symbol', 'date', 'price', 'vol_tick']
    if 'time' in all_cols: core_cols.append('time')
    if 'timestamp' in all_cols: core_cols.append('timestamp')
    columns_to_keep = [c for c in core_cols + lob_cols if c in all_cols]

    # Use polars lazy evaluation to scan all parquet files and push down the symbol filter
    try:
        lf = pl.scan_parquet(target_files)
        df_all = lf.filter(pl.col("symbol") == symbol).select(columns_to_keep).collect()
    except Exception as e:
        print(f"Polars 扫描失败: {e}")
        return
        
    if len(df_all) == 0:
        print(f"在指定日期范围内未能提取到 {symbol} 的数据。可能是停牌或不在底层池中。")
        return
        
    groups = list(df_all.group_by(["symbol", "date"]))
    print(f"数据加载完成，共提取到 {len(df_all)} 行 Tick，切分为 {len(groups)} 个 [Stock-Day] 任务块。耗时: {time.time() - start_t:.2f}s")
    
    print(f"🚀 OMEGA TDA 引擎启动 | 单核顺序执行")
    start_extract_t = time.time()
    results, errors = [], []
    
    for i, group in enumerate(groups):
        res = extract_daily_tda_from_df(group)
        if isinstance(res, dict): results.append(res)
        elif isinstance(res, str): errors.append(res)
            
        print(f"进度: {i + 1} / {len(groups)} | 耗时: {time.time() - start_extract_t:.1f}s")
    
    if results:
        schema = {"symbol": pl.Utf8, "date": pl.Utf8, "open_price": pl.Float32, "close_price": pl.Float32, "triggered_windows": pl.Int32}
        for i in range(len(results[0]["tda_features"])):
            schema[f"tda_f_{i}"] = pl.Float32
            
        flat_results = []
        for r in results:
            row = {"symbol": r["symbol"], "date": r["date"], "open_price": r["open_price"], "close_price": r["close_price"], "triggered_windows": r["triggered_windows"]}
            for i, val in enumerate(r["tda_features"]):
                row[f"tda_f_{i}"] = float(val)
            flat_results.append(row)
            
        out_df = pl.DataFrame(flat_results, schema=schema)
        out_df = compute_y_labels(out_df)
        
        print(f"\n📊 {symbol} 样本数据 (审计后的 Y 标签对比 - MaxPool + LogModulus + T+1 Slippage):")
        sample = out_df.filter(pl.col('y_log_sharpe_20d').is_not_null()).head(15)
        if len(sample) > 0:
            print(sample.select(["symbol", "date", "open_price", "close_price", "y_breakout_20d", "y_log_sharpe_20d", "y_phase_20d"]))
        else:
            print("Not enough days to calculate 20-day future returns.")

if __name__ == "__main__":
    extract_raw_and_run("300476.SZ")
