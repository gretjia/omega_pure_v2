# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-18 (Wednesday) - **STATUS: WORKFLOW AUTOMATION COMPLETE**

## 1. CURRENT STATUS: Workflow Automation Deployed

**All ETL and Topo-Forge processes remain HALTED.** Math core code is **frozen**.

The Claude CLI environment restructuring and workflow automation are **complete**. Three-layer automation architecture (Hooks + Skills + Agents) deployed and audited.

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

### What was done in session 2 (2026-03-18, workflow automation)

三层工作流自动化架构，9 个文件操作（7 创建 + 1 更新 + 1 目录）：

12. **3 Hooks** (`.claude/hooks/`, `.claude/settings.json`):
    - `block-destructive.sh` — PreToolUse: 拦截 `rm -rf`、`git push --force`、`git reset --hard`、物理常数修改
    - `post-edit-axiom-check.sh` — PostToolUse: 编辑核心文件后自动运行 `omega_axioms.py`
    - `stop-guard.sh` — Stop: 提醒未提交的核心文件变更（仅提醒，不阻止）

13. **3 New Skills** (`.claude/skills/`):
    - `/architect-ingest` — 架构师指令摄取 + 三级公理影响检测（NONE / UPDATE REQUIRED / VIOLATION）
    - `/dev-cycle` — 八阶段开发周期自动编排（Plan→Audit→Fix→Code→Audit→Fix→Axiom→Summary）
    - `/deploy-cycle` — 六阶段部署周期自动编排（Pre-flight→Axiom→Health→Deploy→Verify→Document）

14. **Agent update** — `architect-liaison.md` 新增公理影响检测职责和三级评级输出

15. **Agent manual** — `handover/agent_manuals.md` 新 agent 完整上手指南

### Recursive audit result (session 1)
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
│   ├── agent_manuals.md               # AI Agent 完整操作手册
│   ├── HARDWARE_TOPOLOGY.md           # Nodes, IPs, SSH routes
│   ├── ETL_ENGINEERING_LESSONS.md     # OOM, cgroup, Python traps
│   ├── EXPERIMENTAL_DESIGN_AND_ROADMAP.md  # Constants derivation
│   └── V3_SMOKE_TEST_PLAN.md         # V3 validation plan
├── tools/
│   ├── omega_etl_v3_topo_forge.py     # V3 ETL (halted)
│   └── empirical_calibration.py       # Constants calibration
├── .claude/
│   ├── settings.json                  # Project hooks config (committed)
│   ├── settings.local.json            # Local permissions (not in git)
│   ├── hooks/
│   │   ├── block-destructive.sh       # PreToolUse: block dangerous commands
│   │   ├── post-edit-axiom-check.sh   # PostToolUse: auto axiom check
│   │   └── stop-guard.sh             # Stop: warn uncommitted core changes
│   ├── skills/
│   │   ├── architect-ingest/SKILL.md  # /architect-ingest (+ axiom impact)
│   │   ├── dev-cycle/SKILL.md         # /dev-cycle (8-stage)
│   │   ├── deploy-cycle/SKILL.md      # /deploy-cycle (6-stage)
│   │   ├── axiom-audit/SKILL.md       # /axiom-audit
│   │   ├── pre-flight/SKILL.md        # /pre-flight
│   │   └── node-health-check/SKILL.md # /node-health-check
│   └── agents/
│       ├── recursive-auditor.md       # Math audit (opus, read-only)
│       ├── architect-liaison.md       # Directive lifecycle + axiom detection (opus)
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

## 7. SESSION 3: 架构师 Spec vs 代码递归审计 (2026-03-18)

来源：架构师 3 份 Google Docs（Doc id.1 数学验证 / Doc id.2 工程审计 / Doc id.3 修复意见）

### 审计发现 & 修复状态

| # | 严重度 | 问题 | 文件 | 状态 |
|---|--------|------|------|------|
| Fix 1 | CRITICAL | V3 ETL 缺失 fcntl.LOCK_EX 单实例锁 | omega_etl_v3_topo_forge.py | FIXED |
| Fix 2 | CRITICAL | sigma_d 全 1 假值导致 SRL 反演失真 | omega_webdataset_loader.py | FIXED |
| Fix 3 | MEDIUM | targeted 模式 pq.read_table() 全量加载 | omega_etl_v3_topo_forge.py | FIXED |
| Fix 4 | MEDIUM | 4 个 V2 遗留文件与 V3 不兼容 | tools/ (4 files) | FIXED (git rm) |
| Fix 5 | LOW | omega_axioms.py 缺少运行时张量形状验证 | omega_axioms.py | FIXED |

### 已确认对齐的模块
- omega_epiplexity_plus_core.py — 95% 对齐，数学核心已封存不修改
- architect/current_spec.yaml — 100% 对齐，无需修改

## 8. NEXT STEPS
1. ~~Complete Claude CLI environment restructuring~~ **DONE**
2. ~~Run axiom audit~~ **DONE — PASSED**
3. ~~Recursive audit of all files~~ **DONE — PASSED**
4. ~~Workflow automation (hooks + skills + agents)~~ **DONE — AUDITED**
5. ~~Agent manual (handover/agent_manuals.md)~~ **DONE**
6. ~~架构师 Spec vs 代码递归审计~~ **DONE — 5 fixes applied**
7. Restart Claude CLI, verify hooks + skills work in new session
8. Re-evaluate V3 ETL strategy with architect
9. If V3 proceeds: multi-process Topo-Forge rewrite for linux1 (break the single-threaded bottleneck)
10. GCS sync (`gsutil -m rsync`) and Vertex AI HPO when sufficient data available

## 8. CRITICAL RULES FOR NEXT AGENT
1. **Read `CLAUDE.md` first** — it's auto-loaded but understand the rules
2. **Read `VIA_NEGATIVA.md`** — know what NOT to do before doing anything
3. **Do not modify `omega_epiplexity_plus_core.py`** unless architect explicitly authorizes
4. **Do not modify Layer 1 constants** (δ=0.5, c=0.842) — ever
5. **All destructive operations require user confirmation** — no exceptions
6. **Run `/axiom-audit` after any math-related code change**
7. **Run `/pre-flight` before any remote deployment**
8. **Architecture changes go through `architect-liaison` agent** → spec update → user confirm
