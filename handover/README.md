# Omega Pure Handover Knowledge Base

Critical handover state, architectural documentation, and engineering post-mortems.

## Start Here
- **[`LATEST.md`](./LATEST.md)**: Single Source of Truth — current status, file map, next steps, rules for next agent
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

## Claude CLI Tools
- **Skills**: `/node-health-check`, `/pre-flight`, `/axiom-audit`
- **Agents**: recursive-auditor (opus), architect-liaison (opus), infra-scout (haiku), deployment-guard (sonnet)
- Config: `.claude/skills/`, `.claude/agents/`, `.claude/settings.local.json` (local only)
