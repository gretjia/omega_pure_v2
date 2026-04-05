# OMEGA-TIB 外部审计底稿
**编制日期**: 2026-04-05
**编制者**: Claude Opus 4.6 (多Agent协作：Git考古 + 训练配置 + 模型产出 + Phase历史 + 数据审核)
**审计对象**: Omega-TIB 模型 (24,581 参数)，Phase 3 至 Phase 13 全生命周期

> **致审计师**：所有路径均为项目根目录 `omega_pure_v2/` 的相对路径。标注 `L:xxx` 表示该文件的具体行号，可直接定位。建议按照"核心算法 → 训练管线 → 数据管线 → 配置 → 报告"的顺序阅读。如需查阅原文，请参见[附录A：源文件导航](#附录a核心源码入口建议优先阅读)。

---

## 一、核心数学算法（原始源码 + 变更链）

### 1.1 创世版本（2026-03-16，commit `f7ccde9`）

> **原文位置**: `git show f7ccde9:omega_epiplexity_plus_core.py`

原始架构名：**SpatioTemporal2DMAE**，4个模块：

```python
# ===== 模块一：SRL 物理反演（0可学习参数）=====
class AxiomaticSRLInverter(nn.Module):
    def __init__(self, c_constant=0.842):      # c 硬编码全局常数
        self.c = c_constant
        self.power_constant = 2.0              # 1/δ = 1/0.5，永恒物理常数

    def forward(self, delta_p, sigma_d, v_d):
        dimensionless_impact = |ΔP| / (c × σ_D + ε)
        q_magnitude = dimensionless_impact² × (V_D + ε)
        return sign(ΔP) × q_magnitude

# ===== 模块二：有限窗口拓扑注意力 =====
class FiniteWindowTopologicalAttention(nn.Module):
    def __init__(self, dim, window_size=(4,4), num_heads=4):  # 原始窗口 4×4！
        # QKV + proj，无 RPB（创世版无位置编码）

# ===== 模块三：压缩器主体 =====
class OmegaMathematicalCompressor(nn.Module):
    def __init__(self, raw_feature_dim, hidden_dim, window_size=(4,4)):
        self.input_proj = Linear(raw_feature_dim + 1, hidden_dim)
        self.tda_layer = FWT(hidden_dim, window_size)
        self.epiplexity_bottleneck = [Linear(hd, hd//2), GELU, Linear(hd//2, hd//4)]
        self.intent_decoder = Linear(hd//4, 1)

    def forward(...):
        pooled_z = torch.mean(z_core, dim=[1,2])  # 全局均值池化
        return intent_decoder(pooled_z), z_core

# ===== 模块四：MDL 损失 =====
def compute_epiplexity_mdl_loss(pred, target, z_core, lambda_s=1e-3):
    h_t = MSE(pred, target)
    s_t = L1_norm(z_core)
    return h_t + lambda_s × s_t
```

### 1.2 变更链（16次 commit，20天）

> **验证命令**: `git log --follow --oneline -- omega_epiplexity_plus_core.py`

| # | 日期 | Commit | 变更 | 影响 |
|---|------|--------|------|------|
| 1 | 03-16 | `f7ccde9` | 创世 | 上面的原始代码 |
| 2 | 03-16 (+17min) | `8105a08` | **加入 RPB 位置编码** | 修复置换不变性——原始版无时间箭头 |
| 3 | 03-19 | `28ee9dc` | **重写：更名 Omega-TIB** | c 从硬编码→per-stock输入；input_proj 固定为 Linear(6,64)；新增 FVU 指标 |
| 4-6 | 04-01 | `74138a5` `897caad` `dd6aeac` | `.squeeze()` → `.view(-1)` | 修复+Revert+重做（Gemini 提交引入缩进错误） |
| 7 | 04-02 | `874c1ea` | 加入 Moment-Matched Spear Loss | Huber + 方差匹配（Phase 11e，后废弃） |
| 8 | 04-03 | `b03e66f` | 加入 Unbounded Spear Loss | Leaky Blinding + Scaled MSE（Phase 12 主力） |
| 9 | 04-03 | `ef46878` | 移除 pred×10000 | C-059 过度修正（后恢复） |
| 10 | 04-03 | `65e34d7` | **窗口默认 (4,4)→(32,10)** | Codex 审计修复，对齐 spec |
| 11 | 04-03 | `206af7f` | 恢复 pred×10000 | C-059b：不投影则梯度冻结 |
| 12 | 04-04 | `f578614` | **11轮外审清理** | 删除 Moment-Matched；SRL 加 autocast+float；FWT 默认→(32,10) |
| 13 | 04-04 | `481870b` | **Phase 13 Mandate B** | +AttentionPooling(16参数) +Pre-LN(128参数) +残差连接 |
| 14 | 04-04 | `df2db3a` | **Phase 13 Mandate A** | +IC Loss；lambda_s=0（L1 移除） |

**永恒不变的常数**：`power_constant = 2.0`（δ=0.5 的逆）、`eps = 1e-8`、`num_heads = 4`、GELU 激活、4D 张量结构从未展平。

---

## 二、Omega-TIB 计算时的详细数据

### 2.1 输入张量规范

> **原文位置**: `architect/current_spec.yaml` L:15-31

| 维度 | 值 | 含义 |
|------|-----|------|
| B | 256 | 批大小 |
| T | 160 | 容量时钟窗口（~3天建仓周期） |
| S | 10 | LOB 盘口深度（10个价格层级） |
| F | 10 | 特征通道 |

**10个通道**：

| Ch | 名称 | 物理含义 | 进入模型? | 原文位置 |
|----|------|---------|----------|---------|
| 0 | Bid_P | 买价 | Yes 经 FRT 转换为中间价偏差(BP) | `train.py` L:196-199 |
| 1 | Bid_V | 买量 | Yes 经 log1p 压缩 | `train.py` L:205-207 |
| 2 | Ask_P | 卖价 | Yes 经 FRT 转换为中间价偏差(BP) | `train.py` L:196-199 |
| 3 | Ask_V | 卖量 | Yes 经 log1p 压缩 | `train.py` L:205-207 |
| 4 | Close | 收盘价 | Yes 经 FRT 转换为累计对数收益 | `train.py` L:201-203 |
| 5 | reserved | 预留 | No ETL 写 0.0 | `architect/current_spec.yaml` L:27 |
| 6 | reserved | 预留 | No ETL 写 0.0 | `architect/current_spec.yaml` L:28 |
| 7 | delta_p | 微观价格冲击 | No 仅供SRL消费 | `omega_epiplexity_plus_core.py` L:184 |
| 8 | macro_v_d | 20日均成交量 | No 仅供SRL消费 | `omega_epiplexity_plus_core.py` L:185 |
| 9 | macro_sigma_d | 20日均波动率 | No 仅供SRL消费 | `omega_epiplexity_plus_core.py` L:186 |

### 2.2 数据规模

> **原文位置**: `README.md` L:63-70; `tools/omega_etl_v3_topo_forge.py` L:52-60

| 指标 | 值 | 来源 |
|------|-----|------|
| 原始数据 | 2.2 TB，743个 Parquet 文件 | `handover/LATEST.md` L:40 |
| Shard 总量 | 1,992 个 WebDataset .tar | `README.md` L:66 |
| Shard 总大小 | 556 GB | `README.md` L:66 |
| 总样本数 | **9.96M**（每 shard ≤ 5000 样本） | `README.md` L:66 |
| 训练/验证分割 | 80/20 时序分割（前1594 shard 训练，后398验证） | `train.py` L:583 |
| 标的范围 | 全部 A 股（000/001/002/003/300/301/600/601/603/605/688/689） | `tools/omega_etl_v3_topo_forge.py` L:230-234 |
| GCS 路径 | `gs://omega-pure-data/wds_shards_v3_full/` | `README.md` L:65 |

### 2.3 Target 定义

> **原文位置**: `tools/omega_etl_v3_topo_forge.py` L:173-180; `architect/current_spec.yaml` L:76-84

```
Y = (VWAP_exit - VWAP_entry) / VWAP_entry × 10000  [单位: basis points]
Entry = Bar N+1 的 VWAP（信号延迟一根Bar）
Exit  = Bar N+1+20 的 VWAP（H=20 bars ≈ 0.4 交易日）
```

### 2.4 ETL 管线关键参数

> **原文位置**: `tools/omega_etl_v3_topo_forge.py` L:52-60, L:87, L:117

| 参数 | 值 | 物理含义 | 代码位置 |
|------|-----|---------|---------|
| vol_threshold | 50,000 | 容量时钟阈值（冷启动） | L:87 |
| adv_fraction | 0.02 | 动态阈值 = 20日ADV × 2% | L:54, L:117 |
| window_size | 160 | 最大感受野 | L:52 |
| stride | 20 | 滑窗步长 | L:53 |
| payoff_horizon | 20 | 目标计算前瞻Bar数 | L:58 |
| min_buffer | 181 | 最小发射缓冲(160+1+20) | L:60 |
| shard_max_count | 5,000 | 每shard最大样本数 | L:57 |

### 2.5 训练超参数（Phase 13 实际使用）

> **原文位置**: `gcp/phase13_train_config.yaml`（实际配置）; `train.py` L:474-535（CLI定义）; `train.py` L:630-636（优化器）

| 参数 | 值 | 来源 |
|------|-----|------|
| optimizer | AdamW (weight_decay=1e-5) | `train.py` L:630 |
| scheduler | OneCycleLR (pct_start=0.05, cos anneal, div_factor=100) | `train.py` L:632-636 |
| lr | 3e-4 | `gcp/phase13_train_config.yaml` |
| hidden_dim | 64 | 同上 |
| window_size_t | 32 | 同上 |
| window_size_s | 10 | 同上 |
| batch_size | 256 | 同上 |
| epochs | 15 | 同上 |
| steps_per_epoch | 5,000 | 同上 |
| grad_clip | 1.0 | 同上 |
| lambda_s | 0（L1 禁用） | 同上 |
| mask_prob | 0.0 | 同上 |
| AMP | 关闭（--no_amp） | 同上 |
| loss_precision | FP32 | `architect/current_spec.yaml` L:123 |
| seed | 42 | `train.py` L:479 |
| 硬件 | T4 GPU, Spot | `gcp/phase13_train_config.yaml` |

---

## 三、计算出来的 Omega-TIB 模型详细数据

### 3.1 参数清单（Phase 13，经数据审核员验证）

> **参数计数代码**: `train.py` L:622-627
> **核心架构代码**: `omega_epiplexity_plus_core.py` L:145-212
> **包装器代码**: `train.py` L:156-229

| 组件 | 层 | 参数量 | 占比 | 代码位置 |
|------|-----|--------|------|---------|
| SRL 物理反演 | Layer 1 | 0 | 0% | `omega_epiplexity_plus_core.py` L:19-47 |
| input_proj | Linear(6→64) | 448 | 1.8% | `omega_epiplexity_plus_core.py` L:158 |
| post_proj_norm | LayerNorm(64) [在wrapper中] | 128 | 0.5% | `train.py` L:168 |
| **FWT QKV** | Linear(64→192, no bias) | **12,288** | **50.2%** | `omega_epiplexity_plus_core.py` L:62 |
| FWT proj | Linear(64→64) | 4,160 | 17.0% | `omega_epiplexity_plus_core.py` L:63 |
| **RPB 位置编码** | [1197, 4] 表 | **4,788** | 19.6% | `omega_epiplexity_plus_core.py` L:65-66 |
| Pre-LN | LayerNorm(64) | 128 | 0.5% | `omega_epiplexity_plus_core.py` L:160 |
| Bottleneck 第1层 | Linear(64→32) | 2,080 | 8.5% | `omega_epiplexity_plus_core.py` L:163 |
| Bottleneck 第2层 | Linear(32→16) | 528 | 2.2% | `omega_epiplexity_plus_core.py` L:165 |
| AttentionPooling | W_pool(16) | 16 | 0.1% | `omega_epiplexity_plus_core.py` L:133 |
| IntentDecoder | Linear(16→1) | 17 | 0.1% | `omega_epiplexity_plus_core.py` L:167 |
| **总计** | | **24,581** | 100% | `train.py` L:622 实际输出 |

### 3.2 Phase 13 训练结果

> **训练配置**: `gcp/phase13_train_config.yaml`

- **最佳 Epoch**: E9 / 15
- **Job ID**: `6005517512886714368`（可在 `gcp/manifest.jsonl` 查验）
- **Checkpoint**: `gs://omega-pure-data/checkpoints/phase13_v1/best.pt`

### 3.3 Phase 13 Post-Flight（1,904,748 样本，经审核员逐字段验证）

> **原始数据文件**: `reports/postflight/phase13_v1_global_results.json`

| 指标 | 值 | 统计显著性 | JSON字段名 |
|------|-----|-----------|-----------|
| **Spearman Rank IC** | **+0.0292** | p=0.0（高度显著） | `rank_ic` |
| Pearson IC | +0.0101 | | `pearson_ic` |
| R² | 0.000102 | | `r_squared` |
| **D9-D0 Spread** | **+7.00 BP** | 方向正确 | `long_short_spread_bp` |
| D9 均值 | +8.85 BP | | `top_decile_mean_bp` |
| D0 均值 | +1.85 BP | | `bottom_decile_mean_bp` |
| D9 胜率 | 50.4% | | `deciles[9].hit_rate` |
| D0 胜率 | 46.9% | | `deciles[0].hit_rate` |
| D9 Payoff Ratio | 1.19 | 各 decile 最佳 | `deciles[9].payoff_ratio` |
| 单调性 | 6/9 | | `monotonicity_score` |

### 3.4 Crucible 过拟合验证（64样本，2000步）

> **配置文件**: `gcp/phase13_crucible_config.yaml`
> **审计记录**: `handover/PHASE13_FULL_CHAIN_AUDIT.md`

| 指标 | 初始 → 终值 |
|------|------------|
| IC | 0.04 → **0.88** |
| pred_std 衰减 | 1.3x（Phase 12 为 5x） |

### 3.5 参数演进跟踪

| Phase | 参数量 | hidden_dim | window | 池化 | 损失函数 | 来源 |
|-------|--------|-----------|--------|------|---------|------|
| 3 | ~50K+ | 128 | (4,4) | 全局均值 | Huber + L1 | `handover/PHASE3_V15_TRAINING_REPORT.md` |
| 6/7/8 | ~19.7K | 64 | (4,4) | 全局均值 | IC Loss | `tools/phase7_report.py` L:52 |
| 11d | 21,413 | 64 | (32,4) | 全局均值 | Huber(200) | `reports/phase11d_training_complete.md` |
| 12 | 24,437 | 64 | (32,10) | 全局均值 | Unbounded MSE | `handover/PHASE13_FULL_CHAIN_AUDIT.md` L:19 |
| **13** | **24,581** | 64 | (32,10) | **Attention** | **IC Loss** | `README.md` L:30 |

---

## 四、Phase 5-13 辅助参考数据

### 完整演进时间线

> **指令时间线总索引**: `architect/INDEX.md`
> **管线追踪**: `architect/chain_of_custody.yaml`
> **经验库**: `OMEGA_LESSONS.md` (76条, C-001~C-076)
> **否定知识归档**: `VIA_NEGATIVA.md` (已冻结)

| Phase | 损失函数 | 核心指标 | 信号方向 | 判定 | 关键发现 | 报告位置 |
|-------|---------|---------|---------|------|---------|---------|
| **3** | Huber+Z-score+MDL(λ=1e-3) | FVU=0.9997 | N/A | 勉强 | MDL warmup 期信号存在，结束后被 L1 压死 | `handover/PHASE3_V15_TRAINING_REPORT.md` |
| **5** | IC Loss | Spread=-1.67 BP | 错误 | FAIL | 训练不充分（0.6 pass） | `gcp/phase5a_backtest.yaml` |
| **6** | IC Loss (70试HPO) | Val IC=0.066 | 反转(D9-D0=-5.92) | 矛盾 | 训练指标优秀但 post-flight 系统性反转 | `gcp/phase6_icloss_hpo.yaml` |
| **7** | IC Loss (Phase 6 ckpt) | 不对称比=1.20 | 正确(daily IC=0.028) | FAIL | 信号真实但弱 | `reports/phase7/PHASE7_REPORT.md` |
| **8** | IC Loss (模拟器优化) | Sharpe 0.49→0.66 | 正确 | 部分 | Board loss cap 有效，不对称比天花板 1.21 | `reports/phase8/PHASE8_REPORT.md` |
| **9** | 非对称 Pearson | 全部失败 | N/A | FAIL | 奖励劫持，灾难性过拟合 | `reports/phase9/PHASE9_EVIDENCE.md` |
| **10** | Softmax Portfolio | PfRet=0.210 | Beta 泄漏 | FAIL | 批维度归一化+洗牌=赌场漏洞(C-045) | `reports/phase10/Phase_10_Vanguard_V5_Report.md` |
| **11a** | Softmax+Z-score | NaN | N/A | 灾难 | Z-score 仿射不变→权重范数爆炸(C-042) | `incidents/C-042_zscore_nan/` |
| **11c** | Huber(δ=50) | pred_std=5.6 BP | 模糊 | FAIL | 脑死亡：模型输出近常数 | `reports/audits_and_insights/2026-04-01_phase11c_smoke_test_report.md` |
| **11d** | Huber(δ=200) | daily IC=0.009 | 弱正 | FAIL | 有方差无信号 | `reports/phase11d_training_complete.md` |
| **12** | Unbounded Spear MSE | Rank IC=-0.021 | **反转(29σ)** | FAIL | Leaky Blinding→波动率预测器(Gemini 证明) | `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` |
| **13** | **IC Loss (回归)** | **Rank IC=+0.029** | **正确(D9>D0)** | **PASS** | 首次统计显著正向信号 | `reports/postflight/phase13_v1_global_results.json` |

### 关键教训索引（训练相关核心教训）

> **完整教训库**: `OMEGA_LESSONS.md` L:75 起

| 编号 | 教训 | Ω公理 | 事故详情 |
|------|------|-------|---------|
| C-042 | Z-score + SGD = 权重范数爆炸（数学不兼容） | Ω1 | `incidents/C-042_zscore_nan/` |
| C-045 | 批归一化 + 时间洗牌数据 = 学习 Beta 而非 Alpha | Ω3 | `incidents/C-045_batch_norm_poison/` |
| C-046 | z_sparsity ≈ 0 = 脑死亡，不是最大压缩 | Ω1 | `OMEGA_LESSONS.md` |
| C-049 | 训练-推理 216x 尺度灾难 | Ω3 | `incidents/C-049_train_serve_skew/` |
| C-052 | 脑死亡模型浪费9小时GPU | Ω2 | `incidents/C-052_brain_dead_long_training/` |
| C-054 | 损失函数范式切换是原子全栈事件（6个级联失败） | Ω4 | `OMEGA_LESSONS.md` |
| C-062 | torch.compile `_orig_mod.` 前缀导致权重加载静默失败 | Ω1 | `OMEGA_LESSONS.md` L:153 |
| C-066 | 7次损失函数变更横跨7个Phase，所有 post-flight 失败 | Ω1 | `OMEGA_LESSONS.md` |

---

## 五、审核员发现的疑点（仅疑点，不下结论）

### 疑点 A：Phase 6 IC=0.066 的失效归因存疑

> **关键证据**:
> - torch.compile 首次出现: commit `69ddafd` (2026-04-03)
> - Phase 6 训练完成: commit `ca769ec` (2026-03-29)
> - C-062 教训原文: `OMEGA_LESSONS.md` L:153
> - "可能"措辞: `handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md` L:252
> - 待验证调查: `handover/STRATEGY_B_PIPELINE_VALIDATION.md` L:55-59

项目文档称 Phase 6 的 IC=0.066 因 `torch.compile` bug (C-062) 而失效。但数据审核员发现：**torch.compile 在 2026-04-03 才加入代码，Phase 6 训练在 2026-03-29 已完成。** torch.compile 不可能影响 Phase 6 的训练本身。它只可能影响后来用新代码重跑 Phase 6 checkpoint 的推理。

这意味着 Phase 6 IC=0.066 的训练结果可能是**真实有效的**，被错误地一揽子失效了。如果 Phase 6 信号是真的，那么从 Phase 6 到 Phase 13 的7次损失函数变更可能全是不必要的绕路。

### 疑点 B：Phase 3-8 窗口大小为 (4,4)，非 (32,10)

> **关键证据**:
> - 窗口默认值变更: `git show 65e34d7` (2026-04-03, (4,4)→(32,10))
> - Phase 3 训练报告: `handover/PHASE3_V15_TRAINING_REPORT.md`（未列出 window_size，确认使用默认）
> - Phase 3 时代的代码默认: `git show b77e646:train.py` L:309-310 (default=4)

Phase 3 使用了代码默认的 window_size=(4,4)，即每个窗口只有 4×4=16 个 token。直到 Phase 12 (2026-04-03) 才切换到 (32,10)。这意味着 **Phase 3-8 的所有训练结果都基于一个完全不同的感受野结构**，与当前 spec 描述的 (32,10) 不同。Phase 6 的"历史最佳" IC=0.066 是在 (4,4) 窗口下取得的，不是 (32,10)。

### 疑点 C：hidden_dim 从 128 降到 64 的理由链

> **关键证据**:
> - Phase 3 使用 hd=128: `handover/PHASE3_V15_TRAINING_REPORT.md`
> - Phase 4 HPO 搜索空间: `gcp/phase4_hpo_config_v4.yaml` (hd=[128,256])
> - Phase 13 HPO 搜索空间含 hd=[64,128]: `architect/current_spec.yaml` L:167-168
> - Phase 13 实训固定 hd=64: `gcp/phase13_train_config.yaml`

Phase 3 用 hd=128，Phase 4 HPO 发现 hd=64 (T29) 更优。但 HPO 搜索时 window_size 也在搜索空间中，且当时窗口为 (4,4)。hd=64 的优越性是否与 window=(4,4) 绑定？在 window=(32,10) 下，hd=64 是否仍然是最优选择？Phase 13 HPO 搜索空间包含 hd=[64,128]，但实际训练固定用了 hd=64——HPO 搜索结果是否真的在 (32,10) 窗口下确认了 hd=64 更优？

### 疑点 D：post_proj_norm 的归属不透明

> **关键证据**:
> - 核心文件无此组件: `omega_epiplexity_plus_core.py` (搜索 "post_proj_norm" = 0 结果)
> - 实际定义: `train.py` L:168 (`self.post_proj_norm = nn.LayerNorm(hidden_dim)`)
> - 实际使用: `train.py` L:218 (`x = self.post_proj_norm(x)`)
> - Spec 架构描述: `architect/current_spec.yaml` L:232-261 (5层描述，无 post_proj_norm)
> - 审计文档参数归属互换: `handover/PHASE13_FULL_CHAIN_AUDIT.md` L:171-172

模型核心文件 `omega_epiplexity_plus_core.py` 中的 `OmegaMathematicalCompressor` 共 24,453 参数。但实际训练使用的是 `train.py` 中的 `OmegaTIBWithMasking` 包装器，它额外添加了 `post_proj_norm = LayerNorm(64)`（128参数），使总数达到 24,581。

这个包装器里的 LayerNorm **不在核心数学文件中**，不在 spec 中。审计文档还**颠倒了** AttentionPooling(实为+16) 和 Pre-LN(实为+128) 的参数归属。

### 疑点 E：7 BP spread 与 25 BP 交易成本之间的鸿沟

> **关键证据**:
> - D9-D0 spread: `reports/postflight/phase13_v1_global_results.json` (`long_short_spread_bp: 7.00`)
> - 交易成本: `architect/current_spec.yaml` L:209 (`round_trip_bp: 25`)
> - Phase 7 daily IC: `reports/phase7/PHASE7_REPORT.md` (daily IC=0.028)

Phase 13 取得了项目历史上首次正确方向的统计显著信号（Rank IC=+0.029, D9-D0=+7 BP）。但 7 BP 距离 25 BP 交易成本有 **3.5 倍差距**。所有 decile 扣费后均为负收益。

核心信号强度从 Phase 7 的 daily IC=0.028 到 Phase 13 的 Rank IC=0.029 基本无实质提升。架构改变主要修复了信号方向的正确性，而非信号强度。

### 疑点 F：SRL 物理层对宏观量的遮蔽效应

> **关键证据**:
> - 通道筛选代码: `omega_epiplexity_plus_core.py` L:198 (`lob_features = x_2d[:, :, :, :5]`)
> - SRL 消费通道 7-9: `omega_epiplexity_plus_core.py` L:184-186
> - 通道定义: `architect/current_spec.yaml` L:22-31

通道 7-9（ΔP, V_D, σ_D）只被 SRL 公式消费，神经网络从未直接看到这三个原始值。如果波动率水平（σ_D）本身作为独立的 regime 指标对预测有用，模型无法学习这个关系。

### 疑点 G：Financial Relativity Transform 未被审计覆盖

> **关键证据**:
> - FRT 代码: `train.py` L:185-216（非参数变换，不在核心文件中）
> - 历次外审范围: Codex/Gemini 审计对象为 `omega_epiplexity_plus_core.py`，不包含 `train.py` 中的包装器

`train.py` L:185-216 中的 Financial Relativity Transform 对原始 5 个 LOB 通道做了非参数变换（价格→BP偏差，量→log1p，收盘价→累计对数收益）。这个变换虽无可学习参数，但**改变了输入数据的物理含义和数值分布**。它不在 `omega_epiplexity_plus_core.py` 中，不在 spec 中，且历次外部审计（Codex/Gemini）的审计范围是核心数学文件，不包含 `train.py` 中的包装器。

---

## 附录A：核心源码入口（建议优先阅读）

| 优先级 | 文件 | 行数 | 角色 |
|--------|------|------|------|
| ★★★ | `omega_epiplexity_plus_core.py` | 312 | **数学核心**：SRL反演 + 拓扑注意力 + 信息瓶颈 + 全部损失函数 |
| ★★★ | `train.py` | 751 | **训练管线**：模型包装器 + FRT变换 + 训练循环 + 验证指标 |
| ★★☆ | `tools/omega_etl_v3_topo_forge.py` | 713 | **数据管线**：原始tick→容量时钟→WebDataset shard |
| ★★☆ | `architect/current_spec.yaml` | 261 | **架构规范**：张量合约 + 物理常数 + 训练参数（权威源） |
| ★☆☆ | `omega_webdataset_loader.py` | 105 | 数据加载器：shard解码 + 粗粒化 + 形状校验 |
| ★☆☆ | `omega_axioms.py` | 603 | 公理断言模块：物理/架构不变量自动检查 |
| ★☆☆ | `backtest_5a.py` | 329 | 回测/推理脚本：加载checkpoint + 生成预测 |

### `omega_epiplexity_plus_core.py` 详细导航

| 行号 | 内容 |
|------|------|
| L:19-47 | `class AxiomaticSRLInverter` — SRL物理反演，δ=0.5 硬编码于 L:29 |
| L:50-122 | `class FiniteWindowTopologicalAttention` — 2D窗口注意力，RPB表 L:65-79 |
| L:125-142 | `class AttentionPooling` — 可学习注意力池化，W_pool定义 L:133 |
| L:145-212 | `class OmegaMathematicalCompressor` — 完整模型，forward流程 L:174-212 |
| L:215-242 | `compute_ic_loss()` — IC Loss，sqrt(var+eps)安全 L:237-238 |
| L:245-255 | `compute_epiplexity_mdl_loss()` — MDL Loss（历史） |
| L:258-266 | `compute_fvu()` — FVU指标 |
| L:269-311 | `compute_spear_loss_unbounded()` — Unbounded Spear（历史） |

### `train.py` 详细导航

| 行号 | 内容 |
|------|------|
| L:86-100 | `compute_ic_loss_wrapper` — IC Loss 包装器 |
| L:115-152 | `class VolumeBlockInputMasking` — 输入掩码模块 |
| L:156-229 | `class OmegaTIBWithMasking` — **模型主类（包装器）** |
| L:168 | `post_proj_norm = nn.LayerNorm(hidden_dim)` — 额外128参数来源 |
| L:185-216 | **Financial Relativity Transform** — LOB通道非参数变换 |
| L:218 | `x = self.post_proj_norm(x)` — post_proj_norm使用位置 |
| L:255-279 | `save_checkpoint()` — 原子写入checkpoint |
| L:282-297 | `load_checkpoint()` — checkpoint恢复 |
| L:330-402 | 训练主循环 — AMP + 梯度裁剪 + 步级checkpoint |
| L:344/352 | IC Loss 调用位置（AMP/非AMP两条路径） |
| L:408-466 | `validate()` — 验证函数：Pearson IC、Rank IC、D9-D0 |
| L:448-451 | Rank IC 计算: `spearmanr(pred_np, tgt_np)` |
| L:453-457 | D9-D0 Spread 计算 |
| L:474-535 | `ArgumentParser` — 所有CLI参数及默认值 |
| L:598-612 | 模型实例化 |
| L:615-620 | torch.compile（可选） |
| L:622-627 | **参数计数 + 配置日志** |
| L:630-636 | AdamW + OneCycleLR |
| L:714-722 | Best model 保存条件 (`if val_rank_ic > best_rank_ic`) |

### `tools/omega_etl_v3_topo_forge.py` 详细导航

| 行号 | 内容 |
|------|------|
| L:52-60 | 物理常数：MACRO_WINDOW=160, STRIDE=20, ADV_FRACTION等 |
| L:71-228 | `class OmegaVolumeClockStateMachine` — 容量时钟状态机 |
| L:87 | vol_threshold 冷启动默认值 50000 |
| L:117 | 动态 vol_threshold 标定 |
| L:139 | Volume bar 发射触发条件 |
| L:173-180 | **Target 计算**：T+N VWAP return in BP |
| L:199-228 | 空间bar快照构建（LOB 10档） |
| L:230-237 | A股标的过滤规则 |
| L:343-560 | `_worker_etl` — 主工作函数 |
| L:503-506 | Shard 写入格式（manifold_2d + target + c_friction + date） |

---

## 附录B：训练/HPO 配置文件完整列表

> **目录位置**: `gcp/`

### 训练配置

| 文件 | Phase | 硬件 | 说明 |
|------|-------|------|------|
| `gcp/phase9_train_config.yaml` | 9 | - | 非对称Pearson训练 |
| `gcp/phase10_train_config.yaml` | 10 | - | Softmax Portfolio训练 |
| `gcp/phase11_train_config.yaml` | 11 | - | Phase 11 训练 |
| `gcp/phase11c_train_config.yaml` | 11c | - | Huber(δ=50)训练 |
| `gcp/phase11d_config_A.yaml` | 11d | Spot | Huber(δ=200) Config A |
| `gcp/phase11d_config_A_ondemand.yaml` | 11d | On-Demand | Config A 备选 |
| `gcp/phase11d_config_B.yaml` | 11d | Spot | λ=1e-5 Config B |
| `gcp/phase11d_config_B_ondemand.yaml` | 11d | On-Demand | Config B 备选 |
| `gcp/phase11e_config.yaml` | 11e | - | Moment-Matched Spear |
| `gcp/phase12_smoke_test.yaml` | 12 | - | 烟测 |
| `gcp/phase12_overfit_test.yaml` | 12 | - | 过拟合测试 |
| `gcp/phase12_train_ondemand.yaml` | 12 | On-Demand T4 | 正式训练（1300GB SSD） |
| `gcp/phase12_postflight_inference.yaml` | 12 | - | Post-flight推理 |
| `gcp/phase12_postflight_latest.yaml` | 12 | - | Post-flight最新 |
| `gcp/phase13_crucible_config.yaml` | 13 | On-Demand L4 | Crucible过拟合验证 |
| `gcp/phase13_train_config.yaml` | 13 | Spot T4 | **当前训练配置** |
| `gcp/phase13_postflight_config.yaml` | 13 | - | Post-flight推理配置 |

### HPO 配置

| 文件 | Phase | 说明 |
|------|-------|------|
| `gcp/phase4_hpo_config.yaml` | 4 | HPO 原始配置 |
| `gcp/phase4_hpo_config_v4.yaml` | 4 | HPO v4 (100 trials, L4 Spot) |
| `gcp/phase4_standard_verify.yaml` | 4 | 标准验证 |
| `gcp/phase4_study_spec.yaml` | 4 | Vizier study 规范 |
| `gcp/phase6_icloss_hpo.yaml` | 6 | IC Loss HPO (70 trials, A100 Spot) |
| `gcp/vanguard_convergence.yaml` | - | Vanguard 收敛协议 |
| `gcp/vanguard_v2_icloss.yaml` | - | Vanguard V2 IC Loss |

---

## 附录C：报告与审计文档完整列表

### `reports/` 目录

| 文件/目录 | 内容 |
|----------|------|
| `reports/postflight/phase13_v1_global_results.json` | **Phase 13 Post-Flight 原始 JSON** |
| `reports/phase3/PHASE3_V15_TRAINING_REPORT.md` | Phase 3 训练报告 |
| `reports/phase6/phase6_results/` | Phase 6 回测结果 (equity_curve + trades) |
| `reports/phase7/PHASE7_REPORT.md` | Phase 7 报告 |
| `reports/phase7/Phase_7_Comprehensive_Report.md` | Phase 7 综合分析 |
| `reports/phase7/Phase_7_Full_Simulation.md` | Phase 7 完整模拟 |
| `reports/phase8/PHASE8_REPORT.md` | Phase 8 报告 |
| `reports/phase8/Phase_8_Comprehensive_Report.md` | Phase 8 综合分析 |
| `reports/phase8/phase8_sweep/` | Phase 8 参数扫描（14个配置） |
| `reports/phase9/PHASE9_EVIDENCE.md` | Phase 9 证据包 |
| `reports/phase10/Phase_10_Vanguard_V5_Report.md` | Phase 10 报告 |
| `reports/phase10/phase10_gated_results/` | Phase 10 gated 回测 |
| `reports/phase10_predictions.parquet` | Phase 10 原始预测 (182 MB) |
| `reports/predictions.parquet` | 最新预测 (181 MB) |
| `reports/phase11_complete_data_summary.md` | Phase 11 数据总结 |
| `reports/phase11_engineer_analysis_for_architect.md` | Phase 11 工程分析 |
| `reports/phase11d_training_complete.md` | Phase 11d 训练完成报告 |

### `reports/audits_and_insights/` 目录

| 文件 | 内容 |
|------|------|
| `INDEX.md` | 本目录索引 |
| `id1_math_verification.md` | SRL 数学推导验证 |
| `id2_engineering_audit.md` | 工程架构全面审计 (63KB) |
| `id3_fix_recommendations.md` | 审计修复建议 |
| `id4_srl_friction_calibration.md` | SRL 摩擦系数 c 校准 |
| `id5_mae_vs_intent_prediction.md` | MAE vs Intent Prediction 裁决 |
| `id6_vd_physics_ruling.md` | V_D 物理规律判定 |
| `gemini_bitter_lessons.md` | Gemini 8条苦涩教训 |
| `2026-03-30_gemini_softmax_portfolio_loss_audit.md` | Softmax Loss 数学审计 |
| `2026-03-30_gemini_gcs_io_optimization_audit.md` | GCS I/O 优化审计 |
| `2026-04-01_inference_scale_explosion_fix.md` | 推理 216x 尺度爆炸修复 |
| `2026-04-01_phase11c_smoke_test_report.md` | Phase 11c 烟测报告 |
| `omega_core_insights.md` | Omega 核心洞察全集 (63KB) |

### `handover/` 目录

| 文件 | 内容 |
|------|------|
| `LATEST.md` | **当前项目状态**（跨会话连续性文档） |
| `HARDWARE_TOPOLOGY.md` | 四节点集群拓扑 |
| `PHASE3_V15_TRAINING_REPORT.md` | Phase 3 训练报告 |
| `PHASE12_ARCHITECT_AUDIT_BRIEF.md` | Phase 12 审计简报 |
| `PHASE13_FULL_CHAIN_AUDIT.md` | Phase 13 全链审计 |
| `STRATEGY_B_PIPELINE_VALIDATION.md` | Strategy B 管线验证 |
| `ETL_ENGINEERING_LESSONS.md` | ETL 工程教训 |
| `EXPERIMENTAL_DESIGN_AND_ROADMAP.md` | 实验设计与路线图 |
| `GCP_PRICING_REFERENCE.md` | GCP 定价参考 |

---

## 附录D：事故库与规则引擎

### 事故库 (`incidents/`)

> 每个事故含 4 文件: `meta.yaml`（摘要）、`root_cause.md`（根因）、`resolution.md`（修复）、`trace.md`（轨迹）

| 事故 | 目录 | 审计相关性 |
|------|------|-----------|
| C-020 | `incidents/C-020_checkpoint_dir_reuse/` | Checkpoint目录复用bug |
| C-028 | `incidents/C-028_pd_ssd_throughput/` | PD-SSD 吞吐量事故 |
| C-040 | `incidents/C-040_pd_ssd_repeat/` | PD-SSD 重复事故 |
| C-042 | `incidents/C-042_zscore_nan/` | **Z-score NaN爆炸（Phase 11a 灾难根因）** |
| C-044 | `incidents/C-044_stale_checkpoint_resume/` | 陈旧checkpoint恢复bug |
| C-045 | `incidents/C-045_batch_norm_poison/` | **批归一化中毒（Phase 10 失败根因）** |
| C-049 | `incidents/C-049_train_serve_skew/` | **训练-推理 216x 尺度灾难** |
| C-050 | `incidents/C-050_dead_code_residue/` | 死代码残留 |
| C-052 | `incidents/C-052_brain_dead_long_training/` | **脑死亡9小时GPU浪费** |
| C-053 | `incidents/C-053_docker_code_timing/` | Docker代码时序 |

### 与训练相关的规则 (`rules/active/`)

| 规则 | 文件 | 防护目标 |
|------|------|---------|
| R-004 | `rules/active/R-004_delta_immutable.yaml` | δ=0.5 不可修改 |
| R-008 | `rules/active/R-008_batch_norm_ban.yaml` | 禁止 BatchNorm（C-045教训） |
| R-010 | `rules/active/R-010_loss_change_checklist.yaml` | 损失函数变更检查清单 |
| R-014 | `rules/active/R-014_long_training_smoke.yaml` | >1h训练前强制烟测 |
| R-016 | `rules/active/R-016_spec_code_drift.yaml` | Spec-代码漂移检测 |
| R-017 | `rules/active/R-017_inference_alignment_gate.yaml` | 推理-训练对齐门禁 |

---

## 附录E：Git 考古命令速查

审计师如需自行验证变更历史：

```bash
# 核心算法文件完整变更历史（16次commit）
git log --follow --oneline -- omega_epiplexity_plus_core.py

# 查看创世版本完整源码
git show f7ccde9:omega_epiplexity_plus_core.py

# 查看特定commit的diff
git show <commit_hash> -- omega_epiplexity_plus_core.py

# 窗口默认值从(4,4)→(32,10)的变更
git show 65e34d75 -- omega_epiplexity_plus_core.py

# torch.compile 首次引入的commit
git log --all --oneline --diff-filter=A -S "torch.compile" -- train.py

# Phase 13 两个 Mandate 的commit
git show 481870b  # Mandate B: AttentionPooling + Pre-LN
git show df2db3a  # Mandate A: IC Loss

# 全项目commit时间线
git log --oneline --all | head -50
```

---

## 附录F：数据审核员验证状态

| 验证项 | 状态 | 详细位置 |
|--------|------|---------|
| Phase 13 参数总数 24,581 | CONFIRMED | `train.py` L:622 实际计数代码 |
| +128 来源为 post_proj_norm | CONFIRMED | `train.py` L:168 定义 |
| Phase 13 Post-Flight 全部数值 | CONFIRMED | `reports/postflight/phase13_v1_global_results.json` 逐字段比对 |
| RPB 表大小 [1197,4]=4788 | CONFIRMED | `omega_epiplexity_plus_core.py` L:65-66 |
| FRT 零可学习参数 | CONFIRMED | `train.py` L:185-216 纯算术变换 |
| Checkpoint 大小合理性 (398KB) | CONFIRMED | AdamW optimizer state 解释 |
| Phase 3 窗口 (4,4) | CONFIRMED | 训练报告未覆盖=使用代码默认值 |
| torch.compile 晚于 Phase 6 | DISCREPANCY | Phase 6: 03-29完成, torch.compile: 04-03引入 |
| 审计文档参数归属互换 | DISCREPANCY | `handover/PHASE13_FULL_CHAIN_AUDIT.md` L:171-172 AttnPool与Pre-LN参数标注互换 |
