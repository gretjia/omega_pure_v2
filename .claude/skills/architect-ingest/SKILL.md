---
name: architect-ingest
description: 架构师指令摄取 — 归档指令、检测公理影响、提议spec更新
user-invocable: true
---

# Architect Ingest（架构师指令摄取）

摄取架构师指令，自动检测公理影响，归档并提议 spec 更新。

## 前置条件

用户已粘贴架构师的指令文本到对话中，或提供了 Google Docs ID。

**如果提供了 Google Docs ID**：使用 `gdocs read <doc_id>` 读取全文（CLI 位于 `/usr/local/bin/gdocs`，详见 memory `reference_gdocs_cli.md`）。

## 步骤

### 1. 完整归档原始指令（不可压缩）

**强制规则：directive 归档必须包含原文级别的完整内容，严禁摘要式归档。**

这是从 Gemini 灾难中学到的 Bitter Lesson：摘要式归档导致训练策略、回测约束、HPO 搜索空间等关键设计意图不可逆丢失。下一个 session 的 AI 无法从摘要中恢复这些信息。

归档到 `architect/directives/YYYY-MM-DD_<topic>.md` 时必须包含：
- **源文档 ID**（Google Docs ID 或其他来源标识）
- **完整指令内容**（逐条，不遗漏）
- **设计哲学与理由**（为什么这样做，不只是做什么）
- **具体参数和公式**（精确到数值和搜索范围）
- **对 current_spec.yaml 每个字段的影响**

同时对比 `architect/current_spec.yaml` 差异。

### 2. 公理影响检测（自动）

分析指令内容，检测是否涉及以下公理相关变更：

**Layer 1 物理常数检测**（不可修改）：
- `delta` / `δ` = 0.5（平方根法则指数）
- `c_tse` / `c` = 0.842（TSE 实证常数）
- `power_constant` / `POWER_INVERSE` = 2.0

如果指令试图修改这些值：
```
⛔ AXIOM VIOLATION — LAYER 1 IMMUTABLE
指令试图修改物理常数: <具体常数>
Layer 1 物理公理由人类锁定，AI 不可修改。
此指令已归档但 **不可执行**。
请联系架构师确认这是否为误操作。
```
**强制阻止，不提供变通方案。**

**Layer 2 架构参数检测**（可演进，需确认）：
- `tensor.shape` — 时间轴、空间轴、特征轴维度
- `etl.vol_threshold` — 成交量阈值
- `etl.window_size` — ACF 窗口大小
- `etl.stride` — 环形缓冲步长
- `etl.adv_fraction` — ADV 动态阈值比例
- `model.lambda_s` — MDL 结构惩罚权重
- 特征维度增删
- ETL 逻辑变更

### 3. 输出公理影响评级

三级评级：

**NO AXIOM IMPACT**:
```
=== AXIOM IMPACT: NONE ===
此指令不涉及物理常数或架构参数变更。
正常流转到开发阶段。
```

**AXIOM UPDATE REQUIRED**:
```
=== AXIOM IMPACT: UPDATE REQUIRED ===
此指令涉及 Layer 2 架构参数变更：

变更项:
  - <param_name>: <old_value> → <new_value>
  - ...

等待用户确认后更新 architect/current_spec.yaml
```

等待用户确认后：
1. 更新 `architect/current_spec.yaml`，**标记变更字段为 `# [DRAFT — pending audit]`**
2. 运行 `python3 omega_axioms.py --verbose` 验证新 spec 基本一致性
3. 如果验证失败，回滚 spec 变更并报告
4. **不标记为 final** — spec 变更在外部审计通过后才移除 `[DRAFT]` 标记

> ⚠️ C-059 教训: spec 在审计前定稿 → 错误假设被固化 → 9h GPU 浪费。
> Draft 状态 = "这是架构师的意图, 但未被验证"。
> Final 状态 = "经过 Codex + Gemini 审计确认"。

**AXIOM VIOLATION**:
```
=== AXIOM IMPACT: ⛔ VIOLATION ===
指令试图修改 Layer 1 永恒物理常数。
已归档但不可执行。
```

### 4. 更新 architect/INDEX.md

在索引中添加新条目，格式：
```markdown
| YYYY-MM-DD | <主题> | [链接](directives/<filename>) | <AXIOM IMPACT 级别> | <状态> |
```

### 5. 生成结构化洞察 (Insight)

从指令中提炼原子化的设计决策，写入 `architect/insights/INS-NNN_<slug>.md`：

```yaml
---
id: INS-NNN           # 递增编号，查 insights/INDEX.md 获取下一个
title: <简短标题>
category: <physics|architecture|training|metrics|nomenclature>
date: <YYYY-MM-DD>
axiom_impact: <NONE|UPDATE_REQUIRED|LAYER1_TO_LAYER2_DOWNGRADE|VIOLATION>
status: <active|pending_<blocker>>
audit_status: <draft|audited|final>   # NEW: draft until external audit passes
source_directive: <directive 文件名>
source_gdoc: <gdoc 文件名 or null>
---

# INS-NNN: <标题>

## 裁决
<一段话概括决策>

## 理由
<为什么这样做，物理/工程/哲学层面>

## 前提假设（C-059 教训: 假设不写明 = 定时炸弹）
<此决策依赖的隐含假设，必须逐条列出>
- **数据格式**: target 的单位是什么? (raw decimal / BP / normalized)
  → 验证方法: `grep -n "target" tools/omega_etl_v3_topo_forge.py | head -5`
- **上游依赖**: 哪些 INS/spec 字段必须先就位?
- **环境假设**: GPU 型号 / 内存 / 磁盘等硬件约束

## 被拒绝的替代方案（防止下一个 session 重蹈覆辙）
<列出考虑过但拒绝的方案，每个附一行拒绝理由>
- **方案 B**: <描述> → 拒绝原因: <一句话>
- **方案 C**: <描述> → 拒绝原因: <一句话>
如果来自外部审计的建议被拒绝，标注 `[AUDIT OVERRIDE]` 及数学/物理理由。

## 验证协议（C-052 教训: 未验证的诊断 = 未诊断）
<如何确认此决策有效，必须是可执行的步骤>
1. 验证命令: `<具体命令或脚本>`
2. 预期结果: `<具体数值范围>`
3. 失败时的回退方案: `<回退到什么状态>`

## 参数标定来源（C-055 教训: 直觉阈值 ≠ 物理常数）
<每个新参数的来源，三选一>
- 🔬 **实测标定**: 来自 <实验/数据/commit>，置信度 <高/中>
- 📐 **理论推导**: 来自 <公式/论文>，需实测验证
- 🎯 **架构师直觉**: 来自 <经验/类比>，**必须标注"待实测标定"**

## 影响文件
<受影响的代码文件及变更描述>

## spec 参数映射（溯源链）
<此 INS 对应的 spec 参数，用于 spec-code 对齐检查>
- `spec.loss_function` → 实现在 `omega_epiplexity_plus_core.py:compute_spear_loss_*`
- `spec.hpo.fixed_params.lambda_s` → 实现在 `train.py:--lambda_s default=`
```

同时更新 `architect/insights/INDEX.md` 索引表。

**一个 directive 可以产生多个 insights**（如 id5 产生了 INS-001/003/004/008 四个独立洞察）。

### 6. 列出受影响文件

输出需要变更的代码文件清单及变更描述。

### 7. 更新 Chain of Custody（Living Harness 管线追踪）

在 `architect/chain_of_custody.yaml` 的 `pipelines:` 下追加新条目：

```yaml
  - directive: "<归档文件名>"
    stage: ins_created       # ingest 完成 + INS 已创建
    insights: [INS-xxx, ...]
    spec_fields: ["<变更的 spec 字段>"]
    code_files: ["<受影响文件>"]
    audit_status: draft      # 尚未经过外部审计
    failures: []
    last_updated: "<today>"
```

此条目将被后续 skill 自动推进:
- `/dev-cycle` Stage 4 (CODE) → `stage: coded`
- `/dev-cycle` Stage 8 (AUDIT) → `audit_status: final`
- `/deploy-cycle` → `stage: deployed` + `docker_tag: <tag>`
- 如果失败 → `/lesson-to-rule` 追加 `failures` 记录

### 8. 后续提醒

如果涉及公理变更（AXIOM UPDATE REQUIRED），提醒用户：
```
提醒: 完成 /dev-cycle 后，建议运行 /axiom-audit 进行全量公理验证。
```

## 输出格式

```
=== ARCHITECT DIRECTIVE INGESTED ===
Date: <date>
Topic: <topic>
Archived to: architect/directives/<filename>

Key Directives:
1. <directive 1>
2. <directive 2>

=== AXIOM IMPACT: <NONE / UPDATE REQUIRED / ⛔ VIOLATION> ===
<详情见上述三级评级>

Proposed spec changes:
  <param>: <old> → <new>

Affected code files:
  - <file>: <变更描述>

ACTION REQUIRED: Please confirm spec update (yes/no)
```
