# V3 完整设计审计 — 数学验证 + 工程重构 + 训练/回测策略

**日期**: 2026-03-18
**来源**: 架构师 Google Docs (3 份)
**摄取者**: Claude CLI (Session 4, 从 Google Docs 重新完整摄取)

## 源文档 ID

| 代号 | 标题 | Google Docs ID |
|------|------|----------------|
| id.1 | 数学公式正确性检查 | `1NQDr54Pg5hE9sVo6SW3ZPmtgGwmIy1fpxZ-kFRRTHyY` |
| id.2 | 量化模型工程化重构审计 | `1iQg46aJOojE0v23xoJxjaAu-NyQLIYTm4EjYzDF4muw` |
| id.3 | 修复意见完整文档 | `1UcNeoOIfgHDkVQNYQqhDY9t2DlvzKLcKyeN0WzRuagg` |

可通过 `gdocs read <doc_id>` 重新读取原文。

---

## 一、数学核心验证 (Doc id.1)

### 1.1 SRL 反演算子验证

**公式推导**:
- 前向 SRL: ΔP = sign(Q) × c × σ_D × √(|Q| / V_D)
- 反演: Q_hidden = sign(ΔP) × (|ΔP| / (c × σ_D))² × V_D
- 其中 δ = 0.5 (平方根指数), 逆运算 = 2.0 (平方)

**计算验证**:
- 输入: Q_true = 50000.0, V_D = 1000000.0, σ_D = 0.02, c = 0.842
- 前向传播生成 ΔP_observed ≈ 0.003765
- 反演恢复 Q_recovered = 50000.0546875
- **最大误差: 0.05 (FP32 精度极限下的万分之一相对误差)**
- eps = 1e-8 防止极度缩量时除零 NaN

**结论**: SRL 反演算子数学逻辑 100% 正确。

### 1.2 MDL 损失函数梯度验证

**公式**:
- Total_MDL = H_T + λ_s × S_T
- H_T = MSE(prediction, target) — 不可预测的市场噪音
- S_T = ||z_core||₁ (L1范数均值) — 结构描述长度

**梯度验证** (.backward()):
- z_core 中为 0 的特征: 梯度 ≈ 0 (散户噪音被自动忽略)
- z_core 中非 0 的特征: 梯度 = λ_s × sign(z) (恒定惩罚力度，往0压迫)
- 只有当特征强大到能成倍降低 H_T 时，才能抵抗 L1 "猎杀"存活

**结论**: L1 + MSE 的双部码 MDL 在数学上完美实现了"压缩即智能"。

### 1.3 拓扑撕裂下界修正

**原始表述**: 1D 展平的寻址鸿沟 = Ω(N)
**修正**: 严格来说应为 **Ω(√N)** (Graph Bandwidth Lower Bound)
- 对于 N=10000 的时空矩阵, √N=100 的步长撕裂依然致命
- 结论不变（1D 展平必定空间失忆），但精确表述供论文使用

### 1.4 FWT 算子复杂度验证

- 注意力矩阵大小锁死在 (W_T × W_S) × (W_T × W_S)
- 无论输入 T 多长，局域 TDA 算子复杂度严格 O(W²) = **O(1)**
- 免疫时间轴拉长带来的全局噪音污染

**最终裁决: 数学核心封存，不做任何底层公式改动。**

---

## 二、工程重构指令 (Doc id.2)

### 2.1 用户物理数据边界

1. **原始 4.5TB Level-2 Tick** — 3秒快照, 每日~4800 Ticks/票, 含十档盘口
2. **提纯 2.2TB Base_L1** — 保留高频时间戳 + vol_tick + bs_flag + 十档盘口
3. **目标产出** — WebDataset .tar shards, 形状 [160, 10, 7]

### 2.2 核心工程质询与架构师解答

**Q1: 观测窗口期的甜蜜点搜索**
- 问题：主力建仓周期 1~8 周，如何搜索最佳窗口？
- **解答：ETL 固化最大感受野 (W_T=160) + GPU 动态切片**
  - 不让每次 HPO Trial 触发 CPU 重计算
  - 在 Dataset.__getitem__ 中执行 `tensor[-macro_window:, ...]` 毫秒级切换
  - HPO 搜索空间: `macro_window ∈ qrandint(40, 160, step=20)`

**Q2: 容量时钟取代物理时钟**
- 问题：大盘股建仓慢、小盘股建仓快，固定窗口期拓扑撕裂
- **解答：彻底抹除 Wall-Clock Time，重构为 Volume Clock**
  - Y轴 = 累计换手率区间 (每根 Bar = 消耗 ADV 的 2%)
  - 所有股票输入尺寸绝对归一化为固定 Shape
  - 大盘股 3 天填满一行，微盘股 15 分钟填满一行 → 几何等价
  - 公式: `vol_threshold_i = Rolling_ADV_i (past 20 days) × 0.02`

**Q3: 微观分辨率 (coarse_graining)**
- 问题：4800 Ticks 太细 (噪音), 1 根日线太粗 (丢失细节)
- **解答：ETL 固化安全底线 + 网络端动态池化**
  - 在 OmegaMathematicalCompressor 首层: `F.avg_pool2d(tensor, kernel=(factor, 1))`
  - HPO 搜索: `coarse_graining_factor ∈ [1, 2, 4, 8]`
  - Factor=1 显微镜，Factor=8 望远镜

**Q4: Anti-OOM 铁律**
- **铁律一 (数据坍缩期)**: `pq.ParquetFile.iter_batches()` 流式处理，封杀 df.collect()
- **铁律二 (训练期)**: WebDataset sharded .tar + IterableDataset，RAM 锁死 4-8GB
- **铁律三 (回测期)**: 单向游标状态机 (Forward-only Cursor)，O(1) 内存

### 2.3 为什么是 2D 而不是 ND

**物理根据**:
- 单票 LOB 天然是致密 2D 黎曼流形:
  - X轴 (空间): 盘口价格深度 (Bid10~Ask10, 严格物理相邻)
  - Y轴 (时间): 容量时钟
- price, vol, srl_residual 是附着在 (x,y) 上的特征标量 (如图像 RGB)

**为什么不能升维到 ND**:
1. 违背奥卡姆剃刀: 高维空间 99% 坐标无订单分布
2. 空间受限熵爆炸: 极度稀疏张量浪费 Tensor Core 算力 → OOM
3. 结论: **降维到 1D = 拓扑撕裂, 升维到 ND = 算力自杀, 2D = 最小完备拓扑**

### 2.4 TDA 窗口尺度

- TDA 维度永远锁定 2D (不需要搜索)
- TDA 窗口大小 (W_T × W_S) 是 HPO 核心搜索对象
  - 主力战术动作: 跨越 3 档 × 4 步长? 还是 10 档 × 32 步长?
  - 人类不可能猜透，必须让 Bayesian 优化器在数据中盲测

### 2.5 Epiplexity 压缩算法

**不是传统压缩 (ZIP/LZ77)，而是两把奥卡姆剃刀**:

1. **架构级信息瓶颈**: hidden_dim → hidden_dim/2 → hidden_dim/4
   - 通道骤降 4 倍，迫使网络扔掉冗余，只保留精华

2. **损失函数级 L1 MDL**: S_T = ||z_core||₁
   - L1 范数产生极稀疏解，强烈逼迫神经元熄灭
   - 散户噪音不可压缩 → 强塞进 z_core 会让 S_T 爆表
   - 优化器被迫将噪音扔进 H_T，只在 z_core 点亮极少数神经元
   - 幸存的非零稀疏向量 = 被极致浓缩的主力控盘代码

---

## 三、递归审计 5 项致命缺陷 (Doc id.2 后半段)

### 3.1 致命漏洞一：绝对标尺悖论 (vol_threshold)

- **问题**: 全局固定 50000 手 → 大盘股 3 分钟填满，微盘股 3 天才凑齐
- **修正**: `vol_threshold_i = Rolling_ADV_i × 0.02` (相对容量时钟)
- **状态**: ✅ 已修复 (V3 ETL 实现)

### 3.2 致命漏洞二：空间维度坍缩 ([160, 7] → [160, 10, 7])

- **问题**: V2 聚合 OHLC 丢弃十档盘口 → TDA 无空间可操作
- **修正**: 保留完整 10 档空间深度
- **状态**: ✅ 已修复 (V3 ETL 实现)

### 3.3 工程隐患一：Tumbling Window 流形斩断

- **问题**: 160 行满后清空重新积累 → 主力阵型被腰斩
- **修正**: Ring Buffer + stride=20 平移不变性重叠采样
- **状态**: ✅ 已修复 (V3 ETL 实现)

### 3.4 工程隐患二：MAE 掩码作弊 (Block-wise Causal Masking)

- **问题**: 随机像素掩码 → 模型通过线性插值作弊，不启动 Epiplexity 引擎
- **修正**: 一次挖去连续 10~30 个 Volume 步长，断掉插值退路
- **状态**: ⏳ 未实现 (需要 train.py)

### 3.5 工程隐患三：滑点幽灵 (Slippage Phantom)

- **问题**: 第 160 根 Bar 触发信号 = 大扫盘 Gap Up，假设 Close 买入是致命幻觉
- **修正**: 三大物理摩擦硬编码:
  1. N+1 Bar VWAP 延迟执行
  2. 强制 T+1 隔夜跳空暴露
  3. 容量时钟计时平仓 (80 bars)
- **状态**: ⏳ 未实现 (需要 omega_parallel_crucible.py)

---

## 四、修正后的完整战略路线图 (Doc id.3)

### Phase 1: 创世实验 (DONE)
- vol_threshold = 动态 Rolling_ADV × 2% (冷启动 50000)
- window_size = 160 (ACF 衰减上限)

### Phase 2: 数据坍缩 (PARTIAL)
- 2.2TB → WebDataset .tar shards [160, 10, Features]
- 双节点 (Linux1 + Windows1) 并行 ETL
- Linux1: 76 complete shards, Windows1: 61 complete shards

### Phase 3: 云端盲测 HPO (NOT STARTED)
- Upload shards → GCS
- Google Vizier × 100x L4 GPU
- 搜索: macro_window + coarse_graining_factor
- 成功标准: FVU 在特定时空尺度出现 distinct sharp minimum

### Phase 4: 全量训练 (NOT STARTED)
- 锁定最优超参
- 8x A100 分布式训练
- **Block-wise Causal Masking** (10-30 volume steps)
- 输出: omega_2d_oracle.pth
- 成功标准: Out-of-sample 高保真重构

### Phase 5: 回测熔炉 (NOT STARTED)
- Deploy to Mac Studio
- omega_parallel_crucible.py 事件研究
- 三大物理摩擦: N+1 VWAP + T+1 + 容量时钟退场
- **终极标准: 非对称收益比 > 3.0 (叠加所有物理摩擦后)**

---

## 五、对 current_spec.yaml 的影响

### 已存在 (确认无变更):
- tensor.shape: [B, 160, 10, 7]
- physics.delta: 0.5, physics.c_tse: 0.842
- etl.*: 全部参数

### 新增:
- training.masking_strategy: block_causal
- hpo.*: 完整搜索空间 (engine, gpu, search_space)
- backtest.*: 执行延迟、T+1、退场策略、成功标准
- model_architecture.*: 四层架构描述

### 公理影响评级: **AXIOM UPDATE REQUIRED** (Layer 2 新增参数)
