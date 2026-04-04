# OMEGA Living Harness — 架构文档

> 灵感来源: MIT Meta-Harness (arxiv 2603.28052v1) + Karpathy autoresearch
> 核心理念: Harness 不是规则手册, 是有生命的神经系统。它观察自己、学习、进化。

---

## 1. 为什么需要 Living Harness

Phase 1-11 累积了 60 条教训 (C-001~C-060), 但:

| 指标 | 升级前 | 升级后 |
|------|--------|--------|
| 有自动执法的教训 | 12 (20%) | 25+ (42%) |
| 同类错误重复发生 | 5 组 | 被规则拦截 |
| 修复类 commit 占比 | 27.7% | 待观测 ↓ |
| INS 信息丢失 | 严重 (只有裁决+理由) | 6 section 必填 |
| Spec-Code 漂移 | 静默 (C-057 跑了 17 job) | 自动检测 |

**根因**: 教训写进文档后就死了。80% 只是文字, 没有变成机器可执行的规则。同类错误反复发生因为没有自动拦截。

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     OMEGA LIVING HARNESS                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 3: 进化层 (Evolution)                             │   │
│  │  /harness-reflect — 自评健康分 + 修剪无效规则            │   │
│  │  /lesson-to-rule — 教训自动转化为规则                    │   │
│  │  chain_of_custody — 管线失败回溯到源头                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 2: 执法层 (Enforcement)                           │   │
│  │  rule-engine.sh — 16+ 条数据驱动规则 (YAML, 动态加载)   │   │
│  │  lesson-enforcer.sh — 5 条遗留硬编码规则 (向后兼容)     │   │
│  │  pipeline-quality-gate.sh — INS 完整性 + Spec DRAFT     │   │
│  │  spec_code_alignment.py — Spec-Code 参数对齐检查         │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 1: 记忆层 (Memory)                                │   │
│  │  incidents/ — Trace Vault (完整失败上下文, 不压缩)       │   │
│  │  OMEGA_LESSONS.md — 人可读经验索引 (≤2 行/条)           │   │
│  │  rules/active/*.yaml — 规则定义 (自描述, 含效果统计)    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  管线神经系统 (Pipeline Nervous System)                   │   │
│  │                                                           │   │
│  │  Directive → INS → Spec(DRAFT) → Audit → Spec(FINAL)    │   │
│  │     → Code → Docker → Deploy → Results                   │   │
│  │                                                           │   │
│  │  每个阶段有质量门禁, 失败可回溯到源头 INS 假设          │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 文件地图

### 3.1 Hook 系统 (自动触发, 用户无感)

| Hook | 触发时机 | 功能 |
|------|----------|------|
| `block-destructive.sh` | PreToolUse (Bash) | 拦截 rm -rf, git push --force 等 |
| `pre-deploy-gate.sh` | PreToolUse (Bash) | Canary PASS 才允许全量提交 |
| `lesson-enforcer.sh` | PreToolUse (Edit/Write) | 5 条硬编码规则 (legacy) |
| `rule-engine.sh` | PreToolUse (Edit/Write) | 16+ 条 YAML 规则 (动态加载) |
| `post-edit-axiom-check.sh` | PostToolUse (Edit/Write) | 数学核心文件改动后自动公理检查 |
| `post-lesson-trigger.sh` | PostToolUse (Edit/Write) | OMEGA_LESSONS 变更后提示 /lesson-to-rule |
| `pipeline-quality-gate.sh` | PostToolUse (Edit/Write) | INS 完整性 + Spec DRAFT + 失败回溯 |
| `post-upload-verify.sh` | PostToolUse (Bash) | GCS 上传后验证文件非空 |
| `stop-guard.sh` | Stop | 提醒未提交代码 + /harness-reflect |

### 3.2 Skill 系统 (用户可调用)

| Skill | 用途 |
|-------|------|
| `/dev-cycle` | 10+1 阶段开发周期 (含 Stage 8.5 Spec-Code 对齐) |
| `/deploy-cycle` | 7 阶段部署周期 (含烟测 + 物理断言) |
| `/architect-ingest` | 指令摄取 (归档 + INS + chain_of_custody) |
| `/axiom-audit` | 三层公理审计 (self + Codex + Gemini) |
| `/lesson-to-rule` | 教训→规则自动转化 + incidents 自动迁移 |
| `/harness-reflect` | 自省循环 (规则效果 + 管线健康 + 健康分) |
| `/pre-flight` | 远程节点部署前检查 |
| `/node-health-check` | 集群节点健康报告 |
| `/handover-update` | 会话交接文档 |

### 3.3 数据文件

| 文件 | 角色 | 维护方式 |
|------|------|----------|
| `OMEGA_LESSONS.md` | 经验索引 (人可读) | Session 结束手动追加 |
| `incidents/` | Trace Vault (机器可读完整上下文) | /lesson-to-rule 自动创建 |
| `incidents/INDEX.yaml` | 事件索引 (enforcement 状态) | /lesson-to-rule 更新 |
| `rules/active/*.yaml` | 执法规则 | /lesson-to-rule 生成, 用户确认 |
| `rules/enforcement.log` | 规则触发日志 | rule-engine.sh 自动写入 |
| `architect/chain_of_custody.yaml` | 管线追踪 | /architect-ingest 创建, 各 skill 推进 |
| `architect/current_spec.yaml` | 架构规范 (DRAFT/FINAL) | /architect-ingest 更新, Stage 8.5 finalize |

---

## 4. 生命循环

### 4.1 日常开发循环

```
架构师指令
  ↓ /architect-ingest
  ├→ 归档 directive (完整, 不压缩)
  ├→ 生成 INS (6 section 必填, pipeline-quality-gate 检查)
  ├→ 更新 spec (标记 [DRAFT])
  └→ 创建 chain_of_custody 条目 (stage: ins_created)

  ↓ /dev-cycle
  ├→ Stage 0: Pre-mortem (读 OMEGA_LESSONS, 列 3 方案)
  ├→ Stage 1-3: Plan + Audit
  ├→ Stage 4-6: Code + Audit
  ├→ Stage 7: Axiom Check
  ├→ Stage 8: External Audit (Codex + Gemini)
  ├→ Stage 8.5: Spec-Code 对齐 (DRAFT→FINAL, 参数校验, 假设验证)
  └→ Stage 9: Summary + Commit

  ↓ /deploy-cycle
  ├→ Pre-flight + Axiom + Node Health
  ├→ safe_build_and_canary.sh (含 Step 1d spec-code alignment)
  ├→ safe_submit.sh (含 canary gate)
  └→ chain_of_custody → stage: deployed
```

### 4.2 失败学习循环

```
训练/部署失败
  ↓ 记录教训到 OMEGA_LESSONS.md (C-xxx)
  ↓ post-lesson-trigger.sh 自动提醒
  ↓ /lesson-to-rule C-xxx
  ├→ 如果没有 incidents/ → 自动创建 trace 目录
  ├→ 分类失败模式 (10 种 pattern)
  ├→ 搜索是否有现有规则覆盖
  ├→ 生成新规则 YAML (或扩展现有规则)
  ├→ 回归测试 (对 trace vault dry-run)
  └→ 用户确认 → 规则激活 → 下次自动拦截

  ↓ pipeline-quality-gate.sh 提醒更新 chain_of_custody
  ↓ 在对应 directive 的 failures 中记录:
  ├→ 哪个 C-xxx
  ├→ 在哪个阶段失败
  ├→ 哪个 INS 假设被违反
  └→ 这信息在 /harness-reflect 中统计
```

### 4.3 自省进化循环

```
/harness-reflect (Session 结束或定期运行)
  ├→ Stage 1: 盘点 (events + rules + log)
  ├→ Stage 2: 缺口分析 (未执法教训 Top 5)
  ├→ Stage 3: 规则效果评分 (trigger/bypass/fp)
  ├→ Stage 4: 模式聚类 (新重复模式?)
  ├→ Stage 5: 修剪 (退休无效规则)
  ├→ Stage 6: 健康分 (enforcement × repeat × fix_ratio)
  ├→ Stage 7: 管线健康 (INS 完整率 + DRAFT 年龄 + 漂移数)
  └→ Stage 8: 行动建议 (最多 5 条)
```

---

## 5. 规则引擎详解

### 5.1 规则格式 (YAML)

```yaml
id: R-008
name: "Block Batch-dimension normalization"
source_incidents: [C-042, C-045]
axiom: "Ω1"
trigger:
  event: PreToolUse
  matcher: "Edit|Write"
  file_glob: "*.py|gcp/*.py"
check:
  type: grep
  pattern: "softmax\\(.*dim\\s*=\\s*0|BatchNorm"
enforcement: block    # block / warn / log
stats:
  times_triggered: 3
  last_triggered: "2026-04-03"
```

### 5.2 当前活跃规则 (16 条)

| ID | 名称 | 级别 | 来源 |
|---|---|---|---|
| R-001 | 大容量 pd-ssd 无 Local SSD | block | C-028/C-040 |
| R-002 | checkpoint_interval 不可为零 | block | C-032 |
| R-003 | device 不可硬编码 CPU | block | C-039 |
| R-004 | delta 物理常数不可修改 | block | Layer 1 |
| R-005 | bash -c 必须传递 $@ | block | C-017 |
| R-006 | window_size 默认值与 spec 同步 | warn | C-037/C-057 |
| R-007 | output_dir 必须唯一 | warn | C-020/C-044 |
| R-008 | Batch 维度归一化绝对禁止 | block | C-042/C-045 |
| R-009 | 废弃变量 TARGET_STD/.squeeze() | warn | C-049/C-050 |
| R-010 | Loss 函数变更触发全栈检查 | warn | C-043/C-051/C-054 |
| R-011 | Docker 必须在代码修复后构建 | warn | C-053/C-058 |
| R-012 | 容器路径假设验证 | warn | C-060 |
| R-013 | ETL 输出单位验证 | warn | C-059 |
| R-014 | 长训练必须 E0-E1 烟测 | warn | C-052 |
| R-015 | Spot checkpoint 先写 /tmp | warn | C-047 |
| R-016 | Spec-Code default 漂移检测 | warn | C-057/C-037 |

### 5.3 添加新规则

无需修改任何代码。只需:
1. 创建 `rules/active/R-xxx_slug.yaml` (遵循 `rules/RULE_SCHEMA.yaml`)
2. rule-engine.sh 下次运行时自动加载

或者使用 `/lesson-to-rule C-xxx` 自动生成。

---

## 6. Trace Vault 详解

### 6.1 目录结构

```
incidents/
├── INDEX.yaml                     # 全局索引
├── INCIDENT_SCHEMA.yaml           # 格式规范
├── C-020_checkpoint_dir_reuse/    # 一个事件 = 一个目录
│   ├── meta.yaml                  # 标签: pattern, axiom, severity, enforcement
│   ├── trace.md                   # 完整执行记录 (命令→输出→错误)
│   ├── root_cause.md              # WHY chain (因果分析)
│   └── resolution.md              # 修复方案 + 执法创建
```

### 6.2 为什么不压缩

MIT Meta-Harness 论文实测:
- Scores Only: 34.6 准确率
- Scores + Summary: 34.9 (摘要几乎无用)
- **Scores + Raw Traces: 50.0** (+15 分)

OMEGA_LESSONS.md 的 ≤2 行格式 = Scores + Summary。Trace Vault = Raw Traces。

Agent 用 grep/read 按需查询完整上下文, 而不是读压缩摘要。

---

## 7. 管线神经系统详解

### 7.1 INS 质量门禁 (6 必填 section)

| Section | 防止的失败 | 教训来源 |
|---------|-----------|----------|
| 裁决 | (基础) | — |
| 理由 | (基础) | — |
| **前提假设** | ETL 单位假设错误 → double-convert | C-059 |
| **被拒绝的替代方案** | 下一个 session 重新提议被否方案 | INS-063 |
| **验证协议** | 诊断未被验证 → ablation 未执行 | C-052 |
| **参数标定来源** | 直觉阈值被当物理常数 | C-055 |
| 影响文件 | (基础) | — |

### 7.2 Spec Draft/Final 两阶段

```
/architect-ingest → spec 字段标记 [DRAFT — pending audit]
/dev-cycle Stage 8 → 外部审计 (Codex + Gemini)
/dev-cycle Stage 8.5 → 审计通过 → 移除 [DRAFT] 标记 → final
```

DRAFT 状态 = "架构师的意图, 但未被验证"
Final 状态 = "经过 Codex + Gemini 审计确认"

### 7.3 Chain of Custody

每个架构师指令在 `architect/chain_of_custody.yaml` 中有一条生命记录:

```yaml
- directive: "2026-04-02_phase12_unshackling_protocol.md"
  stage: deployed          # ingested → ins_created → spec_draft → coded → deployed
  insights: [INS-060, INS-063]
  audit_status: final
  failures:
    - lesson: C-059
      stage_failed: coded
      assumption_violated: "target 是 raw decimal (实际是 BP)"
```

当训练失败时, 从 C-xxx → chain_of_custody → 找到哪个 INS 的哪个假设出错。

---

## 8. 元公理 (不变)

| # | 元公理 | 一句话 |
|---|--------|--------|
| Ω1 | 只信实测 | 报告/ETA 必须由命令输出生成 |
| Ω2 | 先量化后行动 | du -sh / df -h / 带宽实测, 然后才承诺 |
| Ω3 | 测试=生产 | Canary 必须目标环境精确镜像 |
| Ω4 | 可执行 > 可记忆 | 教训固化为脚本/规则, 不只是文档 |
| Ω5 | 生产者 ≠ 验证者 | 外部审计不可删除 |
| Ω6 | 数据在哪计算在哪 | 大数据不搬运 |

---

## 9. 烟测

```bash
# 规则引擎烟测 (26 项, 覆盖 block/warn/exempt/compound/performance)
python3 -m pytest tests/test_harness_v3.py -v

# 已知 bug 回归测试 (8 项)
python3 -m pytest tests/test_known_bugs.py -v

# Spec-Code 对齐检查
python3 tools/spec_code_alignment.py
```

---

## 10. 设计哲学

1. **Karpathy 极简**: 规则引擎核心 = 1 个 bash 脚本 + N 个 YAML 文件。没有框架、没有数据库。
2. **Meta-Harness filesystem-as-memory**: incidents/ 是记忆, 不是日志。Agent 按需 grep, 不全量加载。
3. **Taleb 反脆弱**: 每次失败让系统变强 (新规则), 而不是更脆弱 (更多文档)。
4. **Ω4 到极致**: 如果一个教训只存在于文本, 它就是死的。只有变成 YAML/hook/script 的教训才活着。
5. **人审批, 机执行**: 规则生成自动化, 激活需要人确认。进化但可控。
