> **⚠️ SUPERSEDED** — 本文件已被 [2026-04-06_codex_audit_workpapers.md](2026-04-06_codex_audit_workpapers.md) 取代。仅供历史参考。

# Omega-TIB Comprehensive Audit Data Pack
**Purpose**: 为外部审计（Codex + Gemini + 领域专家）准备的原始数据包
**Date**: 2026-04-06
**Compiler**: Claude (5-Agent parallel research)
**Scope**: 模型架构是否足够好？训练科学是否最优？

---

## §1. 架构师指导原文（Directive 溯源）

### 1.1 时间线

| 日期 | 文件 | 关键决策 | INS 编号 |
|------|------|----------|----------|
| 2026-03-16 | `f7ccde9` (初始提交) | 从前代项目 SpatioTemporal2DMAE 继承数学核心 | — |
| 2026-03-18 | `architect/directives/2026-03-18_v3_full_design_audit.md` | 4 层架构定稿、SRL 公式验证、MDL 损失定义、空间轴不可拍扁 | INS-001~008 |
| 2026-03-18 | `architect/directives/2026-03-18_v3_spatial_restoration.md` | 恢复 [160,10,F] 形状，拒绝 [160,7] 一维化 | INS-006, INS-007 |
| 2026-03-24 | `architect/directives/2026-03-24_v15_launch_authorization.md` | hidden_dim=128, LR scheduler, Huber warmup | — |
| 2026-03-25 | `architect/directives/2026-03-25_phase4_hpo_authorization.md` | HPO 搜索空间: hd, wt, lambda_s, lr | INS-009~013 |
| 2026-03-25 | `architect/directives/2026-03-25_phase4_ashare_swing_tracker.md` | 锁定 ws=10, 搜索 coarse_graining, 移除 hd=384 | — |
| **2026-03-29** | **`architect/directives/2026-03-29_compression_is_intelligence_phase7_golive.md`** | **hd=64 物理瓶颈胜出**, wt=32×ws=10 确认, Phase 7 部署授权 | **INS-019, INS-020** |
| 2026-04-04 | Phase 13 Mandate A+B | IC Loss 替代 MSE, AttentionPooling 替代 Mean Pooling, Pre-LN Residual | INS-066~069 |

### 1.2 核心决策原文摘录

**hd=64 的决策依据**（2026-03-29 directive, lines 27-34）:
> "hd=64（仅 1.9 万参数的超小模型 T29/T55）居然极其华丽地击败了 hd=128 和 hd=256（高达 30 万参数的大模型）！"
> Phase 6 证据链:
> - hd=64 (T29, 19.7K params): IC=+0.0661, monotonicity 8/9
> - hd=128 (T36, 77K params): IC=+0.0667, monotonicity 7/9
> - hd=256 (305K params): 未进入 Top-3

**⚠️ 审计注意**: INS-072 已正式宣布 Phase 6 所有基线数据作废（torch.compile bug C-062 + 全局排序污染）。Phase 14 Step 1 复测: Phase 6 T29 RankIC=0.0023, pred_std=790 BP → **信号死亡**。hd=64 的唯一实证依据已被推翻。

**单层注意力的决策依据**（2026-03-18 directive, lines 119-123）:
> "TDA 维度永远锁定 2D (不需要搜索)"
> "TDA 窗口大小 (W_T × W_S) 是 HPO 核心搜索对象"

**⚠️ 审计注意**: "不需要搜索"指的是 2D vs 1D 维度，但被执行为"层数也不需要搜索"。原始指令**从未讨论过层数**。

**window_size=(32,10) 的决策依据**（2026-03-25 directive + 2026-03-29 directive）:
> wt 搜索空间: [8, 16, 32, 64]，HPO 选出 wt=32
> ws 搜索空间: [5, 10]，architect 直接锁定 ws=10（全盘口深度）
> "wt=32 配合 10 档 LOB 深度，把这些散落的冰山单，在 2D 时空张量中描绘出一个'建仓/洗盘/拉升'的连续几何形状"

**bottleneck 64→32→16 的决策依据**（2026-03-18 directive, lines 129-136）:
> "架构级信息瓶颈: hidden_dim → hidden_dim/2 → hidden_dim/4，通道骤降 4 倍，迫使网络扔掉冗余，只保留精华"
> "L1 范数产生极稀疏解，强烈逼迫神经元熄灭。散户噪音不可压缩 → 强塞进 z_core 会让 S_T 爆表"

**⚠️ 审计注意**: lambda_s=0 已永久锁定（6 Phase 实证）。L1 惩罚不参与训练，bottleneck 的 L1 稀疏化理论依据已失效。

### 1.3 从未被讨论的议题

以下关键架构问题**在整个 directive 历史中从未出现过**:
1. **模型深度**（层数）— 从未搜索过，从未讨论过
2. **简单 baseline 对比**（MLP / 无 SRL / 无拓扑）— 从未执行过
3. **注意力层数 > 1** — 从未提议过
4. **跨窗口通信机制**（Swin-style shifted window / global token）— 从未提议过
5. **Dropout** — 从未讨论过
6. **EMA / 模型平均** — 从未讨论过
7. **梯度累积 / 有效 batch size 对 IC Loss 的影响** — 从未讨论过

---

## §2. 真实执行的算法 Source Code

### 2.1 代码演化时间线

| 提交 | 日期 | 变更 |
|------|------|------|
| `f7ccde9` | 2026-03-16 | **GENESIS**: SRL(c=0.842固定), FWT(window=(4,4), 无RPB), 瓶颈(hd→hd/2→hd/4), 全局均值池化, MDL(λ_s=1e-3) |
| `8105a08` | 2026-03-16 (+17min) | 修复: 添加相对位置偏置表(RPB, Swin-style) |
| `28ee9dc` | 2026-03-19 | **Phase 0.5**: c→per-stock c_friction, 10通道张量, 重命名为 Omega-TIB |
| `b77e646` | 2026-03-22 | train.py 创建: VolumeBlockInputMasking, 时序验证分割, AMP |
| `481870b` | 2026-04-04 | **Phase 13 B**: AttentionPooling + Pre-LN Residual |
| `df2db3a` | 2026-04-04 | **Phase 13 A**: IC Loss 替代 MSE |

### 2.2 当前模型架构（精确代码）

```
omega_epiplexity_plus_core.py → OmegaMathematicalCompressor
 ├── Layer 1: AxiomaticSRLInverter (非可学习, torch.no_grad + fp32)
 │   Q_hidden = sign(ΔP) × (|ΔP| / (c_i × σ_D))^2 × V_D
 │   δ=0.5 永恒常数，c_i 从 a_share_c_registry.json 读取
 │
 ├── 特征组装: LOB(ch0-4) + q_metaorder → [B,T,S,6]
 │   train.py 中额外 FRT 变换: bid/ask→BP偏差, close→累计对数收益, vol→log1p
 │
 ├── input_proj: Linear(6→64) + LayerNorm(64) → post_proj_norm
 │
 ├── VolumeBlockInputMasking (训练时, mask_prob 默认=0.0 即禁用)
 │
 ├── Layer 2: FiniteWindowTopologicalAttention (hd=64, 4头, window=(32,10))
 │   Pre-LN Residual: out = x + tda(LayerNorm(x))
 │   5个不重叠窗口(160/32=5), 窗口间零通信
 │   RPB 表: (63×19) × 4头 = 4788 参数
 │
 ├── Layer 3: EpiplexityBottleneck
 │   Linear(64→32) → GELU → Linear(32→16)
 │   lambda_s=0, L1 不参与训练
 │
 ├── AttentionPooling(dim=16)
 │   pool = Σ softmax(z @ W_pool / √16) × z, over T*S tokens
 │
 └── IntentDecoder: Linear(16→1) → scalar prediction
```

### 2.3 参数计数

| 组件 | 参数量 |
|------|--------|
| input_proj (6→64, bias) | 448 |
| tda_layer.qkv (64→192, no bias) | 12,288 |
| tda_layer.proj (64→64, bias) | 4,160 |
| tda_layer.RPB 表 | 4,788 |
| tda_pre_ln (LayerNorm) | 128 |
| bottleneck (64→32→16) | 2,608 |
| attention_pool.W_pool | 16 |
| intent_decoder (16→1) | 17 |
| post_proj_norm (LayerNorm) | 128 |
| **总计** | **~24,581** |

### 2.4 训练配置（Phase 13 实际执行）

```
Loss: IC Loss (Pearson correlation, lambda_s=0)
Optimizer: AdamW(lr=3e-4, weight_decay=1e-5, betas=(0.9, 0.999))
Scheduler: OneCycleLR(pct_start=0.05, anneal_strategy='cos', div_factor=100)
Batch size: 256 (无梯度累积)
Epochs: 15, steps/epoch: 5000
AMP: 禁用 (--no_amp)
Grad clip: 1.0
VolumeBlockInputMasking: mask_prob=0.0 (禁用)
Dropout: 无 (模型中完全不存在)
```

---

## §3. 数据来源 Snapshot

### 3.1 原始数据

- **来源**: A 股 L1 tick 数据（逐笔交易 + 10 档 LOB 快照）
- **格式**: Apache Parquet, 按日期排序
- **总量**: ~2.2TB raw → Volume-Clocked tensors
- **覆盖**: 沪深 A 股（000/001/002/003/300/301/600/601/603/605/688/689 前缀）
- **时间范围**: 20230103-20260130 (约 551 个交易日)
- **每日列**: symbol, date, price, vol_tick + 40 列 LOB (bid_p/v × 10档 + ask_p/v × 10档) = 44 列

### 3.2 ETL 管线参数

| 参数 | 值 | 含义 |
|------|-----|------|
| MACRO_WINDOW | 160 bars | ACF 衰减极限 (~3 天仓位周期) |
| STRIDE | 20 bars | 滑窗步长 (翻译不变性) |
| ADV_FRACTION | 0.02 (1/50) | 动态阈值 = 20日ADV × 2% |
| PAYOFF_HORIZON | 20 bars | T+1 隔夜回报视野 (~0.4 天) |
| SPATIAL_DEPTH | 10 | LOB 全深度 |
| FEATURE_DIM | 10 | 7 基础 + ΔP + V_D + σ_D |
| SHARD_MAX_COUNT | 5,000 | ~1GB/shard |
| vol_threshold | max(ADV×0.02, 1000) | 每股每日动态 |

### 3.3 目标变量

```
entry_vwap = VWAP of bar N+1  (信号延迟: bar N 发出信号, N+1 才能执行)
exit_vwap  = VWAP of bar N+1+20
target_bp  = (exit_vwap - entry_vwap) / entry_vwap × 10000  (基点)
```

### 3.4 数据集统计

- **训练集**: 1593 shards (~80%), ~7.6M samples
- **验证集**: 399 shards (~20%), ~1.9M samples (1,904,747 精确)
- **Target 分布**: Mean=6.93 BP, Std=189.60 BP, Skew=11.78, **Kurtosis=2006**, Range=[-9035, +42671] BP
- **Data SNR**: 6.93/189.60 = 3.655%

### 3.5 SRL 摩擦系数标定

- **c_default**: 0.842 (TSE 回退值)
- **c_i 范围**: [0.3, 1.5+]，按个股流动性实证标定
- **方法**: OLS 无截距回归 Y = c_i × X, 其中 X=√(Q/V_D), Y=ΔP/σ_D
- **来源文件**: `a_share_c_registry.json`

---

## §4. Omega-TIB 结果细节（全 Phase 汇总）

### 4.1 核心指标演进

| Phase | Loss | hd | Window | 参数 | Rank IC | D9-D0 (BP) | pred_std (BP) | 判定 |
|-------|------|-----|--------|------|---------|-----------|-------------|------|
| 3 | Huber+MDL | 128 | (4,4) | ~50K | N/A | N/A | N/A | FVU≈1.0, MDL 杀信号 |
| 5 | IC | ~20K | (4,4) | ~20K | N/A | -1.67 | — | 方向错误 |
| 6 | IC (HPO) | 64 | (32,10)* | 19.7K | +0.0023† | +11.16† | 790† | †复测值, 信号死亡 |
| 9 | Asym Pearson | 64 | (32,10) | ~20K | N/A | — | 50+ | 7 job 全失败 |
| 10 | Softmax PF | 64 | (32,?) | 21.4K | N/A | +18.42 | 5055 | Beta 走私 |
| 11c | Huber(50) | 64 | (32,4) | 21.4K | +0.016‡ | +8.90‡ | 5.64 | ‡5shard, 脑死亡 |
| 11d | Huber(200) | 64 | (32,4) | 21.4K | **-0.026** | +2.91 | 17.33 | 噪声非信号 |
| 12 | Unbounded MSE | 64 | (32,10) | 24.4K | **-0.021** | +4.51 | 26.61 | 29σ 反转 |
| **13** | **IC Loss** | **64** | **(32,10)** | **24.6K** | **+0.029** | **+7.00** | varied | **✓ 唯一 PASS** |

### 4.2 Phase 13 详细截面（1,904,748 样本）

| 十分位 | 样本数 | mean_pred (BP) | mean_target (BP) | hit_rate | payoff_ratio |
|--------|--------|---------------|-----------------|----------|-------------|
| D0 (最低) | 190,475 | 19,513 | 1.85 | 46.9% | 1.151 |
| D1 | 190,475 | 28,982 | 6.31 | 48.3% | 1.150 |
| D2 | 190,474 | 31,797 | 7.11 | 48.8% | 1.160 |
| D3 | 190,475 | 33,215 | 6.22 | 49.5% | 1.132 |
| D4 | 190,475 | 34,156 | 7.14 | 50.0% | 1.142 |
| D5 | 190,475 | 34,930 | 7.05 | 50.4% | 1.132 |
| D6 | 190,474 | 35,664 | 7.89 | 50.6% | 1.147 |
| D7 | 190,475 | 36,452 | 8.49 | 50.8% | 1.155 |
| D8 | 190,474 | 37,445 | 8.38 | 50.7% | 1.160 |
| D9 (最高) | 190,476 | 39,579 | **8.85** | **50.4%** | **1.190** |

- **Spearman Rank IC**: +0.0292 (p=0.0)
- **D9-D0**: +7.00 BP
- **D9 hit_rate (50.4%) > D0 hit_rate (46.9%)**: 模型选到了赢家，非仅波动率
- **单调性**: 6/9

### 4.3 Phase 7 回测（Phase 6 T29 checkpoint, 551 交易日）

- 年化收益: +4.58% (board_cap 后 +6.31%)
- Sharpe: 0.49 (0.66 with cap)
- Max Drawdown: -26.50%
- **不对称比: 1.20** (目标 >3.0, 未达标)
- Daily CS-IC: 0.028, ICIR: 0.38
- **理论极限**: IC=0.028 时不对称比 3.0 数学上不可达，需 IC>0.10

---

## §5. 后续训练数据的支持性证据

### 5.1 已证实的事实

| 证据 | 来源 | 对审计的意义 |
|------|------|------------|
| lambda_s>0 杀信号 | Phase 3/11c/11d/12 vs Phase 13 (lambda_s=0) | L1 稀疏化在此数据上有害，MDL 理论依据需重新审视 |
| IC Loss > MSE/Huber/Softmax | Phase 5-12 全部失败, Phase 13 成功 | 排名 > 回归 对低 SNR 数据更稳健 |
| window=(32,10) > (4,4) | Phase 6 HPO + C-057 教训 | 全盘口深度 + 足够时间跨度是必要的 |
| AttentionPooling > Mean Pooling | Phase 13 vs Phase 12 | 结构信息保留关键 |
| Pre-LN Residual 必要 | Phase 13 引入后首次成功 | 梯度流改善是成功因素之一 |
| Phase 6 IC=0.066 不可信 | C-062 (torch.compile bug) + Phase 14 复测 | 历史所有"hd=64 最优"的唯一实证基础已被推翻 |
| "2.4% SNR" 是伪常数 | C-077, 实际数据 SNR=3.655% | 基于此的架构限制需重新评估 |
| Kurtosis=2006 极端肥尾 | Phase 14 Step 0 | 标准统计方法可能失效，需尾部专用处理 |

### 5.2 可以收集但尚未收集的数据

| 实验 | 目的 | 预估成本 | 优先级 |
|------|------|---------|--------|
| MLP baseline (同数据，无 SRL/拓扑) | 量化物理层+拓扑层的边际贡献 | 1-2h T4 | **P0** |
| 去 SRL baseline (原始特征直喂注意力) | SRL 反演是帮助还是瓶颈 | 1-2h T4 | **P0** |
| 2-3 层注意力 (hd=64) | 深度是否是瓶颈 | 2-4h T4 | **P0** |
| hd=128/256 在 Phase 13 管线上 | Phase 13 修复后容量是否仍是瓶颈 | 2-4h T4 | **P0** |
| Swin-style shifted window (2层) | 跨窗口通信是否释放信号 | 2-4h T4 | **P1** |
| 梯度累积 (effective batch=1024/2048) | 大截面 IC 估计是否更稳定 | 1-2h T4 | **P1** |
| 尾部加权 IC Loss | Loss 与 Taleb 哲学对齐 | 1-2h T4 | **P1** |
| EMA / SWA 模型平均 | 免费精度提升 | 1h T4 | **P2** |
| Dropout 0.05-0.1 + weight_decay 0.01 | 正则化影响 | 1h T4 | **P2** |
| AdamW beta2=0.95 | 优化器对噪声金融数据的适应性 | 1h T4 | **P2** |

---

## §6. 训练科学专家视角的补充

### 6.1 致命发现: 跨窗口零通信

当前架构将 [B, 160, 10, D] 切为 5 个 [32, 10] 窗口。**窗口之间完全没有信息流动。** 每个窗口是独立的特征提取器，直到 AttentionPooling 才合并——但那时已经过了 64→32→16 的瓶颈压缩。

这意味着：如果机构主力的建仓行为跨越 40-50 个 bar（跨越一个 32-bar 窗口边界），**模型物理上不可能将其识别为一个连续模式**。

**类比**: 这像是让 5 个独立的人各看一段 32 秒的监控录像片段，然后投票判断"这是否是一次抢劫"——但没有人能同时看到连续的两段。

### 6.2 IC Loss 与 Taleb 哲学的脱节

项目核心哲学：
> "尾部事件是信号 | 不对称比 > 3.0 | 小额试错 + 尾部暴利"

但 IC Loss = Pearson 相关系数，**对每个样本等权处理**。一个 +500BP 的尾部暴利事件和一个 +2BP 的无聊事件对 IC 的贡献几乎一样。Loss 函数没有在尾部事件上给予更大的梯度权重。

Kurtosis=2006 意味着极端事件频繁发生。这些极端事件正是 Taleb 哲学认为的"全部 alpha 所在"——但 IC Loss 在优化过程中并不特别关注它们。

### 6.3 有效 Batch Size 对 IC Loss 的影响

IC Loss 计算一个 batch 内的 Pearson 相关。B=256 时：
- 相关系数的采样标准误差 ≈ 1/√256 = 6.25%
- 而信号本身的 Rank IC = 2.9%
- **信噪比 < 1**: 梯度信号被采样噪声淹没

这是一个被忽视的基本统计问题。增加 effective batch size 到 1024-2048（通过梯度累积）可能是成本最低、收益最高的改进。

### 6.4 Early Stopping 缺失

当前代码只检查"模型是否足够好"（threshold-based），不检查"模型是否在变差"（patience-based）。Phase 13 最佳在 E9，但训练跑到 E15。如果 E10-E15 在过拟合，当前代码检测不到。

### 6.5 正则化几乎为零

| 正则化手段 | 状态 |
|-----------|------|
| Weight decay | 1e-5 (≈0) |
| Dropout | 不存在 |
| VolumeBlockInputMasking | mask_prob=0.0 (禁用) |
| L1 (lambda_s) | 0 (永久禁用) |
| 数据增强 | 无 |

对一个 25K 参数的小模型，过拟合风险可能不高。但**欠正则化也意味着模型没有被迫学习鲁棒特征**。轻量正则化（dropout=0.05, weight_decay=0.01）几乎是免费的。

### 6.6 模型平均: 被忽视的免费午餐

- **SWA** (Stochastic Weight Averaging): 平均最后 3-5 个 epoch 的权重。实现成本 ~10 行代码。通常 0.5-1% IC 提升。
- **EMA** (Exponential Moving Average): 训练时维护一份指数移动平均权重。标准 transformer 训练标配。

在低 SNR 环境下，模型平均对稳定性的提升尤其显著。

### 6.7 优化器设置过于保守

| 参数 | 当前值 | 推荐值 | 理由 |
|------|--------|--------|------|
| beta2 | 0.999 (默认) | 0.95 | 金融数据梯度方差大，0.999 适应太慢 |
| weight_decay | 1e-5 | 0.01-0.1 | AdamW 解耦 WD 与 LR，高 WD 安全且有效 |
| eps | 1e-8 (默认) | 1e-6 | IC Loss 梯度小，eps 需匹配 |

### 6.8 验证策略的潜在泄漏

- 训练/验证按 shard 字母排序分割（前 80% / 后 20%）
- 但 stride=20 + window=160 意味着相邻窗口有 140 bar 重叠
- **边界处的 train/val shards 可能共享时间上下文**
- 需要在边界处加入 embargo gap（丢弃 1-2 个 shard）

---

## §7. 审计建议矩阵

### 7.1 按优先级排序的核心质疑

| # | 质疑 | 当前状态 | 验证方法 | 预估成本 |
|---|------|---------|---------|---------|
| Q1 | 模型容量是否足够？(hd=64 唯一依据已被推翻) | hd=64 locked, Phase 6 证据无效 | Phase 13 管线上跑 hd=128/256 对比 | 2-4h T4 |
| Q2 | 单层注意力是否足够？ | 从未测试过 >1 层 | 2-3 层注意力 ablation | 2-4h T4 |
| Q3 | 跨窗口通信缺失是否是瓶颈？ | 5 个独立窗口零通信 | Swin-shifted window 2 层 | 2-4h T4 |
| Q4 | SRL 物理层是帮助还是瓶颈？ | 被视为"圣域"从未质疑 | 去 SRL ablation | 1-2h T4 |
| Q5 | IC Loss 是否最适合肥尾数据？ | Kurtosis=2006 但 Loss 等权 | 尾部加权 IC 对比 | 1-2h T4 |
| Q6 | B=256 的 IC 梯度噪声是否淹没信号？ | 信噪比 <1 | 梯度累积到 B=1024/2048 | 1h T4 |
| Q7 | 正则化全面缺失是否影响泛化？ | WD≈0, dropout=0, mask=0, L1=0 | 加 dropout+WD ablation | 1h T4 |
| Q8 | MLP baseline 能达到什么水平？ | 从未测试 | 同数据同目标 MLP 对比 | 1-2h T4 |

### 7.2 外审分工建议

| 审计方 | 负责 | 专长匹配 |
|--------|------|---------|
| **Codex (GPT-5.4)** | Q1-Q3 (架构容量/深度/通信), Q8 (baseline) | 代码审计 + 架构判断 |
| **Gemini** | Q4 (SRL 物理学), Q5 (尾部统计), Q6 (IC 采样理论) | 数学/统计 + GCP 优化 |
| **领域专家 (量化)** | Q5 (loss 与交易哲学对齐), Q6 (实操 batch size) | 金融 ML 经验 |

---

## §8. 关键源文件索引

| 文件 | 用途 |
|------|------|
| `omega_epiplexity_plus_core.py` | 数学核心 (当前版本) |
| `train.py` = `gcp/train.py` (字节相同) | 训练脚本 |
| `omega_webdataset_loader.py` | 数据加载器 |
| `tools/omega_etl_v3_topo_forge.py` | ETL 管线 |
| `architect/current_spec.yaml` | 架构规范 |
| `architect/directives/2026-03-18_v3_full_design_audit.md` | 原始架构设计 |
| `architect/directives/2026-03-29_compression_is_intelligence_phase7_golive.md` | hd=64 决策 |
| `architect/insights/INS-019_implicit_compression_victory.md` | 隐式压缩理论 |
| `architect/insights/INS-072_historical_baselines_invalidated_epoch_zero.md` | 历史基线废除 |
| `architect/chain_of_custody.yaml` | 管线追踪 |
| `OMEGA_LESSONS.md` | 79 条教训 |

---

*End of Audit Data Pack*
