# Omega Pure Handover Knowledge Base

Critical handover state, architectural documentation, workflow automation, and engineering post-mortems.

---

## AI Agent Entry Protocol

```
Step 1: CLAUDE.md          → 不可违反的规则（自动加载）
Step 2: handover/LATEST.md → 当前状态 + machine-readable YAML
Step 3: 本文件              → 按任务导航到具体文档
```

**如果你是来做审计的**：直接跳到 [审计入口](#audit-entry-points)。

---

## Audit Entry Points

### Core Algorithm Files（必审）

| File | Role | 关键审计点 |
|------|------|-----------|
| [`omega_epiplexity_plus_core.py`](../omega_epiplexity_plus_core.py) | 数学核心 | SRL physics (δ=0.5 immutable) / Loss 量纲 / 梯度流 / bottleneck 压缩 |
| [`train.py`](../train.py) | 训练循环 | FRT 特征工程 / D9-D0 验证指标 / checkpoint _orig_mod. strip / 单实例锁 |
| [`backtest_5a.py`](../backtest_5a.py) | 推理+统计 | pred_bp * 10000 / defaults alignment (hd=64, wt=32, costs=25) |
| [`omega_webdataset_loader.py`](../omega_webdataset_loader.py) | 数据加载 | target 单位 = BP (ETL 已 ×10000) / c_friction 默认 0.842 |
| [`gcp/phase7_inference.py`](../gcp/phase7_inference.py) | 全量推理 | _orig_mod. strip / z_sparsity hook / pred_bp 输出 |

### Spec & Architecture（规范对齐审计）

| File | Content |
|------|---------|
| [`architect/current_spec.yaml`](../architect/current_spec.yaml) | 张量形状 [B,160,10,10] / 物理常数 / 训练参数 / HPO 搜索空间 |
| [`architect/INDEX.md`](../architect/INDEX.md) | 37 条架构师指令时间线 (2026-03-18 ~ 04-02) |
| [`architect/insights/INDEX.md`](../architect/insights/INDEX.md) | 64 张 Insight 卡 (INS-001 ~ INS-064) |
| [`architect/chain_of_custody.yaml`](../architect/chain_of_custody.yaml) | Directive → Deploy 全链追踪 |

### Audit Reports（已有审计结果）

| Report | Location | Summary |
|--------|----------|---------|
| **Phase 12 架构师审计简报** | [`PHASE12_ARCHITECT_AUDIT_BRIEF.md`](./PHASE12_ARCHITECT_AUDIT_BRIEF.md) | 11 轮外部审计 + overfit test + gradient check + 6 个裁决问题 |
| **Phase 11 数据汇总** | [`../reports/phase11_complete_data_summary.md`](../reports/phase11_complete_data_summary.md) | 11a-d 全阶段数据 |
| **Phase 11 工程分析** | [`../reports/phase11_engineer_analysis_for_architect.md`](../reports/phase11_engineer_analysis_for_architect.md) | 工程视角诊断 |
| **Gemini Bitter Lessons** | [`../reports/audits_and_insights/`](../reports/audits_and_insights/) | 外部数学审计历史 |

### Experience & Governance

| File | Content |
|------|---------|
| [`../OMEGA_LESSONS.md`](../OMEGA_LESSONS.md) | 64 条教训 (C-001~C-064) + 6 元公理 (Ω1-Ω6) + 操作手册 |
| [`../incidents/INDEX.yaml`](../incidents/INDEX.yaml) | 64 事件索引 (machine-readable) + 10 完整 trace |
| [`../rules/active/`](../rules/active/) | 16 条 YAML 执法规则 |
| [`../LIVING_HARNESS.md`](../LIVING_HARNESS.md) | Meta-Harness V3 架构说明 |

---

## Task-Based Navigation

| 你要做什么 | 先读这些 |
|-----------|---------|
| **审计模型代码** | 上方 [Core Algorithm Files](#core-algorithm-files必审) + [`PHASE12_ARCHITECT_AUDIT_BRIEF.md`](./PHASE12_ARCHITECT_AUDIT_BRIEF.md) |
| **理解项目物理** | [`CLAUDE.md`](../CLAUDE.md) §WHY + [`VIA_NEGATIVA.md`](../VIA_NEGATIVA.md) + `architect/insights/INS-019~020` |
| **修改 Loss 函数** | [`PHASE12_ARCHITECT_AUDIT_BRIEF.md`](./PHASE12_ARCHITECT_AUDIT_BRIEF.md) §七（6 个裁决问题）+ Phase 6/9/10/11/12 Loss 历史 |
| **修改 SRL / TDA** | `architect/insights/INS-005` (c 标定) + `INS-057` (SRL 捷径) + Codex TDA 审计结果 |
| **修改 ETL** | [`ETL_ENGINEERING_LESSONS.md`](./ETL_ENGINEERING_LESSONS.md) + `INS-016` (cg 不可二次粗粒化) |
| **回测 / 模拟** | `INS-023` (T+1 铁律) + `INS-022` (时空换算) + `backtest_5a.py` |
| **训练调参** | [`architect/current_spec.yaml`](../architect/current_spec.yaml) + `OMEGA_LESSONS.md` 案例库 |
| **部署 GCP** | [`HARDWARE_TOPOLOGY.md`](./HARDWARE_TOPOLOGY.md) + [`GCP_PRICING_REFERENCE.md`](./GCP_PRICING_REFERENCE.md) + `gcp/safe_*.sh` |
| **追溯 Phase 决策** | [`architect/INDEX.md`](../architect/INDEX.md) + `reports/phase{N}/` |

---

## GCS Data Assets

```
gs://omega-pure-data/wds_shards_v3_full/               # 1992 shards, 556GB, 9.96M samples
gs://omega-pure-data/checkpoints/phase12_unbounded_v1/  # best.pt (E0) + latest.pt (E19)
gs://omega-pure-data/postflight/                        # Phase 12 val predictions (E0 + E19)
```

## Model Checkpoint Info

| Checkpoint | Epoch | D9-D0 | pred_std | z_sparsity | Parquet |
|-----------|-------|-------|----------|------------|---------|
| best.pt | E0 | 4.51 BP | 26.61 BP | 5.4% | `phase12_val_predictions.parquet` |
| latest.pt | E19 | 1.29 BP | 18.57 BP | 18.5% | `phase12_latest_val_predictions.parquet` |

---

## Start Here (Legacy Navigation)
- **[`LATEST.md`](./LATEST.md)**: Single Source of Truth — current status, machine-readable state
- **[`../CLAUDE.md`](../CLAUDE.md)**: Project constitution (auto-loaded every session)
- **[`../OMEGA_LESSONS.md`](../OMEGA_LESSONS.md)**: Experience library — axioms + operations manual + 64 cases
- **[`../VIA_NEGATIVA.md`](../VIA_NEGATIVA.md)**: Falsified paths — what NOT to do (frozen archive)

## Engineering & Infrastructure
- **[`HARDWARE_TOPOLOGY.md`](./HARDWARE_TOPOLOGY.md)**: Physical nodes (omega-vm, linux1, windows1, mac), IPs, SSH routes
- **[`GCP_PRICING_REFERENCE.md`](./GCP_PRICING_REFERENCE.md)**: GCP pricing reference (Vertex AI / GCS / Nearline)
- **[`ETL_ENGINEERING_LESSONS.md`](./ETL_ENGINEERING_LESSONS.md)**: OOM deadlocks, cgroup CPU throttling, Python anti-patterns

## Scripts Quick Reference

| Script | Purpose | Key Args |
|--------|---------|----------|
| `train.py` | Training (Unbounded Spear + MDL) | `--shard_dir --epochs 20 --lambda_s 1e-4 --static_mean_bp 40.0` |
| `gcp/phase7_inference.py` | Full inference → parquet | `--checkpoint --shard_dir --val_only --hidden_dim 64 --window_size_t 32` |
| `tools/postflight_analysis.py` | Post-flight analysis | `python3 tools/postflight_analysis.py predictions.parquet` |
| `backtest_5a.py` | Statistical signal test | `--checkpoint --shard_dir --costs_bp 25` |
| `omega_axioms.py` | Axiom self-check (37 assertions) | `python3 omega_axioms.py --verbose` |
| `tools/spec_code_alignment.py` | Spec-Code drift detection | `python3 tools/spec_code_alignment.py` |

## External Audit Invocation

```bash
# Codex (code audit)
codex exec --full-auto "audit prompt here"

# Gemini (math audit)
source .env
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent?key=${GEMINI_API_KEY}" \
  -H 'Content-Type: application/json' \
  -d '{"contents": [{"parts": [{"text": "audit prompt"}]}], "generationConfig": {"temperature": 0.1}}'

# Axiom self-check
python3 omega_axioms.py --verbose
```

## Workflow Automation

### Hooks (`.claude/hooks/`)
| Hook | Trigger | Function |
|------|---------|----------|
| `block-destructive.sh` | Pre-Bash | Block rm -rf, force push, physics constant changes |
| `rule-engine.sh` | Pre-Edit/Write | 16-rule data-driven enforcement |
| `post-edit-axiom-check.sh` | Post-Edit/Write | Auto axiom check on core file changes |
| `post-bash-error-tracker.sh` | Post-Bash (fail) | Instant error tracking to session log |
| `lesson-enforcer.sh` | Pre-Write | pd-ssd / disk size enforcement |
| `pipeline-quality-gate.sh` | Pre-Write | Architect directive completeness check |

### Skills (`.claude/skills/`)
| Command | Function |
|---------|----------|
| `/dev-cycle` | 10-stage dev cycle (PreMortem → External Audit → Summary) |
| `/deploy-cycle` | 7-stage deploy cycle (Pre-flight → Verify → Document) |
| `/axiom-audit` | 3-layer axiom audit (self + Codex + Gemini) |
| `/architect-ingest` | Architect directive ingestion + axiom impact detection |
| `/lesson-to-rule` | Convert lesson to executable YAML rule |
| `/harness-reflect` | Self-assessment + health score |
| `/pre-flight` | 9-item pre-deploy check |

---

*Last updated: 2026-04-04. Phase 12 post-flight complete, awaiting architect audit.*
