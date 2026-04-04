# OMEGA Meta-Karpathy Harness — 索引与架构全景

> 本目录是 OMEGA Living Harness 的**溯源与对齐中心**。
> 包含学术灵感源（Meta-Harness 论文）、工程灵感源（Karpathy autoresearch）、
> 以及本项目 harness 的完整架构索引。
> 最高指导哲学见 → [`ALIGNMENT.md`](ALIGNMENT.md)

---

## 目录结构

```
meta_karpathy_harness/
├── README.md                          ← 你在这里（索引 + 架构全景）
├── ALIGNMENT.md                       ← 最高指导哲学（所有行动对齐此文档）
├── arxiv_meta_harness.md              ← MIT Meta-Harness 论文归档
├── karpathy_autoresearch.md           ← Karpathy autoresearch 归档
└── _source_autoresearch/              ← autoresearch 完整 git clone
    ├── program.md                     ← Agent 指令原文
    ├── train.py                       ← 被 agent 修改的单文件
    ├── prepare.py                     ← 固定评估基准
    └── ...
```

---

## 灵感谱系

```
Taleb《反脆弱》(2012)        Karpathy autoresearch (2026.03)
    │                              │
    │ "每次打击让系统变强"           │ "propose → evaluate → keep/discard → LOOP"
    │                              │ "program.md = the real innovation space"
    │                              │
    └──────────┬───────────────────┘
               │
    MIT Meta-Harness (2026.03, arxiv 2603.28052v1)
               │
               │ "Raw traces >> summaries (+15分)"
               │ "Filesystem-as-memory, selective grep"
               │ "Causal reasoning from execution traces"
               │ "Code-space search > prompt-space search"
               │
               ▼
    ┌─────────────────────────────────────┐
    │     OMEGA LIVING HARNESS V3         │
    │                                     │
    │  三层架构:                           │
    │  记忆层 → 执法层 → 进化层            │
    │                                     │
    │  Taleb:  失败 → 新规则 → 更强        │
    │  Karpathy: keep/discard loop        │
    │  Meta-Harness: raw traces + grep    │
    └─────────────────────────────────────┘
```

---

## OMEGA Harness 完整组件索引

### Layer 1: 记忆层 (Memory) — "原始诊断经验"

Meta-Harness 证明: raw traces 比 summaries 高 15 分。我们的记忆层保留完整上下文。

| 组件 | 路径 | 角色 | 灵感源 |
|------|------|------|--------|
| **Trace Vault** | `incidents/C-xxx_*/` | 完整失败上下文 (meta/trace/root_cause/resolution) | Meta-Harness filesystem |
| **Incident Index** | `incidents/INDEX.yaml` | 事件索引 + enforcement 状态 | Meta-Harness score files |
| **OMEGA LESSONS** | `OMEGA_LESSONS.md` | 压缩索引 (≤2行/条, 64 lessons) | — (human-readable index) |
| **Enforcement Log** | `rules/enforcement.log` | 规则触发审计轨迹 (TSV) | Karpathy results.tsv |
| **Session Errors** | `logs/session_errors.jsonl` | 实时错误捕获 | Karpathy "run.log" |
| **Chain of Custody** | `architect/chain_of_custody.yaml` | 指令全生命周期追踪 | — (pipeline traceability) |
| **Manifest** | `gcp/manifest.jsonl` | Canary/Job 追踪 | Karpathy results.tsv |

### Layer 2: 执法层 (Enforcement) — "可执行 > 可记忆"

Karpathy 原则: program.md 是 skill, 不是文档。我们的规则是 YAML, 不是文字。

| 组件 | 路径 | 角色 | 灵感源 |
|------|------|------|--------|
| **Rule Engine** | `.claude/hooks/rule-engine.sh` | 18 条 YAML 规则动态加载执行 | Meta-Harness code-space search |
| **Active Rules** | `rules/active/R-xxx.yaml` | 数据驱动规则 (block/warn) | Meta-Harness harness variants |
| **Block Destructive** | `.claude/hooks/block-destructive.sh` | 拦截 rm -rf, force push | — (structural safety) |
| **Pre-Deploy Gate** | `.claude/hooks/pre-deploy-gate.sh` | Canary PASS 才允许提交 | Karpathy keep/discard gate |
| **Axiom Check** | `.claude/hooks/post-edit-axiom-check.sh` | 数学核心文件公理验证 | — (physics constraints) |
| **Error Tracker** | `.claude/hooks/post-bash-error-tracker.sh` | 实时错误捕获到 JSONL | Karpathy "redirect to run.log" |
| **Lesson Trigger** | `.claude/hooks/post-lesson-trigger.sh` | 新 C-xxx → 提醒转规则 | Karpathy "log crash status" |
| **Pipeline Gate** | `.claude/hooks/pipeline-quality-gate.sh` | INS 完整性 + Spec DRAFT | — (pipeline quality) |
| **Upload Verify** | `.claude/hooks/post-upload-verify.sh` | GCS 上传后验证非空 | — (Ω1: 只信实测) |
| **Stop Guard** | `.claude/hooks/stop-guard.sh` | Session 结束提醒 | — (session hygiene) |
| **Spec-Code Align** | `tools/spec_code_alignment.py` | C-057 漂移检测 | — (drift prevention) |
| **Axioms Module** | `omega_axioms.py` | 公理断言 (Ω1-Ω6) | Karpathy prepare.py (fixed truth) |

### Layer 3: 进化层 (Evolution) — "propose → evaluate → keep/discard → LOOP"

Karpathy 的 autonomous loop 是线性的 (improve metric)。我们的是双向的 (失败→规则, 规则→评估→退役)。

| 组件 | 路径 | 角色 | 灵感源 |
|------|------|------|--------|
| **Lesson-to-Rule** | `.claude/skills/lesson-to-rule/` | C-xxx → R-yyy 自动转化 | Karpathy "keep improvement" |
| **Harness Reflect** | `.claude/skills/harness-reflect/` | 自评 + 修剪 + 健康分 | Karpathy "discard regression" |
| **Dev Cycle** | `.claude/skills/dev-cycle/` | 11 阶段开发 (含 Pre-mortem) | Karpathy experiment loop |
| **Deploy Cycle** | `.claude/skills/deploy-cycle/` | 9 阶段部署 (含 I/O 策略) | Karpathy "run → evaluate" |
| **Architect Ingest** | `.claude/skills/architect-ingest/` | 指令摄取 + chain of custody | — (directive tracking) |
| **Axiom Audit** | `.claude/skills/axiom-audit/` | 三层审计 (self + Codex + Gemini) | — (Ω5: producer ≠ verifier) |
| **Pre-flight** | `.claude/skills/pre-flight/` | 远程节点 9 项检查 | — (deployment safety) |
| **Node Health** | `.claude/skills/node-health-check/` | 集群节点健康报告 | — (infrastructure) |
| **Handover** | `.claude/skills/handover-update/` | Session 交接文档 | — (session continuity) |

### 执行安全路径 (Wrapper Scripts) — "making the correct path the only easy path"

| 脚本 | 路径 | 编码的教训 |
|------|------|-----------|
| **Safe Upload** | `gcp/safe_upload.sh` | C-012, C-013 (空文件/验证) |
| **Safe Build & Canary** | `gcp/safe_build_and_canary.sh` | C-053, C-058 (Docker 对齐) |
| **Safe Submit** | `gcp/safe_submit.sh` | C-020 (唯一 output_dir) |
| **Gen Inference Config** | `gcp/gen_inference_config.sh` | C-028, C-032, C-039 (硬件+配置) |

---

## 元公理 (不变层)

| # | 公理 | 一句话 | 灵感映射 |
|---|------|--------|----------|
| Ω1 | 只信实测 | 报告必须由命令输出生成 | Meta-Harness: raw traces >> summaries |
| Ω2 | 先量化后行动 | 资源与目的成比例 | Karpathy: fixed time budget |
| Ω3 | 测试=生产 | Canary 必须目标环境 | Karpathy: same metric, same hardware |
| Ω4 | 可执行>可记忆 | 教训固化为脚本/规则 | Karpathy: program.md > documentation |
| Ω5 | 生产者≠验证者 | 外部审计不可删除 | Meta-Harness: evaluator separate from proposer |
| Ω6 | 数据在哪计算在哪 | 大数据不搬运 | — (domain-specific) |

---

## 健康指标 (2026-04-04)

| 指标 | 当前值 | 目标 |
|------|--------|------|
| 总事件数 | 64 (C-001~C-070) | — |
| 可执行规则 | 18 active | — |
| 执法覆盖率 | 23% (15/64 有 trace) | >80% |
| 规则触发总次数 | ~68 | — |
| 旁路率 | <2% | <5% |
| 误报率 | <1% | <5% |
| 从未触发的规则 | 4 (R-011,012,014,015) | 评估退役 |

---

## 生命循环

```
                    ┌──────────────────────┐
                    │   架构师指令 / 新需求  │
                    └──────────┬───────────┘
                               ↓
                    /architect-ingest (摄取)
                               ↓
                    /dev-cycle (11 阶段开发)
                    ├─ Pre-mortem → Plan → Audit
                    ├─ Code → Audit → Axiom
                    └─ External Audit → Summary
                               ↓
                    /deploy-cycle (9 阶段部署)
                    ├─ I/O Strategy → Pre-flight
                    ├─ Build → Canary → Submit
                    └─ Verify → Document
                               ↓
                    ┌──────────┴───────────┐
                    │     成功 / 失败?       │
                    └──────────┬───────────┘
                       ↙              ↘
                   成功                失败
                    ↓                   ↓
              chain_of_custody    OMEGA_LESSONS.md
              stage: deployed     新 C-xxx 条目
                                       ↓
                              /lesson-to-rule
                              C-xxx → R-yyy
                                       ↓
                              rules/active/ 新规则
                                       ↓
                              rule-engine.sh 自动执法
                                       ↓
                              /harness-reflect
                              ├─ 评估规则效果
                              ├─ 修剪无效规则
                              └─ 更新健康分
                                       ↓
                              ┌────────┴────────┐
                              │   系统变得更强    │
                              └─────────────────┘
```

---

## 信任层 (Defense in Depth)

```
┌─────────────────────────────────────────────────┐
│ Layer 3: 文档 (最弱, 需要人记忆)                  │
│  OMEGA_LESSONS.md, directives/, insights/        │
│  → Meta-Harness: "scores + summary = 34.9"       │
└─────────────────────────────────────────────────┘
        ↑ /lesson-to-rule 转化 ↓
┌─────────────────────────────────────────────────┐
│ Layer 2: 自动执法 (中等, 可被旁路)                │
│  rule-engine.sh, hooks/, manifest.jsonl          │
│  → Meta-Harness: "scores + traces = 50.0"        │
└─────────────────────────────────────────────────┘
        ↓ 编码进脚本 ↓
┌─────────────────────────────────────────────────┐
│ Layer 1: 结构约束 (最强, 不可旁路)                │
│  safe_*.sh, omega_axioms.py, /dev-cycle          │
│  → "making the correct path the only easy path"  │
└─────────────────────────────────────────────────┘
```

---

## 与灵感源的关键差异

| 维度 | Karpathy autoresearch | MIT Meta-Harness | **OMEGA Harness** |
|------|----------------------|------------------|-------------------|
| **目标** | 最小化 val_bpb | 最大化 task accuracy | 最小化重复失败 |
| **循环** | 单向 (improve metric) | 单向 (improve harness) | **双向** (失败→规则→评估→退役) |
| **记忆** | results.tsv (只记分数) | filesystem (完整 traces) | **三层** (LESSONS + traces + rules) |
| **评估** | 固定 (prepare.py) | 固定 (benchmark) | **自评** (/harness-reflect 健康分) |
| **搜索空间** | train.py (1 file) | harness code (k proposals) | **YAML rules** (无需改代码) |
| **退出条件** | 人工中断 | 迭代次数 | **规则退役** (无效→存档) |
| **安全** | git reset (revert) | validation set | **三层防御** (hooks + rules + scripts) |
| **外部验证** | — | — | **Ω5 强制** (Codex + Gemini) |
