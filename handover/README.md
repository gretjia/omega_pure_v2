# Omega Pure Handover Knowledge Base

Critical handover state, architectural documentation, workflow automation, and engineering post-mortems.

## Start Here
- **[`LATEST.md`](./LATEST.md)**: Single Source of Truth — current status, file map, next steps, rules for next agent
- **[`agent_manuals.md`](./agent_manuals.md)**: AI Agent 完整操作手册 — 新 agent 上手指南（工作流、工具链、安全红线）
- **[`../CLAUDE.md`](../CLAUDE.md)**: Project constitution (auto-loaded by Claude CLI every session)
- **[`../VIA_NEGATIVA.md`](../VIA_NEGATIVA.md)**: Falsified paths — what NOT to do (must read before making changes)

## Architecture
- **[`../architect/current_spec.yaml`](../architect/current_spec.yaml)**: Current architecture params (tensor shape, physics constants, ETL config)
- **[`../architect/INDEX.md`](../architect/INDEX.md)**: Architect directive timeline
- **[`../omega_axioms.py`](../omega_axioms.py)**: Dual-layer axiom assertions (`python3 omega_axioms.py --verbose`)

## Engineering & Infrastructure
- **[`HARDWARE_TOPOLOGY.md`](./HARDWARE_TOPOLOGY.md)**: Physical nodes (omega-vm, linux1, windows1, mac), IPs, SSH routes
- **[`ETL_ENGINEERING_LESSONS.md`](./ETL_ENGINEERING_LESSONS.md)**: OOM deadlocks, cgroup CPU throttling, Python anti-patterns
- **[`../audit/gemini_bitter_lessons.md`](../audit/gemini_bitter_lessons.md)**: Gemini CLI 48h disaster post-mortem

## Methodology & Roadmap
- **[`EXPERIMENTAL_DESIGN_AND_ROADMAP.md`](./EXPERIMENTAL_DESIGN_AND_ROADMAP.md)**: Derivation of physical constants (vol_threshold, window_size) and Phase 2-4 success criteria
- **[`V3_SMOKE_TEST_PLAN.md`](./V3_SMOKE_TEST_PLAN.md)**: V3 shard validation and Vertex AI ignition plan

## Workflow Automation
- **[`agent_manuals.md`](./agent_manuals.md)**: 完整操作手册（三层自动化架构、标准工作流、故障排除）

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
| `/dev-cycle` | 八阶段开发周期（Plan→Audit→Fix→Code→Audit→Fix→Axiom→Summary） |
| `/deploy-cycle` | 六阶段部署周期（Pre-flight→Axiom→Health→Deploy→Verify→Document） |
| `/axiom-audit` | 公理完整性验证 |
| `/pre-flight` | 部署前 9 项预检 |
| `/node-health-check` | 集群健康巡检 |

### Agents（智能委托，`.claude/agents/`）
| Agent | 模型 | 职责 |
|-------|------|------|
| `recursive-auditor` | opus | 独立数学审计（只读） |
| `architect-liaison` | opus | 架构师指令生命周期 + 公理影响检测 |
| `infra-scout` | haiku | 快速集群健康检查 |
| `deployment-guard` | sonnet | 部署门禁（任一失败→NO-GO） |

### Config
- [`.claude/settings.json`](../.claude/settings.json) — 项目级 hooks 配置（提交到 git）
- `.claude/settings.local.json` — 本地权限（不提交）
