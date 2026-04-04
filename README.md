# OMEGA PURE V3: Topological Information Bottleneck for Institutional Metaorder Detection

Quantitative finance research: Finite Window Topological Attention + MDL compression, extracting institutional metaorder flow signals from A-share L1 tick data.

**Tech Stack**: Python 3.10+, PyTorch, PyArrow, WebDataset, NumPy, Numba | GCP Vertex AI (T4/L4/A100) | 2.2TB raw → Volume-Clocked tensors

---

## Quick Start for AI Agents

```
1. Read CLAUDE.md              — Project constitution (auto-loaded)
2. Read handover/LATEST.md     — Current status + machine-readable state
3. Read this file              — File map + audit entry points
```

---

## Core Algorithm Files (审计入口)

| File | Lines | Role | 审计重点 |
|------|-------|------|----------|
| **`omega_epiplexity_plus_core.py`** | ~255 | 数学核心：SRL 反演 + FWT 拓扑注意力 + MDL Loss | 物理公理 (δ=0.5) / Loss 量纲 / 梯度流 |
| **`train.py`** | ~800 | 训练循环 + OmegaTIBWithMasking wrapper | Financial Relativity Transform / D9-D0 验证 / checkpoint 保存 |
| **`backtest_5a.py`** | ~310 | 推理 + 统计测试（十分位分析） | Train-serve skew / pred_bp 量纲 / 默认值对齐 |
| **`omega_webdataset_loader.py`** | ~98 | WebDataset 流式加载 | target 单位 (BP) / c_friction 默认值 |
| **`gcp/phase7_inference.py`** | ~490 | 全量推理管线（输出 parquet + z_sparsity） | _orig_mod. strip / FUSE vs pipe |
| **`omega_axioms.py`** | ~140 | 公理断言模块（37 checks） | `python3 omega_axioms.py --verbose` |

### 模型架构一览（24,437 参数）
```
Input [B, 160, 10, 10] + c_friction [B, 1]
  │
  ├─ SRL Inverter (NO_GRAD): ch7/8/9 → q_metaorder [B, 160]    # 物理层，不可学
  ├─ FRT: ch0-4 → relative features [B, 160, 10, 5]             # 特征工程（在 wrapper 中）
  │
  ├─ Concat [5 LOB + 1 SRL] → input_proj(6→64) → LayerNorm(64)
  ├─ FiniteWindowTopologicalAttention(dim=64, window=(32,10), heads=4)  # 87% 参数
  ├─ EpiplexityBottleneck: Linear(64→32) → GELU → Linear(32→16)
  ├─ Global Mean Pooling over [T, S] → [B, 16]
  └─ IntentDecoder: Linear(16→1) → scalar prediction
```

---

## Audit Reports & Diagnostics

| Report | Location | Content |
|--------|----------|---------|
| **Phase 12 架构师审计简报** | [`handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md`](handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md) | 11 轮外部审计 + post-flight + overfit test + 6 个架构师裁决问题 |
| **Handover 状态** | [`handover/LATEST.md`](handover/LATEST.md) | 当前状态 + machine-readable YAML |
| **经验库** | [`OMEGA_LESSONS.md`](OMEGA_LESSONS.md) | 64 条教训 (C-001~C-064) + 6 条元公理 (Ω1-Ω6) |
| **事件 Trace Vault** | [`incidents/INDEX.yaml`](incidents/INDEX.yaml) | 64 事件索引 + 10 个完整 trace |
| **架构师指令时间线** | [`architect/INDEX.md`](architect/INDEX.md) | 37 条指令 (2026-03-18 ~ 04-02) |
| **架构规范** | [`architect/current_spec.yaml`](architect/current_spec.yaml) | 张量形状 / 物理常数 / 训练参数 / HPO 搜索空间 |
| **Insight Cards** | [`architect/insights/INDEX.md`](architect/insights/INDEX.md) | 64 张结构化洞察卡 (INS-001 ~ INS-064) |
| **执法规则** | [`rules/active/`](rules/active/) | 16 条 YAML 规则（rule-engine.sh 自动执法） |

---

## GCS Data Assets

```
gs://omega-pure-data/wds_shards_v3_full/          # 1992 shards, 556GB, 9.96M samples
gs://omega-pure-data/checkpoints/phase12_unbounded_v1/  # best.pt (E0) + latest.pt (E19)
gs://omega-pure-data/postflight/                   # Phase 12 val predictions parquet
```

---

## Phase History

| Phase | Status | Loss | Best Metric | Key Finding |
|-------|--------|------|-------------|-------------|
| 1 | Done | — | 1992 shards | TB-scale ETL complete |
| 6 | Done | **IC Loss** | **IC=0.066** | 历史最高排序能力 |
| 7 | Done | IC Loss | 17-test pass | Full inference + diagnostic |
| 8 | Done | IC Loss | Sharpe +34% | board_loss_cap validated |
| 9 | Failed | Asymmetric Pearson | — | 7 jobs, all Reward Hacking |
| 10 | Done | Softmax Portfolio | Asym=1.30 | PfRet=0.210 但 z_core 脑死亡 |
| 11a-c | Failed | Various | — | NaN / Beta 走私 / 方差坍缩 |
| 11d | Done | Pointwise Huber | D9-D0=6.84 | 方差恢复但 IC 下降 |
| **12** | **Post-flight** | **Unbounded MSE** | **D9-D0=4.51** | **方差恢复 ✓ 但排序失败 (Rank IC=-0.02)** |

**Phase 12 诊断**（11 轮外部审计确认）：
1. Leaky Blinding 导致模型预测波动率而非 Alpha（Gemini 数学证明）
2. MSE 不适合排序任务（Phase 6 IC Loss 历史最佳）
3. Global mean pooling 摧毁时空结构
4. TDA 位置编码梯度极弱（0.08 vs decoder 4811）

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `train.py` | Training loop (Unbounded Spear + MDL, Phase 12) |
| `omega_epiplexity_plus_core.py` | Math core (SRL + FWT + MDL + Loss functions) |
| `omega_webdataset_loader.py` | WebDataset streaming loader |
| `tools/omega_etl_v3_topo_forge.py` | ETL: Parquet → WebDataset shards |
| `gcp/phase7_inference.py` | Full inference (exports predictions + z_sparsity) |
| `tools/postflight_analysis.py` | Post-flight 全量分析 (阈值标定+十分位+Epiplexity) |
| `backtest_5a.py` | Statistical signal test (decile + correlation) |
| `tools/spec_code_alignment.py` | Spec-Code 参数漂移检测 |
| `gcp/safe_build_and_canary.sh` | Docker build + 1-shard canary |
| `gcp/safe_submit.sh` | Full job submission with manifest tracking |

## Living Harness (Meta-Harness V3)

Self-evolving engineering governance. See [`LIVING_HARNESS.md`](LIVING_HARNESS.md).

| Layer | Component | Function |
|-------|-----------|----------|
| Memory | `incidents/` Trace Vault | Raw failure context (never compressed) |
| Enforcement | `rules/active/*.yaml` | 16 data-driven rules (add YAML = instant enforcement) |
| Evolution | `/harness-reflect` | Self-assessment + rule pruning + health score |
| Pipeline | `chain_of_custody.yaml` | Directive → Deploy full lifecycle tracking |

## External Audit Tools

| Tool | Purpose | Invocation |
|------|---------|------------|
| **Codex** (GPT 5.4) | Code correctness / spec alignment / architecture | `codex exec --full-auto "<prompt>"` |
| **Gemini** (3.1 Pro) | Math proofs / gradient analysis / statistical tests | `curl` API (key in `.env`) |
| **omega_axioms.py** | 37 axiom assertions (self-check) | `python3 omega_axioms.py --verbose` |

---

*Current status: 2026-04-04. Phase 12 post-flight complete — signal insufficient, awaiting architect audit.*
*For AI Agents: Start at [`handover/LATEST.md`](handover/LATEST.md). Full audit at [`handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md`](handover/PHASE12_ARCHITECT_AUDIT_BRIEF.md).*
