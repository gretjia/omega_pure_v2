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
1. 更新 `architect/current_spec.yaml`
2. 运行 `python3 omega_axioms.py --verbose` 验证新 spec 一致性
3. 如果验证失败，回滚 spec 变更并报告

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
source_directive: <directive 文件名>
source_gdoc: <gdoc 文件名 or null>
---

# INS-NNN: <标题>

## 裁决
<一段话概括决策>

## 理由
<为什么这样做，物理/工程/哲学层面>

## 影响文件
<受影响的代码文件及变更描述>
```

同时更新 `architect/insights/INDEX.md` 索引表。

**一个 directive 可以产生多个 insights**（如 id5 产生了 INS-001/003/004/008 四个独立洞察）。

### 6. 列出受影响文件

输出需要变更的代码文件清单及变更描述。

### 7. 后续提醒

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
