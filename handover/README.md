# Omega Pure Handover Knowledge Base

This directory contains the critical handover state, architectural documentation, and engineering post-mortems for the Omega Pure project.

## Core Documents (Must Read First)
- **[`LATEST.md`](./LATEST.md)**: The Single Source of Truth — current project phase, status, next steps
- **[`../CLAUDE.md`](../CLAUDE.md)**: Project constitution (auto-loaded by Claude CLI)

## Engineering & Infrastructure
- **[`HARDWARE_TOPOLOGY.md`](./HARDWARE_TOPOLOGY.md)**: Physical nodes and SSH routing
- **[`ETL_ENGINEERING_LESSONS.md`](./ETL_ENGINEERING_LESSONS.md)**: OOM deadlocks, CPU throttling, Python anti-patterns

## Methodology
- **[`EXPERIMENTAL_DESIGN_AND_ROADMAP.md`](./EXPERIMENTAL_DESIGN_AND_ROADMAP.md)**: Derivation of physical constants and roadmap
- **[`V3_SMOKE_TEST_PLAN.md`](./V3_SMOKE_TEST_PLAN.md)**: V3 shard validation plan

## Related Top-Level Files
- **[`../VIA_NEGATIVA.md`](../VIA_NEGATIVA.md)**: Falsified paths — what NOT to do
- **[`../audit/`](../audit/)**: Disaster post-mortems (Gemini CLI 48h incident)
- **[`../architect/`](../architect/)**: Architecture specs and directives
- **[`../omega_axioms.py`](../omega_axioms.py)**: Axiom assertion module
