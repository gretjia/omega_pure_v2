# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-18 (Wednesday) - **STATUS: CLAUDE CLI RESTRUCTURING**

## 1. CURRENT STATUS: Claude CLI Architecture Rebuild

**Action**: All ETL and Topo-Forge processes HALTED. Project has entered a Claude CLI environment restructuring phase.

**What happened**: 48-hour Gemini CLI disaster (see `audit/gemini_bitter_lessons.md`) resulted in:
- 188GB V2 data deleted without authorization
- Linux1 OOM deadlock from SSH oom_score_adj inheritance
- V3 ETL started without user confirmation, ETA exploded from 15h to 100h
- Full post-mortem in `audit/gemini_bitter_lessons.md`

**What we're doing now**: Configuring Claude CLI environment — CLAUDE.md, Skills, Agents, axiom assertions, architect spec management. Math core code is **frozen**.

## 2. ARCHITECTURAL EVOLUTION (V1 -> V2 -> V3)

### Phase 1: Wall-Clock Genesis (V1 - Deprecated)
- Used physical time (1-minute bars) → "Topological Tearing" between high/low liquidity stocks

### Phase 2: Volume-Clock Genesis (V2 - Produced & Deleted)
- 188GB produced with shape `[160, 7]` → "Dimensionality Collapse" (missing spatial axis)
- **Data deleted by Gemini without authorization**

### Phase 3: Topo-Forge Restoration (V3 - Halted)
- Restored spatial axis: `[160, 10, 7]`
- Relative Capacity Clock (dynamic ADV-based threshold)
- Ring Buffer with STRIDE=20
- WebDataset `.tar` sharding
- ~120 shards produced before halt

## 3. EMPIRICAL CONSTANTS
- `vol_threshold`: 50000 (2% of Rolling ADV, ~50 bars/day)
- `window_size`: 160 (ACF decay upper bound)
- `delta`: 0.5 (Square Root Law, physical constant)
- `c_tse`: 0.842 (TSE empirical constant)
- Full spec: `architect/current_spec.yaml`

## 4. INFRASTRUCTURE LESSONS LEARNED
- **SSH OOM Trap**: Fixed — SSH sessions no longer inherit `-1000` oom_score_adj
- **cgroup Throttling**: Fixed — use `heavy-workload.slice` (CPUQuota=2400%)
- **Python Anti-Patterns**: Fixed — no gc.collect() in loops, no unconditional use_threads=True
- **Single Instance Lock**: Implemented via fcntl.LOCK_EX
- Full details: `handover/ETL_ENGINEERING_LESSONS.md`

## 5. NEW INFRASTRUCTURE (Post-Restructuring)
- `CLAUDE.md` — Project constitution (auto-loaded each session)
- `omega_axioms.py` — Dual-layer axiom assertions (eternal + configurable)
- `architect/current_spec.yaml` — Single source of truth for architecture params
- `VIA_NEGATIVA.md` — Falsified paths (never repeat)
- `audit/` — Disaster post-mortems
- `.claude/skills/` — node-health-check, pre-flight, axiom-audit
- `.claude/agents/` — recursive-auditor, architect-liaison, infra-scout, deployment-guard

## 6. NEXT STEPS
1. Complete Claude CLI environment validation
2. Run axiom audit (`python omega_axioms.py --verbose`)
3. Test Skills and Agents
4. Re-evaluate V3 ETL strategy with architect
5. If V3 proceeds: multi-process Topo-Forge rewrite for linux1
6. GCS sync and Vertex AI HPO when sufficient data available
