# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-18 (Wednesday) - **STATUS: CLAUDE CLI RESTRUCTURING COMPLETE**

## 1. CURRENT STATUS: Claude CLI Environment Ready

**All ETL and Topo-Forge processes remain HALTED.** Math core code is **frozen**.

The Claude CLI environment restructuring is **complete**. All infrastructure files have been created, audited, committed, and pushed to `origin/main`.

### What happened before this session
48-hour Gemini CLI disaster (full post-mortem: `audit/gemini_bitter_lessons.md`):
- 188GB V2 data deleted without authorization
- Linux1 OOM deadlock from SSH oom_score_adj=-1000 inheritance
- V3 ETL started without user confirmation, ETA exploded from 15h→100h
- AI self-tested its own code (self-consistency masked correctness)

### What was done in this session (2026-03-18)
Complete Claude CLI architecture rebuild — 18 files, 2 commits:

1. **`CLAUDE.md`** — Project constitution (~49 rules). Auto-loaded every session. Covers physics axioms, destructive operation red lines, deployment checklists, engineering rules, hardware topology, user context.

2. **`omega_axioms.py`** — Dual-layer axiom assertion module.
   - Layer 1 (eternal): δ=0.5, c=0.842, POWER_INVERSE=2.0 — hardcoded, AI cannot modify
   - Layer 2 (evolvable): reads tensor shape, ETL params from `architect/current_spec.yaml`
   - `python3 omega_axioms.py --verbose` runs full self-check — **AUDIT PASSED**

3. **`architect/current_spec.yaml`** — Single source of truth for architecture params. Agents and axiom checker read from this. Architecture upgrades only need to update this YAML.

4. **`architect/INDEX.md`** + **`architect/directives/`** — Architect directive archive. One directive on record (V3 spatial restoration).

5. **`VIA_NEGATIVA.md`** — 10 falsified paths with root cause analysis. Permanent record of what NOT to do.

6. **`audit/gemini_bitter_lessons.md`** — Complete 48h disaster post-mortem with timestamps, root cause chains, and 10-point Bitter Lessons checklist.

7. **`.claudeignore`** — Excludes *.parquet, *.tar, *.pth, *.7z etc. Preserves tools/, handover/, audit/, architect/.

8. **`.mcp.json`** — Empty (intentional). MCP not needed now; Claude native Bash+SSH covers all remote ops.

9. **3 Skills** (`.claude/skills/`):
   - `/node-health-check` — SSH to all nodes, check disk/memory/processes/cgroup
   - `/pre-flight` — GO/NO-GO deployment gate (9 checks)
   - `/axiom-audit` — Run omega_axioms.py, verify physics constants and spec alignment

10. **4 Agents** (`.claude/agents/`):
    - `recursive-auditor` (opus) — Independent math verification, reads spec not hardcoded values, read-only
    - `architect-liaison` (opus) — Ingest architect directives, archive, propose spec updates (requires user confirm)
    - `infra-scout` (haiku) — Fast cluster health check
    - `deployment-guard` (sonnet) — Pre-deployment gate, blocks on any failure

11. **`.claude/settings.local.json`** — Expanded permissions for SSH, git, pip, system diagnostics (not committed — global gitignore excludes it, stays local)

### Recursive audit result
All 19 files audited for cross-file consistency:
- Physics constants aligned across CLAUDE.md ↔ omega_axioms.py ↔ current_spec.yaml ↔ core code
- Tensor shape [B, 160, 10, 7] consistent everywhere
- Architect directive chain complete
- Bitter Lessons encoded into CLAUDE.md rules and agent/skill constraints
- **Verdict: PASS**

## 2. ARCHITECTURAL EVOLUTION (V1 → V2 → V3)

### Phase 1: Wall-Clock Genesis (V1 - Deprecated)
- Used physical time (1-minute bars) → "Topological Tearing" between high/low liquidity stocks

### Phase 2: Volume-Clock Genesis (V2 - Produced & Deleted)
- 188GB produced with shape `[160, 7]` → "Dimensionality Collapse" (missing spatial axis)
- Data deleted by Gemini without authorization

### Phase 3: Topo-Forge Restoration (V3 - Halted)
- Restored spatial axis: `[160, 10, 7]`
- Relative Capacity Clock (dynamic ADV-based threshold)
- Ring Buffer with STRIDE=20
- WebDataset `.tar` sharding
- ~120 shards produced before halt

## 3. EMPIRICAL CONSTANTS (frozen)
- `delta`: 0.5 — Square Root Law exponent (Layer 1 eternal constant)
- `c_tse`: 0.842 — TSE empirical constant (Layer 1 eternal constant)
- `vol_threshold`: 50000 — 2% of Rolling ADV, ~50 bars/day
- `window_size`: 160 — ACF decay upper bound
- `stride`: 20 — Ring buffer step
- `adv_fraction`: 0.02 — Dynamic threshold = ADV × this
- Canonical source: `architect/current_spec.yaml`

## 4. INFRASTRUCTURE LESSONS (from Gemini disaster)
- **SSH OOM Trap**: Fixed — sessions no longer inherit oom_score_adj=-1000
- **cgroup Throttling**: Fixed — use `heavy-workload.slice` (CPUQuota=2400%)
- **Python Anti-Patterns**: Fixed — no gc.collect() in loops, no unconditional use_threads=True
- **Single Instance Lock**: Implemented via fcntl.LOCK_EX
- **Destructive ops**: Must have user confirmation (CLAUDE.md rules #10-15)
- **AI self-testing**: Prohibited — audits must be independent of code author
- Full details: `handover/ETL_ENGINEERING_LESSONS.md`, `audit/gemini_bitter_lessons.md`

## 5. FILE MAP (for next agent)

```
omega_pure_v2/
├── CLAUDE.md                          # Project constitution (auto-loaded)
├── VIA_NEGATIVA.md                    # Falsified paths — never repeat
├── omega_axioms.py                    # Dual-layer axiom assertions
├── omega_epiplexity_plus_core.py      # Math core (FROZEN — do not modify)
├── omega_webdataset_loader.py         # WebDataset loader
├── .claudeignore                      # Context isolation rules
├── .mcp.json                          # MCP config (empty, intentional)
├── architect/
│   ├── current_spec.yaml              # Architecture spec (single source of truth)
│   ├── INDEX.md                       # Directive timeline
│   └── directives/                    # Architect directive archive
├── audit/
│   └── gemini_bitter_lessons.md       # 48h disaster post-mortem
├── handover/
│   ├── LATEST.md                      # ← YOU ARE HERE
│   ├── README.md                      # Navigation guide
│   ├── HARDWARE_TOPOLOGY.md           # Nodes, IPs, SSH routes
│   ├── ETL_ENGINEERING_LESSONS.md     # OOM, cgroup, Python traps
│   ├── EXPERIMENTAL_DESIGN_AND_ROADMAP.md  # Constants derivation
│   └── V3_SMOKE_TEST_PLAN.md         # V3 validation plan
├── tools/
│   ├── omega_etl_v3_topo_forge.py     # V3 ETL (halted)
│   ├── etl_lazy_sink_linux_optimized.py  # V2 ETL (deprecated, kept for reference)
│   ├── etl_lazy_sink.py               # V2 ETL original
│   ├── empirical_calibration.py       # Constants calibration
│   ├── convert_to_webdataset.py       # WebDataset converter
│   └── smoke_test_v2_shards.py        # V2 shard tester
├── .claude/
│   ├── settings.local.json            # Local permissions (not in git)
│   ├── skills/
│   │   ├── node-health-check/SKILL.md # /node-health-check
│   │   ├── pre-flight/SKILL.md        # /pre-flight
│   │   └── axiom-audit/SKILL.md       # /axiom-audit
│   └── agents/
│       ├── recursive-auditor.md       # Math audit (opus, read-only)
│       ├── architect-liaison.md       # Directive lifecycle (opus)
│       ├── infra-scout.md             # Cluster health (haiku)
│       └── deployment-guard.md        # Deploy gate (sonnet)
└── README.md                          # Project overview
```

## 6. HARDWARE TOPOLOGY (quick reference)
- **omega-vm** (current node): GCP US, 16GB RAM, no GPU — control plane
- **linux1-lx**: AMD AI Max 395, 128GB, 4TB+8TB SSD — heavy compute
- **windows1-w1**: AMD AI Max 395, 128GB, 4TB+8TB SSD — heavy compute
- **zephrymac-studio**: Apple M4, 32GB — architect console
- SSH routes: `ssh linux1-lx`, `ssh windows1-w1`, `ssh zephrymac-studio`
- Full topology: `handover/HARDWARE_TOPOLOGY.md`

## 7. NEXT STEPS
1. ~~Complete Claude CLI environment restructuring~~ **DONE**
2. ~~Run axiom audit~~ **DONE — PASSED**
3. ~~Recursive audit of all files~~ **DONE — PASSED**
4. Restart Claude CLI, verify `/axiom-audit` skill works
5. Re-evaluate V3 ETL strategy with architect
6. If V3 proceeds: multi-process Topo-Forge rewrite for linux1 (break the single-threaded bottleneck)
7. GCS sync (`gsutil -m rsync`) and Vertex AI HPO when sufficient data available

## 8. CRITICAL RULES FOR NEXT AGENT
1. **Read `CLAUDE.md` first** — it's auto-loaded but understand the rules
2. **Read `VIA_NEGATIVA.md`** — know what NOT to do before doing anything
3. **Do not modify `omega_epiplexity_plus_core.py`** unless architect explicitly authorizes
4. **Do not modify Layer 1 constants** (δ=0.5, c=0.842) — ever
5. **All destructive operations require user confirmation** — no exceptions
6. **Run `/axiom-audit` after any math-related code change**
7. **Run `/pre-flight` before any remote deployment**
8. **Architecture changes go through `architect-liaison` agent** → spec update → user confirm
