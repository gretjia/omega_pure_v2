# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-22 — **STATUS: ETL 完成 + 烟测 23/23 PASS — 准备进入 Phase 3 train.py**

## 1. CURRENT STATUS: ETL Complete, Phase 2 Passed

**Full ETL COMPLETE** (743/743 files, 9,958,131 samples, 1,992 shards, 164GB). Phase 2 烟测 23/23 ALL CLEAR. Math core code is **frozen**. 准备进入 Phase 3: train.py.

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
- Linux1: 77 shards (2.1 GB), Windows1: 62 shards (14.9 GB) — verified intact 2026-03-18

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
│   │   ├── node-health-check/SKILL.md # /node-health-check
│   │   └── handover-update/SKILL.md  # /handover-update (session结束强制)
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

## 8. SESSION 4: 双节点远程审计与清理 (2026-03-18)

### V3 Shard 完整性验证
- Linux1: 77 shards (`/omega_pool/wds_shards_v3/`), 解包验证 shape=(160,10,7), float32, 无 NaN/Inf — **PASS**
- Windows1: 62 shards (`D:\Omega_frames\wds_shards_v3\`) — 目录完整存在
- **判定：已生成 shards 可用，无需重新生成**（Session 3 的 5 个代码修复均不影响已输出的 shard 数据）

### 空间回收结果

#### Linux1 — 回收 ~316 GB

| 删除项 | 路径 | 大小 |
|--------|------|------|
| V2 volume clock | `/omega_pool/l1_volume_clock_v2/` | 1.5 GB |
| V1 omega_pure (整个旧 repo + base_matrix_shards) | `/home/zepher/omega_pure/` | 188 GB |
| ETL 临时 framing | `/omega_pool/temp_framing/` | 27 GB |
| 7z 恢复隔离区 | `/omega_pool/7z_recovery/` | 62 GB |
| Gemini 时期 vNext 实验 (8个目录) | `/home/zepher/work/Omega_vNext*/` | 38 GB |
| smoke 测试目录 (3个) | `/omega_pool/smoke_v64*` | 50 MB |
| .whl / tarball / zip / binaries / logs | `/home/zepher/` 下散落文件 | ~0.6 GB |
| __pycache__ | 多处 | <50 MB |

磁盘状态变化:
- `/omega_pool`: 96G → 6.5G used (1%)
- `/home`: 306G → 80G used (3%)

#### Windows1 — 回收 ~1+ TB

| 删除项 | 路径 | 大小 |
|--------|------|------|
| stage2_full 实验 | `D:\Omega_frames\stage2_full_20260307_v643fix\` | 1.28 TB |
| V2 volume clock | `D:\Omega_frames\l1_volume_clock_v2\` | 3.3 GB |
| 旧版本 v50/v52/v61/v62 | `D:\Omega_frames\v50,v52,v61,v62_feature_l2\` | 286 GB |
| ETL 临时 framing | `D:\tmp\framing\` | 128 GB |
| stage2/stage3 实验残留 (10个) | `D:\Omega_frames\stage2_*/stage3_*` | ~16 GB |
| _stage2 中间产物 (4个) | `D:\Omega_frames\_stage2_*` | 6.3 GB |
| 空目录 (13个) | 各处 | 0 |
| network_test exe / logs / bat | `D:\` 下散落文件 | <1 MB |

磁盘状态变化:
- D: 可用空间: ~0.1 TB → **1.14 TB**

### 明确保留的数据

| 路径 | 大小 | 原因 |
|------|------|------|
| `/omega_pool/parquet_data/` | 2.3 TB | 原始 parquet（不可再生） |
| `/omega_pool/raw_7z_archives/` | 2.6 TB | 原始 7z 归档（不可再生） |
| `/omega_pool/wds_shards_v3/` | 2.1 GB | V3 有效产出 |
| `/home/zepher/data/` | 51 GB | 原始行情数据源 |
| `D:\Omega_frames\latest_base_l1\` | 2.2 TB | 原始 L1 tick（不可再生） |
| `D:\Omega_frames\wds_shards_v3\` | 14.9 GB | V3 有效产出 |
| `D:\BaiduNetdiskDownload\` | 192 GB | 用户保留 |
| `D:\work\Omega_vNext\` | ~75 GB | 用户保留 |
| ollama / kernel-guardian / multiagent-oom / codex | 各 <5 GB | 用户保留 |

### 用户讨论决策记录
- `/home/zepher/data/` (51GB) → 保留（原始行情源，非中间产物）
- `D:\Omega_frames\stage2_full_20260307_v643fix` (1.28TB) → 删除（V3 取代）
- `D:\BaiduNetdiskDownload` + `D:\work\Omega_vNext` → 保留
- ollama / kernel-guardian / multiagent-oom / codex → 全部保留

## 9. NEXT STEPS
1. ~~Complete Claude CLI environment restructuring~~ **DONE**
2. ~~Run axiom audit~~ **DONE — PASSED**
3. ~~Recursive audit of all files~~ **DONE — PASSED**
4. ~~Workflow automation (hooks + skills + agents)~~ **DONE — AUDITED**
5. ~~Agent manual (handover/agent_manuals.md)~~ **DONE**
6. ~~架构师 Spec vs 代码递归审计~~ **DONE — 5 fixes applied**
7. ~~双节点远程审计与清理~~ **DONE — Linux1 回收 316GB, Windows1 回收 1+TB**
8. ~~三层审计体系建立~~ **DONE — omega_axioms(37项) + Codex(6/6) + Gemini(6/6)**
9. ~~Phase 0.5/0.6/1A: ETL 多核改造 + batch 优化 + 烟测~~ **DONE — 21/23 PASS**
10. ~~Phase 1B — 全量 ETL~~ **DONE — 9,958,131 samples, 1992 shards, 164GB, 69.7h**
11. ~~Phase 2 — 端到端烟测~~ **DONE — 23/23 ALL CLEAR**
12. **IN PROGRESS**: Phase 3: train.py (Omega-TIB + VolumeBlockInputMasking + FVU)
13. Phase 4-6: HPO → 全量训练 → 回测

## 9. SESSION 5: 三层审计体系 + V3 Pipeline Plan (2026-03-18~19)

### 架构师新指令摄取 (3 份 Google Docs)
- id.4: SRL c 特异性标定 — c 从 Layer 1 永恒降级为 Layer 2 per-stock
- id.5: MAE vs Intent Prediction 裁决 — 正名 Omega-TIB, Target = N+1 VWAP forward return
- id.6: V_D 物理量纲裁决 — 特征维度 7→10, 宏观 V_D/σ_D 广播写入
- 所有原文存档于 `architect/gdocs/id{1..6}_*.md`

### current_spec.yaml 全面重写
- tensor.shape: [B,160,10,7] → **[B,160,10,10]** (新增 ΔP, macro_V_D, macro_σ_D)
- training.target_model: SpatioTemporal2DMAE → **Omega-TIB**
- 新增: target (VWAP forward return), srl_calibration (per-stock c_i), masking 详细参数
- physics.c_tse → physics.c_default (Layer 1 → Layer 2 降级, 用户已批准)

### omega_axioms.py 升级
- YAML 解析器: 2 层 → **任意嵌套深度**
- 检查项: 12 项 → **39 项** (覆盖全 spec)
- c 从 Layer 1 eternal → Layer 2 fallback
- 三重独立审计通过: omega_axioms PASS + Codex PASS + Gemini PASS

### 三层审计体系建立
- **Layer A**: `python3 omega_axioms.py --verbose` (39 项自检)
- **Layer B**: `codex exec` (GPT 5.4 xhigh) — spec↔code recursive alignment
- **Layer C**: `gemini -p` — 纯数学推理审计 (公式/量纲/梯度)
- 已集成到 `/dev-cycle` (Stage 8) 和 `/axiom-audit` (三层结构)

### V3 Pipeline Plan 完成
- 10 阶段: Phase 0 → 0.5 → 0.6 → 1A → 1B → 2 → 3 → 4 → 5 → 6
- Codex 审计 6/6 PASS
- 完整 plan 存档于 `plan/v3_pipeline_plan.md`

## 10. SESSION 6: ETL 多核改造 + 烟测 + 全量部署 (2026-03-19)

### ETL 多核改造 (Phase 1A)
- **batch 优化**: 350M `.as_py()` 调用/文件 → ~44 `to_numpy()` 调用/文件。762s → 235s/文件 (**3.2x 加速**)
- **LOB 预构建**: `[n_rows, 10, 4]` numpy 数组批量提取，O(1) 切片替代逐行 40 次 `.as_py()`
- **PyArrow 过滤**: `pc.is_in()` C 级过滤后再转 numpy，减少 92% 无效行
- **Symbol 级并行**: `--workers N` 支持，round-robin 分区，独立 ShardWriter，自动 shard 合并重编号
- **A 股过滤器**: `_is_a_share()` 排除 3054 个非 A 股代码（债券/ETF/基金/逆回购）

### 烟测结果 (Phase 2 部分)
- 30 只纯 A 股 × 50 个交易日 × 4 workers → **4349 samples / 4 shards**
- 23 项检查: **21 PASS / 1 STOP (采样偏差) / 1 WARNING**
- #17 (ch8/ch9 continuity) STOP 是 20-day rolling warmup 的采样偏差，后期样本验证值正确
- **全链路验证通过**: ETL→WebDataset→Loader→Model forward→MDL Loss→Backward 梯度无 NaN

### 关键 Bug 修复
| Bug | 根因 | 修复 |
|-----|------|------|
| readonly numpy | `to_numpy()` 返回只读 view | `np.array()` 强制 copy |
| WebDataset 键名分割 | `601166.SH` 的 `.` 被当扩展名 | `symbol.replace('.', '_')` |
| VWAP=0 幽灵 bar | 大单 carryover + 零成交 ticks | `vwap_den<=0` 跳过 + carryover 封顶 |
| null symbol → 'nan' | `to_pandas()` 将 null 转 NaN float | 显式 NaN guard |
| loader prefetch_factor | PyTorch≥2.0 num_workers=0 冲突 | 条件设置 |

### Bitter Lesson: Symbol 级并行在单节点上是死路
- 12 workers: 580s/文件 (ETA 120h) — **比单 worker 还慢 2.5x**
- 根因: 每个 worker 读全部文件 → 12× I/O 争抢同一 NVMe
- 单 worker: 235s/文件 (ETA 45h) — CPU 2.5%, I/O <1%, 内存 29GB/61GB
- **结论**: 当前架构最优解 = 单 worker + batch 优化。详见 `VIA_NEGATIVA.md`

### 全量 ETL 状态
- **运行中**: linux1, 单 worker, 743 文件 × 5312 只 A 股
- **启动时间**: 2026-03-19 19:55
- **最后检查**: 2026-03-19 22:46 — 40/743 文件 (5.4%), 513K samples, 121 shards, 8.8GB
- **速度**: 263s/文件 (稳定)
- **ETA**: ~50h (预计 **2026-03-22 周六凌晨** 完成)
- **RAM**: 36GB/61GB (状态机 buffer 在增长，仍安全)
- **进程**: PID 437460, systemd heavy-workload.slice
- **输出**: `/omega_pool/wds_shards_v3_full/`
- **监控**: `ssh linux1-lx "tail -5 /home/zepher/omega_pure_v2/etl_full.log && ps -p 437460 -o %cpu,%mem,etime --no-headers && free -h | head -2"`

## 12. SESSION 7: ETL 断点续传 Hotpatch + Handover Skill (2026-03-20)

### ETL 断点续传 Hotpatch（紧急）
ETL 运行 35h 后，RSS 从 31.2GB 阶梯式跳至 42.2GB（file ~420），剩余仅 6GB。
原代码**零断点续传能力**——OOM 崩溃意味着 30+ 小时归零。

**修改文件**: `tools/omega_etl_v3_topo_forge.py` (+99/-6 行，未提交)

| 新增 | 说明 |
|------|------|
| `_save_checkpoint()` | 原子写入（`.tmp` → `os.replace()`），pickle protocol=4 |
| `_load_checkpoint()` | 加载 checkpoint，无则返回 None |
| `_scan_max_shard()` | glob 扫描最大 shard 编号 |
| `--resume` CLI 参数 | 启用断点续传 |
| `--checkpoint_interval` | 每 N 个文件存盘（默认 50，约 3h 工作量） |

**设计决策**:
- 序列化: pickle protocol=4（原生支持 deque + numpy）
- 原子写入: POSIX `os.replace()` 防崩溃损坏
- 恢复策略: 删除最后一个 shard（可能半写），从断点文件索引续传
- Shard 续编: `wds.ShardWriter(start_shard=N)`

**OOM 恢复命令** (linux1):
```
sudo systemd-run --slice=heavy-workload.slice --uid=1000 \
  python3 tools/omega_etl_v3_topo_forge.py \
  --base_dir /omega_pool/parquet_data/latest_base_l1 \
  --output_dir /omega_pool/wds_shards_v3_full \
  --c_registry /home/zepher/omega_pure_v2/a_share_c_registry.json \
  --file_list /home/zepher/omega_pure_v2/etl_full_filelist.txt \
  --workers 1 --batch_size 100000 --resume
```

### 新增 Skill
- `/handover-update` — 会话结束前强制执行的 handover 更新流程（已创建）

### ⚠ Warnings
1. **ETL 代码改动未提交** — `tools/omega_etl_v3_topo_forge.py` 有 +99/-6 行未 commit
2. **代码未部署到 linux1** — 需 `scp` 到 linux1 后才能用 `--resume` 恢复
3. **RSS 仍在增长** — file ~420 时 42.2GB，后续可能再跳，OOM 风险仍存
4. 本次会话未涉及远程节点操作

## 14. SESSION 8: ETL 完成 + Phase 2 全量烟测通过 (2026-03-22)

### ETL 全量完成
- **完成时间**: 2026-03-22 17:37
- **总耗时**: 69.7 小时 (2.9 天)
- **总样本**: 9,958,131
- **股票数**: 5,312 只 A 股
- **总 ticks**: 78,869M
- **Shards**: 1,992 个 / 164 GB
- **输出路径**: `/omega_pool/wds_shards_v3_full/`
- **RSS 峰值**: 43.1 GB / 61 GB (68.4%) — 稳定未 OOM

### Phase 2 烟测结果: 23/23 ALL CLEAR
| 层级 | 检查项 | 结果 |
|------|--------|------|
| Step 1: Shard 格式 (#1-18) | shape/dtype/NaN/channels/target/c_friction | 18/18 PASS |
| Step 2: Loader (#19-20) | WebDataset → batched tensors | 2/2 PASS |
| Step 3: Model (#21-23) | forward → MDL loss → backward gradients | 3/3 PASS |

关键验证点:
- 张量形状 [B, 160, 10, 10] 正确
- 零 NaN/Inf，159K spread 检查零违规
- 51 只股票有 51 个不同 c_friction（per-stock 标定生效）
- Target 分布: mean=-5 BP, std=216 BP — 健康
- 极端值 -2932 BP 是合法尾部事件（连续跌停），非 bug

### 烟测阈值修复
- #5 Bid_P: `max < 10000` → `max < 10_000_000`（适配厘单位）
- #13 target: `abs < 500` → `abs < 5000`（覆盖连续跌停尾部）

### 断点续传代码已部署
- `tools/omega_etl_v3_topo_forge.py` 已 scp 到 linux1
- `--resume` + `--checkpoint_interval` 可用（本次未触发 OOM，未实际使用）

### 本次会话无新架构洞察

## 15. CRITICAL RULES FOR NEXT AGENT
1. **Read `CLAUDE.md` first** — it's auto-loaded but understand the rules
2. **Read `VIA_NEGATIVA.md`** — know what NOT to do before doing anything
3. **Do not modify `omega_epiplexity_plus_core.py`** unless architect explicitly authorizes
4. **Do not modify Layer 1 constants** (δ=0.5) — ever. Note: c is now Layer 2 (per-stock c_i)
5. **All destructive operations require user confirmation** — no exceptions
6. **Run `/axiom-audit` after any math-related code change** — this now includes Codex + Gemini
7. **Run `/pre-flight` before any remote deployment**
8. **Architecture changes go through `architect-liaison` agent** → spec update → user confirm
9. **Read `plan/v3_pipeline_plan.md`** — current execution roadmap
10. **Read `architect/gdocs/`** — 6 份架构师原文是 source of truth
