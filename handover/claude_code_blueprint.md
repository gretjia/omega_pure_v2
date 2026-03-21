# Claude Code 三层自动化治理蓝图

> 从 Omega Pure 项目（48小时 AI 灾难 → 三层治理体系重建）中提炼的通用模板。
> 适用于任何需要 AI 安全护栏的软件工程项目。

---

## 目录

1. [Quick Start（5分钟上手）](#1-quick-start5分钟上手)
2. [设计哲学](#2-设计哲学)
3. [CLAUDE.md 模板（项目宪法）](#3-claudemd-模板项目宪法)
4. [Hook 层模板](#4-hook-层模板)
5. [Skill 层模板](#5-skill-层模板)
6. [Agent 层模板](#6-agent-层模板)
7. [Axiom-as-Code 模板](#7-axiom-as-code-模板)
8. [上下文管理模板](#8-上下文管理模板)
9. [Settings 模板](#9-settings-模板)
10. [Per-Project Decision Checklist](#10-per-project-decision-checklist)

---

## 1. Quick Start（5分钟上手）

最小可用配置只需 3 个文件：

### Step 1: CLAUDE.md（项目宪法）

在项目根目录创建 `CLAUDE.md`，Claude Code 每次会话自动加载：

```markdown
# [PROJECT_NAME] — 项目宪法

## WHAT: 项目定义
[CUSTOMIZE] 一句话描述你的项目。

## WHY: 核心哲学
[CUSTOMIZE] 你的项目为什么存在？遵循什么原则？

## HOW: 不可违反的规则
1. [CUSTOMIZE] 永远不可修改的常量或约束
2. [CUSTOMIZE] 破坏性操作（删除数据、推送代码）必须人工确认
3. [CUSTOMIZE] 关键文件列表
```

### Step 2: block-destructive.sh（1个 Hook）

```bash
mkdir -p .claude/hooks
cat > .claude/hooks/block-destructive.sh << 'HOOKEOF'
#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || echo "")

[ -z "$COMMAND" ] && exit 0

# Block rm -rf on dangerous paths
echo "$COMMAND" | grep -qE 'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|--force\s+)*(\/|~|\.\.|\/home|\/root|\*|\.claude)' && \
    { echo "BLOCKED: Destructive rm command: $COMMAND" >&2; exit 2; }

# Block git push --force
echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force|git\s+push\s+-f' && \
    { echo "BLOCKED: Force push detected: $COMMAND" >&2; exit 2; }

# Block git reset --hard
echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard' && \
    { echo "BLOCKED: git reset --hard: $COMMAND" >&2; exit 2; }

exit 0
HOOKEOF
chmod +x .claude/hooks/block-destructive.sh
```

注册 Hook：

```bash
mkdir -p .claude
cat > .claude/settings.json << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-destructive.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
EOF
```

### Step 3: .claudeignore（上下文隔离）

```
# Binary and large files
*.parquet
*.tar
*.pth
*.7z
*.zip
*.gz
*.npy

# Build artifacts
__pycache__/
*.pyc
node_modules/
.git/
```

**Done.** 这三个文件给你：宪法约束 + 危险命令拦截 + 上下文隔离。

---

## 2. 设计哲学

从 Omega 项目的一次 48 小时 AI 灾难（188GB 数据被删、OOM 内核死锁、AI 自测自验掩盖错误）中提炼出 5 条通用原则：

| 原则 | 说明 | Omega 教训 |
|------|------|-----------|
| **Defense-in-depth** | Hook(秒级拦截) → Skill(流程编排) → Agent(智能委派)，三层递进 | 单层防护不够：AI 绕过了口头规则但无法绕过 exit code 2 |
| **Human-in-the-loop** | 不可逆操作必须人工确认。接收指令 ≠ 授权执行 | AI 收到架构师指令后直接删除 188GB 数据，未经用户确认 |
| **Immutable vs Evolvable** | Layer 1(永恒常量，硬编码) vs Layer 2(可演进，从 YAML 读取) | 物理常数被 AI "优化"为可学习参数，导致模型退化 |
| **Independent Audit** | 写代码的不能自测。审计必须独立于被审计者 | AI 写了 ETL + 写了烟测 → 两者"一致地错误"，自洽 ≠ 正确 |
| **Via Negativa** | 记录"什么不能做"比"什么能做"更有价值 | 同样的错误被重复犯了 3 次，直到建立否定之道日志 |

### 三层架构关系

```
┌─────────────────────────────────────────────────┐
│                  CLAUDE.md                       │  ← 宪法：规则声明
│              (auto-loaded every session)          │
├─────────────────────────────────────────────────┤
│         Layer 1: Hooks (秒级自动拦截)             │  ← 机械执行：exit 2 = 阻止
│  PreToolUse → 拦截危险命令                        │
│  PostToolUse → 编辑后自动校验                     │
│  Stop → 会话结束提醒                              │
├─────────────────────────────────────────────────┤
│         Layer 2: Skills (流程编排)                │  ← 标准化流程：多阶段 + 门禁
│  /dev-cycle → Plan→Audit→Code→Audit→Verify       │
│  /deploy-cycle → Preflight→Deploy→Verify          │
│  /directive-ingest → Archive→Impact→Propose       │
├─────────────────────────────────────────────────┤
│         Layer 3: Agents (智能委派)                │  ← 专家系统：独立判断 + 结构化报告
│  recursive-auditor (opus) → 独立审计              │
│  deployment-guard (sonnet) → 门禁判定             │
│  infra-scout (haiku) → 快速诊断                   │
└─────────────────────────────────────────────────┘
```

---

## 3. CLAUDE.md 模板（项目宪法）

Claude Code 每次会话自动加载 `CLAUDE.md`。这是你与 AI 之间的"社会契约"。

```markdown
# [PROJECT_NAME] — 项目宪法

## WHAT: 项目定义

[CUSTOMIZE] 一段话描述项目做什么、用什么技术栈、数据规模多大。

### 技术栈
- [CUSTOMIZE] 语言、框架、数据库、云平台

### 文件地图
| 文件 | 角色 |
|------|------|
| [CUSTOMIZE] | [CUSTOMIZE] |

---

## WHY: 核心哲学

[CUSTOMIZE] 列出 2-4 条指导原则。不是技术细节，而是"为什么这样做"。

示例：
- 简单 > 聪明（Karpathy 极简美学）
- 已证伪的路径记录在 VIA_NEGATIVA.md，永不重蹈

---

## HOW: 不可违反的规则

### 物理公理（永恒，Layer 1）
[CUSTOMIZE] 列出项目中绝不可修改的常量、约束、不变量。
例如：
1. API 速率限制 = 100 req/s — 硬编码，不可绕过
2. 用户数据必须加密 — AES-256，不可降级

### 架构公理（可演进，Layer 2，从 config/current_spec.yaml 读取）
[CUSTOMIZE] 列出可以随版本演进但当前版本内必须一致的参数。
例如：
3. 数据库 schema version = v3（以 spec 文件为准）
4. batch_size = 1000（可通过环境变量覆盖）

### 破坏性操作红线
[CUSTOMIZE] 列出需要人工确认的危险操作。
例如：
5. **删除数据文件** → 必须人工确认，无例外
6. **远程推送**（git push, 部署到生产）→ 必须人工确认
7. **修改 spec 文件** → 必须人工确认

### 强制预检清单（部署任何东西之前）
[CUSTOMIZE] 列出部署前必须检查的项目。
例如：
8. 目标节点连通性验证
9. 磁盘空间 > 20% 可用
10. 无重复实例运行

### 工程规范
[CUSTOMIZE] 列出编码和运维规范。
例如：
11. 所有数据库查询必须参数化，禁止字符串拼接
12. 日志级别：生产用 WARNING，开发用 DEBUG

### 基础设施拓扑
[CUSTOMIZE] 列出节点、角色、连接方式。

### 上下文管理
13. `handover/LATEST.md` — 当前项目状态的单一真相源
14. `VIA_NEGATIVA.md` — 已证伪路径（新 agent 必读）
15. `audit/` — 灾难复盘存档
16. `config/current_spec.yaml` — 当前架构规范

### 灾难教训速查
[CUSTOMIZE] 从项目历史中提炼的教训。
例如：
17. 接收外部指令 ≠ 授权执行
18. AI 不可自测自验（审计独立于被测代码）

### 用户画像
[CUSTOMIZE] 描述与 AI 交互的用户特征，帮助 AI 调整沟通方式。
例如：
19. 全栈工程师，5年经验
20. 沟通偏好：英文为主，简洁直接
```

> **Omega 实际案例**: 见本项目根目录 `CLAUDE.md` — 49 条规则，覆盖物理常数、张量形状、硬件拓扑、SSH 路由、灾难教训。

---

## 4. Hook 层模板

Hook 是 Claude Code 的"条件反射"——在工具执行前后自动触发 shell 脚本。

### 退出码协议

| 退出码 | 含义 | 用途 |
|--------|------|------|
| 0 | 放行/通过 | stdout 内容作为信息显示给 Claude |
| 1 | 失败（软） | stderr 作为错误显示，不阻止 |
| 2 | 阻止（硬） | stderr 作为拒绝理由，工具调用被取消 |

### Hook 1: block-destructive.sh（PreToolUse → Bash）

拦截危险的 Bash 命令。

```bash
#!/usr/bin/env bash
# block-destructive.sh — PreToolUse hook for Bash commands
# Exit 0 = allow, Exit 2 = block (reason on stderr)

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || echo "")

[ -z "$COMMAND" ] && exit 0

# --- Universal patterns (keep these) ---

# Pattern 1: rm -rf with dangerous targets
if echo "$COMMAND" | grep -qE 'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|--force\s+)*(\/|~|\.\.|\/home|\/root|\*|\.claude)'; then
    echo "BLOCKED: Destructive rm command detected: $COMMAND" >&2
    exit 2
fi

# Pattern 2: git push --force
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force|git\s+push\s+-f'; then
    echo "BLOCKED: Force push detected: $COMMAND" >&2
    exit 2
fi

# Pattern 3: git reset --hard
if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
    echo "BLOCKED: git reset --hard can destroy uncommitted work: $COMMAND" >&2
    exit 2
fi

# Pattern 4: Destructive database operations
if echo "$COMMAND" | grep -qiE 'drop\s+table|drop\s+database|truncate\s+table'; then
    echo "BLOCKED: Destructive database operation: $COMMAND" >&2
    exit 2
fi

# --- [CUSTOMIZE] Project-specific patterns below ---

# Example: Block modification of immutable constants via sed/awk
# if echo "$COMMAND" | grep -qE "(sed|awk).*(YOUR_CONSTANT_NAME|YOUR_CONSTANT_VALUE)"; then
#     echo "BLOCKED: Attempt to modify immutable constants: $COMMAND" >&2
#     exit 2
# fi

# Example: Block deployment to production without explicit flag
# if echo "$COMMAND" | grep -qE "kubectl apply.*--namespace=production"; then
#     echo "BLOCKED: Production deployment detected: $COMMAND" >&2
#     exit 2
# fi

exit 0
```

> **Omega 实际案例**: 额外拦截 `(sed|awk).*(DELTA|C_TSE|c_constant|power_constant|0\.842|0\.5)` — 防止 AI 通过 sed 篡改物理常数。

### Hook 2: post-edit-validate.sh（PostToolUse → Edit|Write）

编辑关键文件后自动运行校验。

```bash
#!/usr/bin/env bash
# post-edit-validate.sh — PostToolUse hook for Edit/Write
# Exit 0 = validation passed, Exit 1 = validation failed

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || echo "")

[ -z "$FILE_PATH" ] && exit 0

# --- [CUSTOMIZE] Define which files trigger validation ---
# Regex pattern matching critical files
CRITICAL_PATTERN="[CUSTOMIZE_PATTERN]"
# Example: "src/core/.*\.py|config/.*\.yaml|schema/.*\.sql"

if ! echo "$FILE_PATH" | grep -qE "$CRITICAL_PATTERN"; then
    exit 0
fi

# --- [CUSTOMIZE] Run your validation command ---
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "[PostToolUse] Critical file modified: $(basename "$FILE_PATH")"
echo "[PostToolUse] Running automatic validation..."

# [CUSTOMIZE] Replace with your validation command:
# Examples:
#   python3 project_axioms.py --verbose
#   npm run typecheck
#   cargo check
#   make lint
if python3 project_axioms.py --verbose 2>&1; then
    echo "[PostToolUse] Validation PASSED"
    exit 0
else
    echo "[PostToolUse] VALIDATION FAILED — review errors before continuing" >&2
    exit 1
fi
```

> **Omega 实际案例**: `CRITICAL_PATTERN="omega_epiplexity_plus_core\.py|omega_axioms\.py|architect/current_spec\.yaml|tools/.*etl.*\.py|tools/.*forge.*\.py"`，触发后运行 `python3 omega_axioms.py --verbose`（39 项公理检查）。

### Hook 3: stop-guard.sh（Stop）

会话结束时提醒未提交的关键文件变更。

```bash
#!/usr/bin/env bash
# stop-guard.sh — Stop hook
# Always exits 0 (advisory only, never blocks session end)

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" 2>/dev/null || exit 0

# Read stdin (required by hook protocol)
cat > /dev/null

# --- [CUSTOMIZE] List your critical files ---
CORE_FILES="[CUSTOMIZE_FILE_LIST]"
# Example: "src/core/engine.py config/spec.yaml schema/migrations/"

DIRTY_CORE=""

for f in $CORE_FILES; do
    if [ -f "$f" ] && ! git diff --quiet -- "$f" 2>/dev/null; then
        DIRTY_CORE="$DIRTY_CORE $f"
    fi
    if [ -f "$f" ] && ! git diff --cached --quiet -- "$f" 2>/dev/null; then
        DIRTY_CORE="$DIRTY_CORE $f (staged)"
    fi
done

if [ -n "$DIRTY_CORE" ]; then
    echo ""
    echo "WARNING: Uncommitted changes in critical files:"
    for f in $DIRTY_CORE; do
        echo "  - $f"
    done
    echo "Consider committing these changes before ending the session."
    echo ""
fi

exit 0
```

> **Omega 实际案例**: 监控 `omega_epiplexity_plus_core.py omega_axioms.py architect/current_spec.yaml` 以及 `tools/` 下所有 ETL 文件。

### settings.json（Hook 注册）

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-destructive.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/post-edit-validate.sh",
            "timeout": 30
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/stop-guard.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

---

## 5. Skill 层模板

Skill 是用户可通过 `/skill-name` 调用的标准化流程。存放于 `.claude/skills/<name>/SKILL.md`。

### Skill 1: /dev-cycle（开发全流程，9 阶段）

```markdown
---
name: dev-cycle
description: [CUSTOMIZE] 完整开发周期 — Plan/Audit/Fix/Code/Audit/Fix/Validate/External/Summary
user-invocable: true
---

# Dev Cycle（完整开发周期）

自动编排从计划到代码完成的完整开发周期。

## 输入

用户提供任务描述，例如：
- `/dev-cycle 实现用户认证模块`
- `/dev-cycle 修复数据库连接池泄漏`

## 九阶段流程

每个阶段间有 PASS/FAIL 门禁。FAIL 时循环修复，不跳过。

### Stage 1: PLAN

1. 读取 `config/current_spec.yaml` 获取当前规范
2. 读取 `VIA_NEGATIVA.md` 确保计划不重蹈覆辙
3. 草拟实现计划：需要修改的文件、每个文件的变更、潜在风险

输出：`=== STAGE 1: PLAN === <实现计划>`

### Stage 2: AUDIT PLAN

调用 `independent-auditor` agent 审计计划：
- 计划是否与 spec 对齐
- 计划是否违反 VIA_NEGATIVA
- 是否涉及 Layer 1 不变量

输出：`=== STAGE 2: AUDIT === Verdict: PASS / FAIL`

**FAIL → Stage 3 修复 → 回到 Stage 2**

### Stage 3: FIX PLAN（仅在 Stage 2 FAIL 时）

修正计划 → 返回 Stage 2。最多 3 次循环。

### Stage 4: CODE

按审计通过的计划执行代码变更。PostToolUse hook 自动校验。

### Stage 5: AUDIT CODE

调用 `independent-auditor` agent 审计代码变更。

**FAIL → Stage 6 修复 → 回到 Stage 5**

### Stage 6: FIX CODE（仅在 Stage 5 FAIL 时）

修正代码 → 返回 Stage 5。最多 3 次循环。

### Stage 7: VALIDATE

运行项目校验命令：
```bash
# [CUSTOMIZE] Replace with your validation:
python3 project_axioms.py --verbose
# or: npm test / cargo test / make check
```

**FAIL → 回到 Stage 6**

### Stage 8: EXTERNAL AUDIT

[CUSTOMIZE] 使用外部 LLM / CI / 人工进行独立审计：
```bash
# Example: codex exec --full-auto "<audit prompt>"
# Example: run CI pipeline
# Example: notify code reviewer
```

### Stage 9: SUMMARY

输出变更摘要 + 等待用户确认 commit。

## 安全约束

- 计划阶段不执行代码变更
- 代码阶段不跳过审计
- 校验是最终门禁，不可跳过
- Layer 1 不变量在任何阶段都不可修改
- 审计循环超过 3 次 → 暂停并征求用户意见
```

> **Omega 实际案例**: Stage 7 运行 `omega_axioms.py --verbose`（39 项检查），Stage 8 调用 Codex (GPT 5.4) + Gemini 进行三层独立审计。

### Skill 2: /deploy-cycle（部署全流程，6 阶段）

```markdown
---
name: deploy-cycle
description: [CUSTOMIZE] 部署周期 — Pre-flight/Validate/Health/Deploy/Verify/Document
user-invocable: true
---

# Deploy Cycle（部署周期）

## 输入

`/deploy-cycle <target-node>`

## 六阶段流程

### Stage 1: PRE-FLIGHT
调用 `/pre-flight` 对目标执行预检。**任一 FAIL → 停止**

### Stage 2: VALIDATE
运行项目校验命令。**FAIL → 不允许部署**

### Stage 3: HEALTH CHECK
调用 `/health-check` 检查基础设施健康。

### Stage 4: DEPLOY
**需要用户明确确认。** 执行实际部署操作。
[CUSTOMIZE] 部署命令：scp/rsync/kubectl apply/terraform apply 等。

### Stage 5: VERIFY
部署后验证：进程运行状态、初始日志、健康检查端点。

### Stage 6: DOCUMENT
更新 `handover/LATEST.md` 记录部署。提示用户 commit。
```

> **Omega 实际案例**: Stage 4 使用 `scp` + `ssh systemd-run --slice=heavy-workload.slice`，确保重计算进程有 cgroup 保护。

### Skill 3: /directive-ingest（外部需求摄入，4 阶段）

```markdown
---
name: directive-ingest
description: [CUSTOMIZE] 外部需求摄入 — 归档指令、检测影响、提议更新、确认执行
user-invocable: true
---

# Directive Ingest（外部需求摄入）

当接收到外部需求（架构师指令、产品需求、技术 RFC）时使用。

## 核心原则

**接收指令 ≠ 授权执行。** 只归档和分析，不执行代码变更。

## 步骤

### 1. ARCHIVE（完整归档，不可压缩）
保存到 `[CUSTOMIZE_DIRECTIVE_DIR]/YYYY-MM-DD_<topic>.md`

### 2. IMPACT-DETECT（自动影响分析）
分析指令是否涉及：
- Layer 1 不变量 → **VIOLATION**（归档但不执行）
- Layer 2 参数 → **UPDATE REQUIRED**（需用户确认）
- 无影响 → **NONE**（正常流转）

### 3. PROPOSE（提议变更）
列出需要更新的配置和代码文件。

### 4. CONFIRM（等待用户确认）
用户确认后才执行 spec 更新。
```

> **Omega 实际案例**: 6 份 Google Docs 架构师指令通过此流程摄取，其中 1 份导致物理常数 c 从 Layer 1 降级到 Layer 2，需要更新 7 个文件。

### Skill 4: /validate（多层审计，3 阶段）

```markdown
---
name: validate
description: [CUSTOMIZE] 多层校验 — 内部自检 + 外部审计 + 结构化报告
user-invocable: true
---

# Validate（多层校验）

### Layer A: Internal
[CUSTOMIZE] 运行内部校验工具（axioms checker, type checker, linter）

### Layer B: External
[CUSTOMIZE] 调用外部校验（CI, 另一个 LLM, 人工 review）

### Layer C: Report
输出结构化 PASS/FAIL 报告。
```

### Skill 5: /pre-flight（部署预检，1 阶段）

```markdown
---
name: pre-flight
description: [CUSTOMIZE] 部署前预检 — 检查目标节点各项指标，输出 GO/NO-GO
user-invocable: true
---

# Pre-Flight Deployment Check

## 步骤

[CUSTOMIZE] 按你的基础设施定制：

1. **连通性**: SSH / HTTP 健康检查端点
2. **磁盘空间**: > 20% 可用
3. **内存**: < 80% 使用
4. **无重复实例**: 检查进程列表
5. **依赖**: 运行时依赖检查
6. **数据路径**: 输入/输出路径存在
7. [CUSTOMIZE] 项目特定检查项

## 输出格式

```
=== PRE-FLIGHT CHECK: <target> ===
[1] Connectivity ......... PASS / FAIL
[2] Disk space ........... PASS / FAIL
...
=== VERDICT: GO / NO-GO ===
```

## 判定规则

**任一 FAIL → NO-GO**，列出修复建议。
```

### Skill 6: /health-check（基础设施诊断，1 阶段）

```markdown
---
name: health-check
description: [CUSTOMIZE] 基础设施健康检查 — 输出结构化诊断报告
user-invocable: true
---

# Health Check

## 检查项

[CUSTOMIZE] 按你的基础设施定制：

| 节点 | 连接方式 | 角色 |
|------|----------|------|
| [CUSTOMIZE] | [CUSTOMIZE] | [CUSTOMIZE] |

对每个节点检查：连通性、磁盘、内存、进程、[CUSTOMIZE]特定检查项。

## 约束

- 纯只读操作
- 超时设置 5 秒
- 节点不可达时标记 UNREACHABLE 并继续
```

---

## 6. Agent 层模板

Agent 是具有独立模型和约束的子进程。存放于 `.claude/agents/<name>.md`。

### 模型分配策略

| 任务类型 | 推荐模型 | 理由 |
|----------|----------|------|
| 深度推理（审计、数学验证） | Opus | 需要最强推理能力 |
| 流程执行（门禁、部署） | Sonnet | 足够聪明 + 更快 |
| 快速诊断（健康检查） | Haiku | 最快速度，秒级响应 |

### Agent 1: independent-auditor（Opus，只读审计）

```markdown
---
model: opus
description: [CUSTOMIZE] 独立验证正确性和规范对齐的审计员。只读操作。
---

# Independent Auditor

你是项目的独立审计员。你的职责是验证代码和配置的正确性，**独立于**编写代码的 AI agent。

## 核心原则

- 你是**只读的**。绝不修改任何文件。
- 审计标准来自 `config/current_spec.yaml`，不是硬编码的。
- 不信任被审计代码作者的自我验证。

## 审计检查项

### 1. 不变量完整性（Layer 1）
[CUSTOMIZE] 读取核心代码，验证不可变常量未被篡改。

### 2. 规范对齐（Layer 2）
[CUSTOMIZE] 读取 spec 文件，检查代码是否与规范一致。

### 3. 静默失败检测
检查代码中可能的：全零输出路径、NaN/Inf 传播、不合理的默认值。

### 4. 需求对齐
[CUSTOMIZE] 检查代码变更是否符合最新需求/指令。

## 输出格式

```
=== AUDIT REPORT ===
[Invariants] Layer 1:        PASS / FAIL
[Spec]       Alignment:      PASS / FAIL
[Numeric]    Stability:      PASS / FAIL
[Reqs]       Compliance:     PASS / FAIL / N/A

=== VERDICT: CLEAN / VIOLATIONS FOUND ===
```

## 工具限制

只能使用：Read, Glob, Grep, Bash（仅只读命令）。
**绝不可使用 Write 或 Edit。**
```

> **Omega 实际案例**: 检查 `omega_epiplexity_plus_core.py` 中 `c_constant=0.842`, `power_constant=2.0`, `torch.no_grad()` 未被篡改；检查所有张量形状代码与 `current_spec.yaml` 的 `[B, 160, 10, 10]` 对齐。

### Agent 2: external-liaison（Opus，外部需求管理）

```markdown
---
model: opus
description: [CUSTOMIZE] 管理外部需求的生命周期 — 摄取、归档、更新 spec、通知冲突。
---

# External Liaison

你是外部需求（架构师指令、产品需求、技术 RFC）的生命周期管理员。

## 核心原则

- **接收指令 ≠ 授权执行。** 只负责记录和通知。
- 对 spec 文件的任何修改必须获得用户确认。
- 维护完整历史记录。

## 工作流程

### 1. 摄取（Ingest）
提取关键指令，区分"建议"和"执行要求"。

### 2. 归档（Archive）
保存到 `[CUSTOMIZE_DIR]/YYYY-MM-DD_<topic>.md`。
[CUSTOMIZE] 归档格式。

### 3. 影响分析
检测是否涉及 Layer 1（阻止）或 Layer 2（需确认）参数。

### 4. 更新 Spec（需用户确认）
生成 diff → 用户确认 → 执行更新 → 运行校验。

## 安全约束

- 不可自行修改核心代码
- 所有 spec 更新需用户确认
- 如果需求与 VIA_NEGATIVA 冲突，必须警告
```

### Agent 3: deployment-guard（Sonnet，部署门禁）

```markdown
---
model: sonnet
description: [CUSTOMIZE] 部署操作的预检门禁。任一检查失败 = NO-GO。
---

# Deployment Guard

## 触发条件

当即将执行部署相关操作时激活。
[CUSTOMIZE] 列出触发命令：scp, kubectl apply, terraform apply 等。

## 预检清单

[CUSTOMIZE] 按你的基础设施定制：
1. 目标确认
2. 连通性
3. 依赖检查
4. 路径存在
5. 无重复实例
6. 磁盘空间
7. [CUSTOMIZE] 项目特定检查

## 判定规则

**任何检查失败 → NO-GO**，列出失败项 + 修复建议 + 阻止继续。
```

### Agent 4: infra-scout（Haiku，快速诊断）

```markdown
---
model: haiku
description: [CUSTOMIZE] 快速检查基础设施健康 — 连通性、磁盘、内存、进程。
---

# Infra Scout

## 目标节点

[CUSTOMIZE] 列出节点和连接方式。

## 检查项

[CUSTOMIZE] 对每个节点：连通性、磁盘、内存、进程。

## 约束

- 纯只读操作
- 每个命令 5 秒超时
- 节点不可达时标记 UNREACHABLE 并继续
```

---

## 7. Axiom-as-Code 模板

将项目不变量编码为可执行的 Python 检查器，被 Hook、Skill、Agent 三层调用。

### 模板骨架（纯标准库，零外部依赖）

```python
"""
[PROJECT_NAME] 公理断言模块 (Axiom Assertion Module)
=====================================================
双层设计：
  Layer 1: 永恒不变量（硬编码，AI 不可修改）
  Layer 2: 可演进参数（从 config/current_spec.yaml 动态加载）

用法：
  python project_axioms.py              # 独立自检
  python project_axioms.py --verbose    # 详细输出
"""

import sys
import os

# ============================================================
# Layer 1: Immutable Invariants (hardcoded, AI cannot modify)
# ============================================================

# [CUSTOMIZE] Define your project's immutable constants:
# Example:
# API_RATE_LIMIT = 100        # req/s — hardcoded ceiling
# ENCRYPTION_ALGO = "AES-256" # never downgrade
# MIN_PASSWORD_LEN = 12       # security floor


# ============================================================
# Layer 2: Evolvable Parameters (loaded from spec YAML)
# ============================================================

def load_spec(spec_path: str = None) -> dict:
    """Load Layer 2 parameters from spec file"""
    if spec_path is None:
        spec_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "config", "current_spec.yaml"
        )

    if not os.path.exists(spec_path):
        print(f"[WARN] Spec file not found: {spec_path}")
        return _default_spec()

    return _parse_simple_yaml(spec_path)


def _default_spec() -> dict:
    """Fallback defaults when spec file is missing"""
    # [CUSTOMIZE] Your project's default parameters
    return {
        "version": "v1",
    }


def _parse_simple_yaml(path: str) -> dict:
    """Pure-Python YAML parser (no PyYAML dependency).
    Supports arbitrary nesting via indentation tracking."""
    result = {}
    stack = [(-1, result)]

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if " #" in stripped:
                stripped = stripped[:stripped.index(" #")].strip()
            if ":" not in stripped:
                continue
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1]
            if not value:
                new_dict = {}
                parent[key] = new_dict
                stack.append((indent, new_dict))
            else:
                parent[key] = _cast_value(value)

    return result


def _cast_value(v: str):
    """Cast string to list, int, float, or str"""
    if v.startswith("[") and v.endswith("]"):
        items = [x.strip() for x in v[1:-1].split(",")]
        return [_cast_scalar(x) for x in items]
    return _cast_scalar(v)


def _cast_scalar(v: str):
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


# ============================================================
# Assertion Functions
# ============================================================

class AxiomViolation(Exception):
    """Raised when an axiom is violated"""
    pass


def assert_layer1(verbose: bool = False) -> list:
    """Verify Layer 1 immutable invariants"""
    errors = []

    # [CUSTOMIZE] Add your Layer 1 checks:
    # Example:
    # if API_RATE_LIMIT != 100:
    #     errors.append(f"FATAL: API_RATE_LIMIT = {API_RATE_LIMIT}, expected 100")
    # elif verbose:
    #     print("  [OK] API_RATE_LIMIT = 100")

    return errors


def assert_layer2(spec: dict, verbose: bool = False) -> list:
    """Verify Layer 2 parameters from spec"""
    errors = []

    # [CUSTOMIZE] Add your Layer 2 checks:
    # Example:
    # db_version = spec.get("database", {}).get("schema_version")
    # if db_version is not None and db_version != "v3":
    #     errors.append(f"STALE: schema_version={db_version}, expected v3")
    # elif verbose:
    #     print(f"  [OK] schema_version = {db_version}")

    return errors


def assert_code_constants(verbose: bool = False) -> list:
    """Verify constants in source code haven't been tampered with"""
    errors = []

    # [CUSTOMIZE] Read critical source files and verify constants:
    # Example:
    # core_path = os.path.join(os.path.dirname(__file__), "src/core/engine.py")
    # if os.path.exists(core_path):
    #     with open(core_path, "r") as f:
    #         content = f.read()
    #     if "RATE_LIMIT = 100" not in content:
    #         errors.append("CODE TAMPERING: RATE_LIMIT modified in engine.py")

    return errors


# ============================================================
# Main Entry
# ============================================================

def run_full_audit(verbose: bool = False, spec_path: str = None) -> bool:
    """Run complete axiom audit, return True if all passed"""
    all_errors = []

    print("=" * 50)
    print(f" PROJECT AXIOM AUDIT")
    print("=" * 50)

    print("\n[Layer 1] Immutable Invariants:")
    all_errors.extend(assert_layer1(verbose))

    print("\n[Layer 2] Evolvable Parameters (from spec):")
    spec = load_spec(spec_path)
    all_errors.extend(assert_layer2(spec, verbose))

    print("\n[Code] Source Constants:")
    all_errors.extend(assert_code_constants(verbose))

    print("\n" + "=" * 50)
    if all_errors:
        print(f" AUDIT FAILED — {len(all_errors)} violation(s):")
        for e in all_errors:
            print(f"   !! {e}")
        print("=" * 50)
        return False
    else:
        print(" AUDIT PASSED — All axioms verified")
        print("=" * 50)
        return True


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    passed = run_full_audit(verbose=verbose)
    sys.exit(0 if passed else 1)
```

> **Omega 实际案例**: `omega_axioms.py` 包含 39 项检查——从 δ=0.5（永恒物理常数）到 backtest.success_criterion（回测收益比 > 3.0），全部自动运行。YAML parser 支持任意嵌套深度（纯标准库，无 PyYAML 依赖）。

---

## 8. 上下文管理模板

4 个文件构成项目的"集体记忆"，确保 AI 跨会话不失忆。

### handover/LATEST.md（会话状态单一真相源）

```markdown
# [PROJECT_NAME] — Handover State
Last Updated: YYYY-MM-DD — **STATUS: [CUSTOMIZE]**

## 1. CURRENT STATUS
[CUSTOMIZE] 一段话描述当前项目状态。

### What happened in this session
[CUSTOMIZE] 本次会话完成的工作。

## 2. KEY DECISIONS
[CUSTOMIZE] 已做出的关键决策及原因。

## 3. NEXT STEPS
1. [CUSTOMIZE] 下一步行动
2. [CUSTOMIZE]

## 4. CRITICAL RULES FOR NEXT AGENT
1. Read CLAUDE.md first
2. Read VIA_NEGATIVA.md — know what NOT to do
3. [CUSTOMIZE] 项目特定规则
```

> **Omega 实际案例**: `LATEST.md` 包含 V1→V2→V3 架构演化历史、10 个 session 的工作记录、硬件拓扑速查、下一步计划。每个新 AI agent 第一件事就是读这个文件。

### VIA_NEGATIVA.md（已证伪路径）

```markdown
# VIA NEGATIVA — 否定之道日志

已证伪路径的永久记录。只增不删。

---

## [CUSTOMIZE_CATEGORY_1]

### [CUSTOMIZE] 路径名称
- **证伪时间**: YYYY-MM-DD
- **做了什么**: [what was attempted]
- **为什么失败**: [root cause]
- **结论**: [the rule derived from this failure]

---

## [CUSTOMIZE_CATEGORY_2]

### [CUSTOMIZE] 路径名称
- **证伪时间**: YYYY-MM-DD
- **做了什么**: [what was attempted]
- **为什么失败**: [root cause]
- **结论**: [the rule derived from this failure]
```

> **Omega 实际案例**: 10 条已证伪路径，分 3 类（数学与架构 / 工程与性能 / AI 治理），每条都有时间戳和根因分析。例如："AI 自己写烟测测自己 → 自洽性掩盖正确性"。

### audit/（灾难复盘存档）

当发生严重事故时，写入 `audit/YYYY-MM-DD_<incident>.md`，包含：
- 完整时间线
- 根因链（5 个 Why）
- 具体损失
- 教训清单
- 已采取的预防措施

### config/current_spec.yaml（活规范）

```yaml
# [PROJECT_NAME] Active Specification
# This is the single source of truth for Layer 2 parameters.
# AI agents read from this; changes require human confirmation.

version: v1  # [CUSTOMIZE]

# [CUSTOMIZE] Add your project's evolvable parameters:
# database:
#   schema_version: v3
#   max_connections: 100
#
# api:
#   rate_limit: 100
#   timeout_ms: 5000
#
# deployment:
#   target_env: staging
#   replicas: 3
```

---

## 9. Settings 模板

### .claude/settings.json（团队共享，入库）

Hook 定义。所有团队成员共享相同的安全护栏。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-destructive.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/post-edit-validate.sh",
            "timeout": 30
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/stop-guard.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### .claude/settings.local.json（个人，gitignore）

权限设置。每个用户根据自己的信任级别配置。

```json
{
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "Agent"
    ],
    "deny": [
      "Bash(rm -rf:*)",
      "Bash(rm -r:*)",
      "Bash(rm --force:*)"
    ]
  }
}
```

> **重要**: `settings.local.json` 不入库（加入 `.gitignore`），因为权限是个人偏好。

### .mcp.json（MCP 配置）

```json
{
  "mcpServers": {}
}
```

默认为空。需要外部工具服务时按 MCP 协议配置。

### .claudeignore（上下文隔离）

```
# Binary and large data files
*.parquet
*.tar
*.pth
*.7z
*.zip
*.gz
*.bz2
*.npy

# Build artifacts
__pycache__/
*.pyc
*.pyo
*.egg-info/
node_modules/
dist/
build/

# Git internals
.git/

# OS artifacts
.DS_Store
Thumbs.db

# Logs
*.log

# [CUSTOMIZE] Project-specific exclusions:
# *.sqlite
# data/raw/

# Do NOT exclude (critical context):
# [CUSTOMIZE] List directories that must remain visible to Claude:
# src/         — source code
# config/      — specifications
# handover/    — project state
# audit/       — post-mortems
```

---

## 10. Per-Project Decision Checklist

实例化模板前，回答以下问题：

### 不变量（Layer 1）

- [ ] 你的项目中有哪些**绝不可修改**的常量/约束？
  - 例：物理常数、安全阈值、合规要求、协议版本
  - 写入：`CLAUDE.md` HOW 段 + `project_axioms.py` Layer 1

### 可演进参数（Layer 2）

- [ ] 哪些参数会随版本演进但当前版本内必须一致？
  - 例：schema version, batch size, feature dimensions
  - 写入：`config/current_spec.yaml` + `project_axioms.py` Layer 2

### 破坏性操作

- [ ] 哪些操作是不可逆/高风险的？
  - 例：删除数据、推送代码、部署生产、发送通知
  - 写入：`CLAUDE.md` 红线段 + `block-destructive.sh`

### 关键文件

- [ ] 哪些文件修改后需要自动校验？
  - 例：核心算法、配置文件、数据库 schema
  - 写入：`post-edit-validate.sh` CRITICAL_PATTERN

### 校验命令

- [ ] 你的项目用什么命令验证正确性？
  - 例：`python project_axioms.py --verbose` / `npm test` / `cargo check`
  - 写入：`post-edit-validate.sh` + `/dev-cycle` Stage 7

### 部署拓扑

- [ ] 你的部署目标是什么？
  - 例：单服务器 SSH / Kubernetes 集群 / AWS Lambda / 本地 Docker
  - 写入：`CLAUDE.md` 基础设施段 + `/deploy-cycle` + `deployment-guard`

### 会话结束提醒

- [ ] 哪些文件的未提交变更需要在会话结束时提醒？
  - 例：核心算法文件、配置文件
  - 写入：`stop-guard.sh` CORE_FILES

### 外部需求来源

- [ ] 需求/指令从哪里来？
  - 例：Google Docs / Jira / Slack / 直接对话
  - 写入：`/directive-ingest` + `external-liaison` agent

---

## 推荐文件树（模板实例化后）

```
project-root/
  CLAUDE.md                            # 项目宪法（auto-loaded）
  VIA_NEGATIVA.md                      # 已证伪路径（只增不删）
  project_axioms.py                    # 不变量检查器（被三层调用）
  config/
    current_spec.yaml                  # 活规范（Layer 2 参数源）
  handover/
    LATEST.md                          # 会话状态单一真相源
  audit/                               # 灾难复盘存档
  .claude/
    settings.json                      # Hook 定义（团队共享，入库）
    settings.local.json                # 权限（个人，gitignore）
    hooks/
      block-destructive.sh             # PreToolUse: 拦截危险命令
      post-edit-validate.sh            # PostToolUse: 编辑后校验
      stop-guard.sh                    # Stop: 结束提醒
    skills/
      dev-cycle/SKILL.md              # /dev-cycle（9 阶段）
      deploy-cycle/SKILL.md           # /deploy-cycle（6 阶段）
      directive-ingest/SKILL.md       # /directive-ingest（4 阶段）
      validate/SKILL.md               # /validate（3 层）
      pre-flight/SKILL.md             # /pre-flight（GO/NO-GO）
      health-check/SKILL.md           # /health-check（诊断报告）
    agents/
      independent-auditor.md           # Opus: 只读审计
      external-liaison.md              # Opus: 外部需求管理
      deployment-guard.md              # Sonnet: 部署门禁
      infra-scout.md                   # Haiku: 快速诊断
  .claudeignore                        # 上下文隔离
  .mcp.json                            # MCP 配置（默认空）
```

---

## 附录：Omega 灾难速查

本蓝图源自 Omega Pure 项目的真实教训：

| 事件 | 根因 | 教训 |
|------|------|------|
| 188GB 数据被删 | AI 收到架构师指令后未经确认直接执行 | 接收指令 ≠ 授权执行 |
| OOM 内核死锁 | SSH 继承 oom_score_adj=-1000，所有进程不可杀 | 用户进程不可继承系统级 OOM 保护 |
| ETL 100h 超时 | AI 启动第二个实例，内存翻倍触发 OOM | 单实例文件锁是强制要求 |
| 张量形状错误 | AI 写 ETL + 写烟测，两者"一致地错误" | 审计必须独立于被审计者 |
| 物理常数被改 | AI 将 δ=0.5 设为可学习参数 | 物理常数由人类锁定，AI 只提供参考区间 |
| 同样错误重复 3 次 | 没有"什么不能做"的记录 | Via Negativa：记录证伪路径 |

完整复盘见 Omega 项目 `audit/gemini_bitter_lessons.md`。
