# Omega Pure Handover Knowledge Base

Critical handover state, architectural documentation, workflow automation, and engineering post-mortems.

---

## Path Finder — AI Agent 快速导航

> **新 Agent 进场顺序**: CLAUDE.md → LATEST.md → 按任务查下表

| 你要做什么 | 先读这些 |
|-----------|---------|
| 理解项目核心物理 | [`CLAUDE.md`](../CLAUDE.md) §WHY + [`VIA_NEGATIVA.md`](../VIA_NEGATIVA.md) + [`architect/insights/INS-019`](../architect/insights/INS-019_implicit_compression_victory.md) + [`INS-020`](../architect/insights/INS-020_topology_epiplexity_unification.md) |
| 修改损失函数 | [`architect/insights/INS-033`](../architect/insights/INS-033_softmax_portfolio_loss_paradigm_shift.md) (Softmax Portfolio Loss) + [`INS-035`](../architect/insights/INS-035_phase9_asymmetric_pearson_postmortem.md) (Pearson 验尸) + [`reports/audits_and_insights/`](../reports/audits_and_insights/) |
| 修改 SRL / 拓扑注意力 | [`architect/insights/INS-005`](../architect/insights/INS-005_srl_c_calibration.md) (c 标定) + [`reports/audits_and_insights/id4`](../reports/audits_and_insights/id4_srl_friction_calibration.md) + [`id6`](../reports/audits_and_insights/id6_vd_physics_ruling.md) |
| 修改 ETL / 数据管线 | [`ETL_ENGINEERING_LESSONS.md`](./ETL_ENGINEERING_LESSONS.md) + [`architect/insights/INS-016`](../architect/insights/INS-016_cg_microstructure_protection.md) (cg 不可二次粗粒化) |
| 回测 / 模拟 | [`architect/insights/INS-023`](../architect/insights/INS-023_t1_simulation_iron_rules.md) (T+1 三铁律) + [`INS-022`](../architect/insights/INS-022_spacetime_correction_20bars_04days.md) (时空换算) + [`reports/phase10/`](../reports/phase10/) |
| 训练调参 | [`architect/current_spec.yaml`](../architect/current_spec.yaml) + [`OMEGA_LESSONS.md`](../OMEGA_LESSONS.md) 案例库 (C-xxx) + [`architect/insights/INS-036`](../architect/insights/INS-036_softmax_scale_explosion_variance_fix.md)~[`048`](../architect/insights/INS-048_lambda_s_recalibration.md) |
| 部署到 GCP / 远程节点 | [`HARDWARE_TOPOLOGY.md`](./HARDWARE_TOPOLOGY.md) + [`GCP_PRICING_REFERENCE.md`](./GCP_PRICING_REFERENCE.md) + `gcp/safe_*.sh` 脚本 |
| 追溯某个 Phase 的决策 | [`architect/INDEX.md`](../architect/INDEX.md) (指令时间线) + [`reports/phase{N}/`](../reports/) + [`architect/insights/INDEX.md`](../architect/insights/INDEX.md) |
| 理解项目演进全貌 | [`reports/`](../reports/) 按 phase3→6→7→8→9→10 顺序 + [`reports/audits_and_insights/omega_core_insights.md`](../reports/audits_and_insights/omega_core_insights.md) |

---

## Start Here
- **[`LATEST.md`](./LATEST.md)**: Single Source of Truth — current status, file map, next steps, rules for next agent
- **[`../CLAUDE.md`](../CLAUDE.md)**: Project constitution (auto-loaded by Claude CLI every session)
- **[`../OMEGA_LESSONS.md`](../OMEGA_LESSONS.md)**: 唯一经验源 — 元公理 + 操作手册 + 案例库 (C-001~C-03x)
- **[`../VIA_NEGATIVA.md`](../VIA_NEGATIVA.md)**: Falsified paths — what NOT to do (frozen archive)

## Architecture & Insights
- **[`../architect/current_spec.yaml`](../architect/current_spec.yaml)**: Current architecture params (tensor shape, physics constants, ETL config)
- **[`../architect/INDEX.md`](../architect/INDEX.md)**: Architect directive timeline (21 directives, 2026-03-18 ~ 04-01)
- **[`../architect/insights/INDEX.md`](../architect/insights/INDEX.md)**: 48 structured insight cards (INS-001 ~ INS-048)
- **[`../omega_axioms.py`](../omega_axioms.py)**: Axiom assertions (37 checks, `python3 omega_axioms.py --verbose`)

## Reports & Evidence (按 Phase 组织)
- **[`../reports/phase3/`](../reports/phase3/)**: V15 训练报告
- **[`../reports/phase6/`](../reports/phase6/)**: 回测结果 (Equity, Trades)
- **[`../reports/phase7/`](../reports/phase7/)**: T29 旗舰回测 + 全量模拟方案 + 决策历史 (3 GDocs)
- **[`../reports/phase8/`](../reports/phase8/)**: 物理法则重铸 + 14 组参数扫描 (Sweep)
- **[`../reports/phase9/`](../reports/phase9/)**: 非对称 Pearson Loss 证据包 (7 jobs 全败)
- **[`../reports/phase10/`](../reports/phase10/)**: Vanguard V5 + Softmax Portfolio Loss 结果
- **[`../reports/audits_and_insights/`](../reports/audits_and_insights/)**: Gemini 审计 + 架构师 GDoc 精选 ([INDEX](../reports/audits_and_insights/INDEX.md))
- **[`../reports/general/`](../reports/general/)**: Epiplexity 理论文档

## Engineering & Infrastructure
- **[`HARDWARE_TOPOLOGY.md`](./HARDWARE_TOPOLOGY.md)**: Physical nodes (omega-vm, linux1, windows1, mac), IPs, SSH routes
- **[`GCP_PRICING_REFERENCE.md`](./GCP_PRICING_REFERENCE.md)**: GCP 计费参考 (Vertex AI / GCS / Nearline)
- **[`ETL_ENGINEERING_LESSONS.md`](./ETL_ENGINEERING_LESSONS.md)**: OOM deadlocks, cgroup CPU throttling, Python anti-patterns

## Training & Backtest Scripts
| Script | Purpose | Usage |
|--------|---------|-------|
| [`../train.py`](../train.py) | Training loop (Softmax Portfolio Loss) | `python3 train.py --shard_dir ... --epochs 20` |
| [`../tools/phase7_inference.py`](../tools/phase7_inference.py) | Full inference → predictions + z_sparsity parquet | `python3 tools/phase7_inference.py --checkpoint ... --shard_dir ...` |
| [`../tools/phase7_simulate.py`](../tools/phase7_simulate.py) | T+1 overnight swing backtest simulator | `python3 tools/phase7_simulate.py --predictions ... --cost_bp 25` |
| [`../backtest_5a.py`](../backtest_5a.py) | Phase 5a spread backtest | `python3 backtest_5a.py ...` |

## Historical / Early Phase (参考价值，不再更新)
- **[`EXPERIMENTAL_DESIGN_AND_ROADMAP.md`](./EXPERIMENTAL_DESIGN_AND_ROADMAP.md)**: Phase 2-4 物理常数推导 + 成功准则 (Phase 7+ 后已演进)
- **[`V3_SMOKE_TEST_PLAN.md`](./V3_SMOKE_TEST_PLAN.md)**: V3 shard 验证计划 (已完成)
- **[`PHASE3_V15_TRAINING_REPORT.md`](./PHASE3_V15_TRAINING_REPORT.md)**: Phase 3 报告副本 (canonical 版本在 `reports/phase3/`)
- **[`agent_manuals.md`](./agent_manuals.md)**: Harness V1 操作手册 (已被 CLAUDE.md + harness_v2_spec 取代，保留供参考)
- **[`claude_code_blueprint.md`](./claude_code_blueprint.md)**: Harness V1 蓝图 (已被 CLAUDE.md 取代，保留供参考)

## Workflow Automation

### Hooks（自动质量门禁，`.claude/hooks/`）
| Hook | 触发 | 功能 |
|------|------|------|
| [`block-destructive.sh`](../.claude/hooks/block-destructive.sh) | Bash 执行前 | 拦截 rm -rf、force push、物理常数修改 |
| [`post-edit-axiom-check.sh`](../.claude/hooks/post-edit-axiom-check.sh) | Edit/Write 后 | 核心文件变更时自动公理检查 |
| [`stop-guard.sh`](../.claude/hooks/stop-guard.sh) | 回复结束时 | 提醒未提交的核心变更 |

### Skills（一键工作流，`.claude/skills/`）
| 命令 | 功能 |
|------|------|
| `/architect-ingest` | 架构师指令摄取 + 公理影响检测 + spec 更新 |
| `/dev-cycle` | 九阶段开发周期（Plan→Audit→Fix→Code→Audit→Fix→Axiom→**ExternalAudit**→Summary） |
| `/deploy-cycle` | 六阶段部署周期（Pre-flight→Axiom→Health→Deploy→Verify→Document） |
| `/axiom-audit` | 三层公理审计（omega_axioms.py + Codex recursive + Gemini 数学推理） |
| `/pre-flight` | 部署前 9 项预检 |
| `/node-health-check` | 集群健康巡检 |

### Agents（智能委托，`.claude/agents/`）
| Agent | 模型 | 职责 |
|-------|------|------|
| `recursive-auditor` | opus | 独立数学审计（只读） |
| `architect-liaison` | opus | 架构师指令生命周期 + 公理影响检测 |
| `infra-scout` | haiku | 快速集群健康检查 |
| `deployment-guard` | sonnet | 部署门禁（任一失败→NO-GO） |

### External Audit Tools（独立交叉验证）

防止 AI 自测自验 (Bitter Lesson #7)，使用外部 LLM 进行独立审计：

| 工具 | 用途 | 调用方式 |
|------|------|----------|
| **Codex** (GPT 5.4 xhigh) | Spec↔Code recursive alignment audit | `codex exec --full-auto "<prompt>"` |
| **Gemini** | 纯数学推理审计（公式、量纲、梯度） | `cat <file> \| gemini -p "<prompt>"` |
| **gdocs** | 读取架构师 Google Docs 原文 | `gdocs list` / `gdocs read <doc_id>` |

**触发规则**:
- Codex: 每次修改 spec/核心代码/ETL/Loader 后必须运行
- Gemini: 仅在涉及数学公式、物理常数、损失函数时运行
- gdocs: 摄取架构师指令时用于获取原文

### Config
- [`.claude/settings.json`](../.claude/settings.json) — 项目级 hooks 配置（提交到 git）
- `.claude/settings.local.json` — 本地权限（不提交）
