# V3 完整 Pipeline Plan & Spec

## Context

V3 基础设施（代码修复、公理系统、spec 全管线覆盖、远程清理）已完成。现在需要从当前状态出发，规划到 V3 全部完成的完整路径。

核心问题：
1. ETL 只完成了一小部分（139 shards），且存在单核瓶颈（ETA 100h）
2. 从未执行过正式烟测
3. 训练脚本、GCS 配置、Vertex AI 配置、回测引擎均不存在

---

## 零、Codex (GPT 5.4 xhigh) 审计结果

**审计日期**: 2026-03-18, 全部 7 项检查 FAIL。以下是必须解决的关键发现：

### 架构师新指令: SRL 前置系数 c 特异性标定（CRITICAL — 公理变更）

**来源**: 架构师指令（本 session 内）
**核心变更**: c = 0.842 不再是全局不变常数，而是 per-stock 动态标定值

**物理解释**:
- δ = 0.5: 宇宙拓扑常数，跨所有 LOB 市场不变 → 仍然是 Layer 1
- c (前置系数): 生态摩擦系数，因市场/股票而异 → **从 Layer 1 降级为 Layer 2**
  - TSE 高流动性: c ≈ 0.842
  - A股 (预期): c 可能显著不同（T+1、涨跌停、散户结构）
  - 大盘股 (工农中建): c 极低（盘口厚如城墙）
  - 微盘妖股: c 极高（盘口薄如蝉翼）

**影响范围**:
1. `omega_epiplexity_plus_core.py`: `AxiomaticSRLInverter` 改为接受 `c_friction` 张量输入
2. 新脚本: `tools/omega_srl_friction_calibrator.py` — 全市场标定（OLS 无截距回归）
3. ETL: 需要将 per-stock c_i 写入 shard (meta.json 或额外 tensor)
4. Loader: 需要传递 c_friction 到模型
5. `omega_axioms.py`: c 从 Layer 1 eternal → Layer 2 calibrated
6. `CLAUDE.md`: 更新规则 #2 和 #11 (只有 δ 是永恒常数)
7. `current_spec.yaml`: physics.c_tse → physics.c_default (降级为回退值)
8. **标定必须在 ETL 之前运行**

**公理影响评级**: ⚠️ AXIOM UPDATE REQUIRED — Layer 1 → Layer 2 降级

**执行顺序**: 标定 → ETL → 烟测 → 训练

---

### 关键发现 1: ETL 跨文件状态断裂（CRITICAL）
- **问题**: discovery 模式下 `file_symbol_states` 每个文件重建，20-day rolling ADV 和 ring buffer 在文件边界重置
- **违反**: spec 要求 20-day rolling ADV 连续计算 + 160 bar (~3天) 宏观窗口
- **影响**: 已生成的 139 个 shards 可能包含不连续的状态跳变
- **修复**: 将 symbol 状态机提升到文件外部（全局 dict），跨文件持续维护

### 关键发现 2: 训练目标未定义 → 已由架构师裁决（RESOLVED）
- **原问题**: ETL 写入 `target.npy = [0.0]`（占位符），spec 用 MAE 命名但代码是 intent prediction
- **架构师裁决**:
  - 正名 SpatioTemporal2DMAE → **Omega-TIB** (Topological Information Bottleneck)
  - Target = 基于 N+1 VWAP 延迟执行的 H-bar 前向收益率 (BP)
  - Block-wise Masking = 输入端致盲（非输出重构）
  - FVU = MSE/Var(target) 为 HPO 最高准则

### 关键发现 3: SRL_Residual / Epiplexity 可能全为零（MEDIUM）
- **问题**: ETL 从 tick 的 `srl_residual` 和 `epiplexity` 字段复制，如果上游 parquet 不含这些字段则默认 0.0
- **需要验证**: 检查远程节点的实际 parquet 文件是否包含这些字段

### 架构师裁决: V_D 物理量纲修复（CRITICAL — 已裁决）

**问题**: loader 计算 `v_d = bid_v + ask_v`（盘口瞬时静止挂单量），SRL 公式要求 V_D 是宏观日均成交量

**架构师裁决**: V_D 和 σ_D 必须是宏观物理量（20-day Rolling ADV / 20-day Rolling ATR），绝不可用微观局部值

**理由**:
1. `bid_v + ask_v` 是静态势能，不是动态动能 — 量纲灾难
2. Volume bar 累计成交量 = vol_threshold (常数) — 分母变死板常量，无意义
3. 标定 c_i 时用的是 daily volume / daily volatility，推理时必须一致

**核心变更: 特征维度从 7 扩展到 10**

| 通道 | 旧 (7) | 新 (10) |
|------|--------|---------|
| 0 | Bid_P | Bid_P (不变) |
| 1 | Bid_V | Bid_V (不变，供 TDA 提取阻力墙结构) |
| 2 | Ask_P | Ask_P (不变) |
| 3 | Ask_V | Ask_V (不变) |
| 4 | Close | Close (不变) |
| 5 | SRL_Residual | SRL_Residual (不变) |
| 6 | Epiplexity | Epiplexity (不变) |
| 7 | — | **delta_p** (微观价格冲击 ΔP) |
| 8 | — | **macro_v_d** (20-day Rolling ADV) |
| 9 | — | **macro_sigma_d** (20-day Rolling ATR) |

**影响范围**:
- `current_spec.yaml`: shape [B, 160, 10, 7] → **[B, 160, 10, 10]**, feature_axis: 7 → 10
- `tools/omega_etl_v3_topo_forge.py`: FEATURE_DIM=10, 新增 rolling_sigma, _collapse 写入通道 7-9
- `omega_webdataset_loader.py`: 完全重写 feature 提取逻辑（通道 7=ΔP, 8=V_D, 9=σ_D）
- `omega_epiplexity_plus_core.py`: forward() 从 x_2d 通道 7-9 提取物理量
- `omega_axioms.py`: feature_axis 更新为 10
- **已有 139 shards 必须全部废弃重新生成**

### 关键发现 5: 文档间 Phase 编号不一致 → 已统一（RESOLVED）
- **统一方案**: plan 使用 Phase 0/0.5/0.6/1A/1B/2/3/4/5/6 编号
- architect docs 中的 Phase 2/3/4 对应 plan 的 Phase 4/5/6（因为 plan 增加了前置修复阶段）
- spec 不使用 phase 编号（只定义参数），phase 编号以 plan 为准

### 关键发现 6: omega_axioms.py 覆盖不足（LOW）
- 只验证 2 层 YAML 标量值
- 不验证 training/hpo/backtest 参数
- 不验证 loader/model 接口契约
- 不验证 ETL 行为语义

---

## 一、当前状态清点

### 已完成 ✅
| 项目 | 状态 |
|------|------|
| 数学核心 `omega_epiplexity_plus_core.py` | 封存，不修改 |
| ETL 管线 `omega_etl_v3_topo_forge.py` | 代码完成，5 fixes applied（但有跨文件状态断裂 bug） |
| WebDataset Loader `omega_webdataset_loader.py` | 完成（sigma_d 修复，但 target 未接入） |
| 公理系统 `omega_axioms.py` | 通过（但覆盖范围有限，见 Codex 审计） |
| 架构 spec `current_spec.yaml` | 全管线覆盖，已更新为 Omega-TIB + 10 通道 + target 定义 |
| 远程节点清理 | Linux1 回收 316GB, Windows1 回收 1+TB |
| V3 shards（部分） | Linux1: 76+1 truncated, Windows1: 61+1 partial（可能需要重新生成）|

### 未完成 ❌
| 项目 | 阻塞原因 |
|------|----------|
| **ETL 跨文件状态修复** | Codex 审计发现 #1，必须先修 |
| **训练目标实现** | 架构师已裁决: Omega-TIB + N+1 VWAP forward return (BP) |
| ETL 多核改造 | 单核瓶颈 100h ETA |
| ETL 全量重新生成 | 依赖上述两项修复 |
| 正式烟测 | 从未执行 |
| `train.py` 训练循环 | 未编写 |
| GCS bucket + Vertex AI 配置 | 未配置 |
| `omega_parallel_crucible.py` 回测 | 未编写 |
| Block-wise Causal Masking | 在 spec 中定义，代码未实现 |

### 关键数据
- 原始数据: 552 trading days (2023-01-03 → 2026-01-30), 2.2TB parquet
- 现有 shards: ~685,000 samples (覆盖率未知，ETL 中途暂停)
- 截断 shard: 两节点各 1 个，需删除

---

## 二、ETL 多核改造（独立关键项目）

### 为什么这是最高优先级

- 当前 ETL 单核运行，V3 数据密度是 V2 的 ~80x
- ETA 从 15h 暴涨至 100h（已记录在 handover）
- `handover/ETL_ENGINEERING_LESSONS.md` 明确指出：pandas groupby 单线程是硬天花板，必须水平分片
- linux1 有 32 核但 ETL 只用了 1 核（heavy-workload.slice 允许 24 核）
- **不解决此问题，全量 ETL 无法在合理时间内完成**

### 瓶颈分析

```
当前处理模型（单线程）:
for fpath in all_files:           # 552 files, 顺序
  for batch in iter_batches():    # 100K rows/batch
    for tick in records:          # 逐 tick
      sm.push_tick(tick)          # 状态机更新
```

瓶颈在于：所有文件顺序处理，所有 symbol 在同一线程内交替处理。

### 多核改造方案

**核心思路**: 文件级并行 — 每个 worker 独立处理一批 parquet 文件，各自维护 symbol 状态机，各自写独立的 shard 输出。最后合并/重编号。

**安全约束** (来自 bitter_lessons + CLAUDE.md):
- fcntl 单实例锁: 改为每个 worker 独立锁文件，master 进程持有全局锁
- OOM 防护: 必须通过 `systemd-run --slice=heavy-workload.slice` 启动
- 禁止 gc.collect() 在紧密循环中
- 禁止 use_threads=True（无条件）
- 每个 worker 内存上限需要估算和测试

**关键难点**: 跨文件的 symbol 状态连续性
- 同一只股票的 tick 分布在多个日期文件中
- 当前架构：每个文件独立维护 `file_symbol_states` 字典，文件结束时状态丢弃
- **这意味着：当前架构已经按文件隔离了状态，天然支持文件级并行！**
- Ring buffer 在文件边界会重置 → 这是已有行为，不是 bug（每个文件独立产出 shards）

**实施计划**:
1. 引入 `joblib.Parallel` 或 `multiprocessing.Pool`
2. 文件列表分 N 组（N = worker 数量, 建议 8-16）
3. 每个 worker 独立 `ShardWriter` 输出到独立目录
4. Master 进程最后合并重编号 shards
5. 添加 `--workers N` CLI 参数
6. 保留 `--workers 1` 作为安全回退

**预估性能提升**: 8 workers → 8x speedup → ~12h 降至 ~1.5h

### 研究与实施建议

**这应该作为独立的关键子项目**，原因：
1. 涉及并发代码，OOM 风险高，需要仔细测试
2. 必须在 linux1 上实际跑 benchmark 才能确定最优 worker 数
3. 需要验证多 worker 产出的 shards 与单 worker 完全等价
4. bitter_lessons #2/#6/#8 都与此相关（OOM、单实例锁、多实例禁止）

---

## 三、V3 Pipeline 完整阶段图

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 0: 基础设施                                    ✅ DONE │
│  CLAUDE.md + axioms + hooks + skills + agents + cleanup     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 0.5: Codex 审计修复（关键前置）          ❌ 最高优先级 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. [CRITICAL] 修复 ETL 跨文件状态断裂:              │    │
│  │    - symbol 状态机提升到文件外部全局 dict            │    │
│  │    - rolling ADV 和 ring buffer 跨文件持续维护      │    │
│  │    - 最后一天的 daily_vol 在文件结束时 flush         │    │
│  │                                                     │    │
│  │ 2. [CRITICAL] 实现训练目标（架构师裁决已确认）:      │    │
│  │    - 正名: SpatioTemporal2DMAE → Omega-TIB          │    │
│  │    - ETL 计算 VWAP + Forward Target (H=20 bars)     │    │
│  │    - target.npy = (VWAP_{N+1+H} - VWAP_{N+1})/VWAP │    │
│  │    - Feature dim 7→10 (新增 ΔP, V_D, σ_D)          │    │
│  │    - 更新 spec: shape→[B,160,10,10], target_model→  │    │
│  │      Omega-TIB, 新增 payoff_horizon, FVU formula    │    │
│  │                                                     │    │
│  │ 3. [MEDIUM] 验证远程 parquet 的 SRL/Epiplexity 字段 │    │
│  │    - SSH 到 linux1 检查实际 parquet schema          │    │
│  │    - 如果字段不存在，需要上游计算步骤               │    │
│  │                                                     │    │
│  │ 4. [CRITICAL] V_D 物理量纲修复（架构师已裁决）:      │    │
│  │    - V_D = 20-day Rolling ADV (宏观日均成交量)       │    │
│  │    - σ_D = 20-day Rolling ATR (宏观日均波动率)       │    │
│  │    - 特征维度 7 → 10 (新增 delta_p, V_D, σ_D)       │    │
│  │    - ETL: rolling_sigma 队列 + 通道 7-9 广播写入     │    │
│  │    - Loader: 重写 feature 提取                       │    │
│  │    - Core model: forward() 从 x_2d 通道 7-9 提取    │    │
│  │                                                     │    │
│  │ 5. [LOW] 统一文档 Phase 编号                        │    │
│  │ 6. [LOW] omega_axioms.py 覆盖范围扩展（可后续）     │    │
│  └─────────────────────────────────────────────────────┘    │
│  验收: omega_axioms.py PASS (39 checks) + Codex PASS (A-G)  │
│  影响: 已有 139 shards 需要废弃重新生成                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 0.6: SRL c 特异性标定                      ❌ 公理变更 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. 编写 tools/omega_srl_friction_calibrator.py      │    │
│  │    - Polars 流式扫描 2.2TB parquet                  │    │
│  │    - 同向游程(Directional Runs)切分代理母单         │    │
│  │    - 无量纲化 + OLS 无截距回归 → per-stock c_i      │    │
│  │    - 多进程并行全市场标定                           │    │
│  │    - 输出: a_share_c_registry.json                  │    │
│  │                                                     │    │
│  │ 2. 重构 AxiomaticSRLInverter                        │    │
│  │    - c 从 __init__ 硬编码 → forward() 动态输入      │    │
│  │    - 接受 c_friction: Tensor [B] 或 [B,1,1,1]      │    │
│  │                                                     │    │
│  │ 3. 更新公理系统                                     │    │
│  │    - omega_axioms.py: c 从 Layer 1 → Layer 2        │    │
│  │    - CLAUDE.md: 规则 #2, #11 更新                   │    │
│  │    - current_spec.yaml: c_tse → c_default           │    │
│  │                                                     │    │
│  │ 4. 更新 ETL: 写入 c_friction 到 shard meta          │    │
│  │ 5. 更新 Loader: 传递 c_friction 到模型              │    │
│  └─────────────────────────────────────────────────────┘    │
│  验收: A股全市场 c_i 标定完成，Median <c> 打印              │
│  前置: 在 linux1 上运行标定脚本 (2.2TB parquet)             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1A: ETL 多核改造                           ❌ 关键路径 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. 分析当前 file-level 状态隔离的可并行性           │    │
│  │ 2. 引入 multiprocessing + 独立 ShardWriter/worker   │    │
│  │ 3. Linux1 benchmark (1/2/4/8/16 workers)            │    │
│  │ 4. 验证多 worker 输出 == 单 worker 输出             │    │
│  │ 5. OOM 测试 (每 worker 内存用量)                    │    │
│  └─────────────────────────────────────────────────────┘    │
│  验收: linux1 上 8 workers 能在 <3h 完成全量 552 files      │
│  关键文件: tools/omega_etl_v3_topo_forge.py                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 1B: 全量 ETL 执行                          ❌ 依赖 1A │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. 删除两节点各 1 个截断 shard                      │    │
│  │ 2. Linux1: systemd-run --slice=heavy-workload.slice │    │
│  │    python3 omega_etl_v3_topo_forge.py --workers 8   │    │
│  │ 3. Windows1: 同步执行                               │    │
│  │ 4. 两节点 shard 统计: 总数、总样本数、符号覆盖      │    │
│  └─────────────────────────────────────────────────────┘    │
│  验收: 全部 552 个交易日处理完成，shard 数量与预期一致      │
│  预计产出: Linux1 ~200+ shards, Windows1 ~300+ shards       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 端到端烟测 (本地 + GCP)                  ❌ 关键门禁│
│                                                             │
│  Step 2.1: 本地数据验证 (linux1)                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 解包 10 个随机 shard，每个检查:                    │    │
│  │   - shape == (160, 10, 10) ✓                         │    │
│  │   - dtype == float32 ✓                              │    │
│  │   - NaN/Inf == 0 ✓                                  │    │
│  │   - 价格范围合理 (0 < Bid_P < 10000) ✓              │    │
│  │   - 成交量 > 0 ✓                                    │    │
│  │   - SRL_Residual 分布检查 (不全为 0) ✓              │    │
│  │   - Epiplexity 分布检查 ✓                           │    │
│  │ • 验证 3 只代表性股票:                               │    │
│  │   - 000001.SZ (大盘高流动性)                        │    │
│  │   - 600519.SH (超大市值)                            │    │
│  │   - 1 只微盘股                                      │    │
│  │ • 检查不同市值股票的 bar 密度是否被容量时钟熨平      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Step 2.2: Loader → Model 端到端测试 (linux1)               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 用 create_dataloader() 从本地 shards 加载 1 batch │    │
│  │ • 验证 10-channel 张量 [B,T,10,10] 及 c_friction [B] │    │
│  │ • Ch8(macro_v_d)>0, Ch9(macro_sigma_d)>0            │    │
│  │ • 接入 Omega-TIB forward(x_2d, c_friction)          │    │
│  │ • 验证 prediction shape, z_core shape               │    │
│  │ • 计算 MDL loss, 确认 loss 是有限数（非 NaN/Inf）   │    │
│  │ • 执行 1 次 backward(), 确认梯度非 NaN              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Step 2.3: GCS 上传 + 云端验证                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 配置 GCS bucket gs://omega-pure-data/             │    │
│  │ • gsutil -m rsync 上传全部 shards                   │    │
│  │ • CRC32C 完整性校验                                 │    │
│  │ • 从 GCS 路径创建 WebDataset loader, 读取 1 batch   │    │
│  │ • 确认云端读取结果 == 本地读取结果                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Step 2.4: Vertex AI GPU 烟测 (单 L4)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 编写 vertex_smoke_test.py:                        │    │
│  │   - 从 GCS 加载 shards                              │    │
│  │   - 实例化 OmegaMathematicalCompressor              │    │
│  │   - 5 forward + 1 backward pass                     │    │
│  │   - 打印 loss, host RAM, GPU VRAM                   │    │
│  │ • 提交 Vertex AI CustomJob (1x L4, g2-standard-4)   │    │
│  │ • 验收: Job SUCCEEDED, loss 非 NaN, RAM < 4GB       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  GATE: Step 2.1-2.4 全部 PASS → 进入 Phase 3               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 编写训练循环 train.py                    ❌ 依赖 2 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 训练循环: forward → loss → backward → step        │    │
│  │ • Block-wise Causal Masking (10-30 volume steps)    │    │
│  │ • Checkpoint 保存/加载                              │    │
│  │ • Loss 追踪 (H_T, S_T, total_MDL)                  │    │
│  │ • Validation split (temporal: 最后 20% 日期)        │    │
│  │ • Mixed precision (fp16)                            │    │
│  │ • Gradient clipping                                 │    │
│  │ • HPO 参数从 CLI args / config 注入                 │    │
│  │ • Vertex AI CustomJob 提交脚本                      │    │
│  └─────────────────────────────────────────────────────┘    │
│  关键文件: train.py (新建)                                  │
│  验收: 本地 10 epoch 训练 loss 持续下降                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Vertex AI HPO Blitzkrieg                 ❌ 依赖 3 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • Google Vizier Bayesian 搜索:                      │    │
│  │   - macro_window: [40, 60, 80, 100, 120, 140, 160] │    │
│  │   - coarse_graining: [1, 2, 4, 8]                  │    │
│  │   - window_size_t: [4, 8, 16, 32]                  │    │
│  │   - window_size_s: [4, 5, 10]                      │    │
│  │ • 100x L4 GPU 并行搜索                              │    │
│  │ • 成功标准: FVU 在特定时空尺度出现 sharp minimum    │    │
│  └─────────────────────────────────────────────────────┘    │
│  验收: 收敛的最优超参组合 + FVU 曲线                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: 全量训练 The Forge                       ❌ 依赖 4 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 锁定 Phase 4 最优超参                             │    │
│  │ • 8x A100 分布式训练 (DDP)                          │    │
│  │ • Block-wise Causal Masking                         │    │
│  │ • 输出: omega_2d_oracle.pth                         │    │
│  │ • 验证: Out-of-sample FVU                           │    │
│  └─────────────────────────────────────────────────────┘    │
│  验收: Out-of-sample FVU < 0.95 (意图预测，非像素重构)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 6: 回测验证 The Crucible                    ❌ 依赖 5 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • 部署 omega_2d_oracle.pth 到 Mac Studio            │    │
│  │ • omega_parallel_crucible.py 事件研究               │    │
│  │ • 三大物理摩擦硬编码:                               │    │
│  │   1. N+1 Bar VWAP 延迟执行                         │    │
│  │   2. 强制 T+1 隔夜跳空暴露                         │    │
│  │   3. 容量时钟计时退场 (80 bars)                     │    │
│  │ • 终极标准: 非对称收益比 > 3.0                      │    │
│  └─────────────────────────────────────────────────────┘    │
│  验收: Payoff Ratio > 3.0 after all physical friction       │
└─────────────────────────────────────────────────────────────┘

---

## 四、烟测详细 Spec (Phase 2)

### 为什么必须烟测

1. V3 ETL 从未被端到端验证过（Bitter Lesson #7: AI 自测自验 = 零置信度）
2. sigma_d Fix 2 影响 SRL 反演质量，需要在真实数据上验证
3. 容量时钟是否真的熨平了大小盘差异？需要实证
4. GCP 部署前必须确认 WebDataset 在云端可用
5. OOM 是 #1 历史杀手，必须在真实负载下压测

### 数据验证检查项（Step 2.1 详细）

| 检查项 | 期望 | 失败处理 |
|--------|------|----------|
| shape | (160, 10, 10) | ETL bug，停止 |
| dtype | float32 | ETL bug，停止 |
| NaN count | 0 | ETL bug，停止 |
| Inf count | 0 | ETL bug，停止 |
| Bid_P range | 0 < x < 10000 (人民币) | 数据清洗问题 |
| Bid_V range | x ≥ 0 | 负成交量 = ETL bug |
| Ask_P > Bid_P (同档) | 对所有非零档位成立 | 盘口倒挂 = 数据质量问题 |
| Close range | 与 Bid_P/Ask_P 区间一致 | 价格不一致 |
| SRL_Residual | 不全为 0，分布合理 | 上游计算问题 |
| Epiplexity | 不全为 0，分布合理 | 上游计算问题 |
| 容量时钟均匀性 | 大盘股 vs 微盘股 bar 密度差异 < 5x | 容量时钟失效 |
| 符号覆盖 | 至少 100 只以上股票 | ETL 过滤过严 |

### 端到端管线验证（Step 2.2 详细）

```python
# 伪代码 — 实际脚本需编写 (Omega-TIB 10-channel 接口)
loader = create_dataloader("local_shards/*.tar", batch_size=4, macro_window=160)
batch = next(iter(loader))

# 1. 张量形状验证 (10 channels per id6 V_D physics ruling)
x_2d = batch["manifold_2d"]  # [B, 160, 10, 10]
assert x_2d.shape == (4, 160, 10, 10)

# 2. 通道语义验证
assert (x_2d[:, :, :, 8] > 0).all()  # Ch8 = macro_v_d > 0
assert (x_2d[:, :, :, 9] > 0).all()  # Ch9 = macro_sigma_d > 0
assert not (x_2d[:, :, :, 5] == 0).all()  # Ch5 = SRL_Residual 非全零
assert not (x_2d[:, :, :, 6] == 0).all()  # Ch6 = Epiplexity 非全零

# 3. 模型前向传播 (新接口: x_2d + c_friction)
c_friction = batch["c_friction"].unsqueeze(-1)  # [B] → [B, 1] per id6 API
model = OmegaMathematicalCompressor(hidden_dim=64)
pred, z_core = model(x_2d, c_friction)

# 4. Loss 计算 (target = forward VWAP return in BP)
target = batch["target"]  # [B]
loss, h_t, s_t = compute_epiplexity_mdl_loss(pred, target, z_core)
assert not torch.isnan(loss)
assert not torch.isinf(loss)

# 5. 反向传播
loss.backward()
for p in model.parameters():
    assert not torch.isnan(p.grad).any()
```

---

## 五、关键文件清单

| 文件 | 角色 | 状态 | 需要操作 |
|------|------|------|----------|
| `tools/omega_etl_v3_topo_forge.py` | V3 ETL | 完成 | 多核改造 |
| `omega_webdataset_loader.py` | 数据加载 | 完成 | — |
| `omega_epiplexity_plus_core.py` | 数学核心 | 封存 | 不修改 |
| `omega_axioms.py` | 公理验证 | 完成 | — |
| `architect/current_spec.yaml` | 架构 spec | 完成 | — |
| `tools/v3_smoke_test.py` | 烟测脚本 | **不存在** | 新建 |
| `train.py` | 训练循环 | **不存在** | 新建 |
| `vertex_smoke_test.py` | GPU 烟测 | **不存在** | 新建 |
| `omega_parallel_crucible.py` | 回测引擎 | **不存在** | 新建 |

---

## 六、执行优先级与依赖关系

```
Phase 0.5 (Codex修复) → Phase 0.6 (c标定) → Phase 1A (多核) → Phase 1B (全量ETL) → Phase 2 (烟测) → Phase 3-6
```

**建议执行顺序**:
1. **立即**: Phase 0.5 — Codex 审计修复（ETL 跨文件状态 + Omega-TIB 实现 + V_D 量纲修复）
2. **紧接**: Phase 0.6 — SRL c 特异性标定（公理变更 + 全市场标定脚本 + 代码重构）
3. **0.5+0.6 完成后**: Codex re-audit → PASS 后继续
4. **继续**: Phase 1A — ETL 多核改造
5. **1A 完成后**: Phase 1B — 全量 ETL 重新生成（已有 139 shards 废弃，新 shards 含 c_friction）
6. **1B 完成后**: Phase 2 — 四步烟测（本地 → Loader → GCS → GPU）
7. **2 通过后**: Phase 3 — 编写 train.py (Omega-TIB + VolumeBlockInputMasking + FVU)
8. **3 完成后**: Phase 4 — Vertex AI HPO
9. **4 收敛后**: Phase 5 — 全量训练
10. **5 完成后**: Phase 6 — 回测验证

**Codex re-audit gate**: Phase 0.5+0.6 完成后需要重新运行 codex exec 审计，至少 A/B/C/D 四项 PASS

**⚠️ 公理变更已批准**: Phase 0.6 将 c 从 Layer 1 永恒常数降级为 Layer 2 可标定参数（用户已于 2026-03-18 确认批准）

---

## 七、风险与约束

| 风险 | 影响 | 缓解 |
|------|------|------|
| 多核 ETL 引入 OOM | linux1 死锁重演 | 必须 heavy-workload.slice + 内存监控 |
| shard 数据质量问题 | 训练结果无意义 | Phase 2 烟测是硬门禁 |
| GCP 配额不足 | 无法启动 HPO | 提前验证 Vertex AI quota |
| Vertex AI L4/A100 成本 | 预算超支 | 先单 L4 烟测，再扩容 |
| 容量时钟未熨平 | 大小盘仍不等价 | 烟测 Step 2.1 检查 bar 密度 |
| sigma_d 计算错误 | SRL 反演失真 | 烟测 Step 2.2 验证 |

---

## 八、架构师四大裁决（已确认）

### 裁决一: 架构正名

**废弃**: `SpatioTemporal2DMAE`（命名遗留物，误导性极强）
**新名**: **Omega-TIB** (Topological Information Bottleneck 欧米伽拓扑信息瓶颈)
- Topological: 有限窗口 2D 容量流形特征提取
- Information Bottleneck: Two-part MDL 压缩 → 标量意图预测

**影响**: `current_spec.yaml` 的 `training.target_model` 改为 `Omega-TIB`

### 裁决二: Target 物理学绝对定义

**核心**: 基于延迟执行的未来宏观容量累计收益率

**公式**:
```
Entry = VWAP of bar N+1 (signal at bar N, forced delay)
Exit  = VWAP of bar N+1+H (H = payoff_horizon, e.g. 20 bars ≈ 半天~1天)
Y     = (VWAP_{N+1+H} - VWAP_{N+1}) / VWAP_{N+1} × 10000 (BP)
```

**ETL 实现三步法（向量化，防索引错位）**:
1. Tick 流 → Volume Bars 序列（含 VWAP）
2. 在 1D Volume Bar 序列上 shift 计算 Forward_Target
3. Sliding Window (160, stride=20) 截取 2D 矩阵，绑定最后一根 Bar 的 target

**影响**:
- ETL `target.npy` 从 `[0.0]` 改为真实 forward return (BP)
- `current_spec.yaml` 新增 `training.payoff_horizon: 20`
- HPO 搜索空间可加入 `payoff_horizon: [10, 20, 40, 80]`

### 裁决三: Block-wise Input Masking（训练时 On-the-fly）

**绝对不在 ETL 阶段做**（保持磁盘数据纯净），而是在 `train.py` GPU DataLoader 中实时发生。

**实现**: `VolumeBlockInputMasking` 模块，架构师已提供完整代码
- min_mask_bars: 10, max_mask_bars: 30
- mask_prob: 0.5（训练时 50% 概率触发）
- 保留最后 5 根 Bar 不遮蔽（模型需要看到"触警现状"）
- 只在 model.train() 模式生效

**串联位置**: `input_proj` 之后、`tda_layer` 之前

### 裁决四: FVU 为最高 HPO 准则

**公式**: `FVU = MSE / Var(target)`
- FVU ≈ 1.0: 模型等同瞎猜均值
- FVU < 0.95 (sharp minimum): 找到了"黄金拓扑窗口"

**优势**: 尺度无关（Scale-invariant），不受不同股票/周期的波动率畸变影响

**影响**: `current_spec.yaml` 的 HPO success_criterion 从 "FVU shows sharp minimum" → 保持但加入具体阈值

### 四大裁决对文件的影响汇总

| 文件 | 变更 |
|------|------|
| `current_spec.yaml` | target_model→Omega-TIB, 新增 payoff_horizon, 更新 success_criterion |
| `tools/omega_etl_v3_topo_forge.py` | 计算 VWAP + Forward Target, 写入真实 target.npy |
| `omega_webdataset_loader.py` | 传递 target 到训练循环 |
| `train.py` (新建) | VolumeBlockInputMasking + FVU 评估器 |
| `omega_epiplexity_plus_core.py` | 不变（数学核心封存） |
| `architect/directives/` | 新 directive 归档 |

---

## 九、补充项

1. **temporal holdout split**: 训练/验证必须按时间切分（最后 20% 日期做验证），不能随机切分（Look-ahead Bias）
2. **shard 合并策略**: 两节点的 shards 需要合并到 GCS，需要处理编号冲突
3. **数据重新生成**: 已确认废弃现有 139 shards，修复 ETL 后全量重新生成
4. **监控仪表盘**: Vertex AI 训练需要 loss 曲线可视化（TensorBoard 或 Vertex AI Experiments）
5. **模型版本管理**: omega_2d_oracle.pth 需要与超参绑定保存
6. **OMP_NUM_THREADS 冲突**: ETL 全局设置 OMP_NUM_THREADS=8，多核改造时每 worker 会各设 8 线程（8 workers × 8 = 64 线程 > 24 核配额）。需要改为 OMP_NUM_THREADS=1 或根据 worker 数动态设置
