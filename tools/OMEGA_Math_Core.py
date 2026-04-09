import numpy as np
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage
import warnings
warnings.filterwarnings('ignore')

class OmegaMathCore:
    def __init__(self, d_embed=3, tau_delay=1, hurst_bounds=(0.45, 0.55), time_penalty=1e6, pl_res=20):
        self.d = d_embed            # Takens 降维后嵌入维度
        self.tau = tau_delay        # 延迟步长
        self.h_min, self.h_max = hurst_bounds # 布朗白噪声(纯物理摩擦)判定边界
        self.gamma = time_penalty   # 因果律逆转惩罚项
        self.res = pl_res           # 持久景观(PL)张量网格分辨率
        
    # =========================================================================
    # 🛠️ Patch 1: 核心流形降维 (破除 44维测度坍缩灾难)
    # =========================================================================
    def patch1_manifold_projection(self, df_window):
        """绝对禁止将 44D LOB 数据直接拍扁或展开！提取降维至 3D 核心本征流形"""
        # Expecting df_window to be shape (W, 40)
        # Columns: bid_p1..10 (0:10), bid_v1..10 (10:20), ask_p1..10 (20:30), ask_v1..10 (30:40)
        bid_v = np.sum(df_window[:, 10:20], axis=1)
        ask_v = np.sum(df_window[:, 30:40], axis=1)
        
        # 维度 1: 订单失衡度 (Order Imbalance), 范围 [-1, 1]
        oim = (bid_v - ask_v) / (bid_v + ask_v + 1e-8)
        # 维度 2: 微观气势价 (Micro-Price)
        micro_price = (df_window[:, 0]*ask_v + df_window[:, 20]*bid_v) / (bid_v + ask_v + 1e-8)
        # 维度 3: 盘口深度对数测度
        depth = np.log1p(bid_v + ask_v)
        
        return np.column_stack([micro_price, oim, depth])

    # =========================================================================
    # 🛠️ Patch 2: 局部赫斯特触发器 (破除 SRL 的 Q->0 微观导数奇点)
    # =========================================================================
    def patch2_local_hurst(self, ts):
        """以局部布朗游走概率(Hurst)替代 1/sqrt(Q) 代数残差，彻底规避除零灾难"""
        if len(ts) < 5 or np.std(ts) < 1e-8: return 0.5 # 盘口死水
        
        lags = range(2, min(10, len(ts)//2 + 1))
        if not lags: return 0.5
        
        # 计算时间滞后的均方根位移 tau ~ lag^H
        tau_vals = [np.sqrt(np.mean((ts[lag:] - ts[:-lag])**2)) for lag in lags]
        
        valid_lags, valid_taus = [], []
        for l, t in zip(lags, tau_vals):
            if t > 1e-8:
                valid_lags.append(l)
                valid_taus.append(t)
                
        if len(valid_taus) < 2: return 0.5
        m = np.polyfit(np.log(valid_lags), np.log(valid_taus), 1)
        return np.clip(m[0], 0.0, 1.0) # 返回局部 H 指数

    # =========================================================================
    # 🛠️ Patch 3 & 4: 有向拓扑复合体与 PL 稠密张量注入
    # =========================================================================
    def patch3_4_directed_tensor(self, point_cloud):
        N = len(point_cloud)
        if N < 2: return np.zeros((3, self.res))
        
        # 原始对称欧氏测度
        std_dev = point_cloud.std(axis=0) + 1e-8
        normalized_pc = (point_cloud - point_cloud.mean(axis=0)) / std_dev
        D_sym = squareform(pdist(normalized_pc))
        
        # 🛠️ Patch 3 核心：焊死时间之箭！逆转时间 (i >= j) 施加无限大物理壁垒
        D_causal = np.full((N, N), self.gamma) 
        for i in range(N):
            for j in range(i+1, N):
                D_causal[i, j] = D_sym[i, j]
                
        # 提取有向连通分支的死亡时间 (模拟 Betti-0 的单向聚类)
        condensed_D = [D_causal[i, j] for i in range(N) for j in range(i+1, N)]
        if not condensed_D: return np.zeros((3, self.res))
        
        Z = linkage(condensed_D, method='single')
        deaths = Z[:, 2]
        deaths = deaths[deaths < self.gamma / 2] # 过滤掉所有时间倒转的非法拓扑边
        
        # 🛠️ Patch 4 核心：映射至 Banach 空间，提取 (3 x Res) 稠密张量，拒绝标量坍缩
        t_max = np.max(deaths) if len(deaths) > 0 else 1.0
        if t_max <= 0: t_max = 1.0
        
        t_grid = np.linspace(0, t_max, self.res)
        pl_tensor = np.zeros((3, self.res))
        
        for i, t in enumerate(t_grid):
            envs = np.maximum(0, np.minimum(t, deaths - t)) # 景观函数投影方程
            env_sorted = np.sort(envs)[::-1]
            for k in range(min(3, len(env_sorted))):
                pl_tensor[k, i] = env_sorted[k]
                
        return pl_tensor

    def forward_sandbox(self, df_window):
        manifold_state = self.patch1_manifold_projection(df_window)
        hurst = self.patch2_local_hurst(manifold_state[:, 0]) # 监控 Micro-Price
        
        if self.h_min <= hurst <= self.h_max:
            # 物理奇点拦截生效：纯随机游走，无 Epiplexity，节省 100% 算力
            return "INTERCEPTED", hurst, np.zeros((3, self.res))
            
        # 唤醒 TDA 引擎 (因果张量计算)
        tensor = self.patch3_4_directed_tensor(manifold_state)
        return "TRIGGERED", hurst, tensor
