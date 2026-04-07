---
name: deep-audit
description: "迭代式深度审计 — 强制 agent 反复阅读-思考-验证-再阅读，拒绝一次性读完凭记忆审计"
user-invocable: true
---

# /deep-audit — 迭代式深度审计

## 核心原则

**Agent 不可以读一次文件就凭记忆审计。**

本项目的文档和代码规模远超任何 agent 的单次阅读能力。
必须通过 INDEX 导航 → 精确段落读取 → 迭代验证来工作。

每个判断必须：
1. 附带 `file:line` 精确引用——给不出引用 = 必须重新 Read
2. 计算/推理后必须回到源数据 Read 验证
3. 验证失败必须重新阅读再启动推理
4. 不信任其他 agent 的文字摘要——对关键数据必须自己 Read 原文

---

## 输入

用户提供审计主题。例如：
- `/deep-audit 数学核心是否需要重设计？`
- `/deep-audit 最近一次实验结果是否可信？`

**范围限制**: `/deep-audit` 仅产出**咨询性 (advisory) 发现**。
如果审计涉及新代码、新 Phase、Plan/Spec 变更或 spec-code 对齐，
`/deep-audit` 的发现必须交由 `/dev-cycle` 或 `/axiom-audit` 做正式 PASS/FAIL 门禁。
`/deep-audit` 不替代 CLAUDE.md 规定的 Codex+Gemini 外部审计。

---

## Stage 0: 预检 (Codex FAIL #8 修正)

在任何阅读之前，快速扫描项目知识库的相关条目:

1. 在 `OMEGA_LESSONS.md` 中搜索与审计主题相关的教训 (Grep 关键词)
2. 在 `rules/active/` 中检查是否有相关执法规则
3. 在 `architect/chain_of_custody.yaml` 中检查审计主题涉及的指令链
4. 记录发现的相关条目——供 Stage 1 规划时参考

---

## Stage 1: 协调者规划审计

**不立即深入阅读文档。先做审计规划。**

### 1.1 快速定位

读取以下导航文件获取全局视图 (只读索引，不读全文):
- `handover/LATEST.md` — 当前状态
- `reports/INDEX.md` — 全部实验结果导航
- `reports/audits_and_insights/INDEX.md` — 审计报告导航
- `architect/INDEX.md` — 架构师指令时间线
- `architect/insights/INDEX.md` — 决策卡片导航

对于候选文件，可以先 Read 其标题/目录 (前 30 行) 来确认段落范围，
不要凭 INDEX 猜测行号。

### 1.2 分解子问题

根据审计主题 + Stage 0 发现，分解为 **3-5 个具体子问题**。

对每个子问题，指定：
- **必须阅读的精确文件 + 段落范围**
- **需要验证的具体数字/公式/逻辑**
- **验证方法**: 对比文件 A 和文件 B? 重新计算? Grep 代码默认值?

### 1.3 输出审计 Plan

```
=== AUDIT PLAN ===
主题: <审计主题>
Stage 0 相关发现: <教训/规则/指令链摘要>

Q1: <具体问题>
  读取: file1 (lines X-Y), file2 (section Z)
  验证: <对比/计算/grep>
  
Q2: ...
```

### 1.4 用户确认门禁

**将 Audit Plan 展示给用户。必须等用户确认后才进入 Stage 2。**
用户可以修改子问题、调整阅读范围、增减验证方法。

---

## Stage 2: 多 Agent 迭代审计

### 2.1 启动子 Agent

对每个子问题启动一个**独立子 agent** (general-purpose 类型)。
- 独立子问题**并行启动**
- 有依赖关系的**串行启动**

子 agent 通过 Claude Code 的 Agent 工具启动 (subagent_type: general-purpose)。
Agent 工具启动的子 agent 获得独立上下文窗口，不继承父级对话历史。
(技术前提: Claude Code Agent 工具的设计保证。如果行为不符预期，标注为实现风险。)
每个子 agent 只收到: (1) 它负责的子问题 (2) 源文件列表 (3) 四轮循环规则。
**不给子 agent 发送其他 agent 的结论或父级的分析——防止偏见注入。**

### 2.2 子 Agent 四轮迭代循环

每个子 agent 的 prompt 必须包含以下强制规则:

```
你是审计员。严格按以下 4 轮循环工作。不可跳步。不可合并。

═══ Round 1: 阅读与提取 ═══
- 使用 Read 工具读取指定文件的相关段落
- 提取每个关键数据点，记录 file:line
- 形成初步判断
- 写成结构化笔记 (不是散文)

═══ Round 2: 质疑自己 ═══
- 列出初步判断中 2-3 个最薄弱的环节
- 对每个薄弱环节:
  * 用 Grep 搜索可能推翻它的证据
  * 找到矛盾: 重新 Read 相关段落
  * 搜索无结果: 标注 [UNVERIFIED] → 自动降级为 LOW 置信度

═══ Round 3: 计算与验证 ═══
- 涉及数字: 从源文件重新 Read 提取，手动验算
  (不用 Round 1 记忆中的数字——必须重新 Read)
- 涉及代码: 用 Grep 确认代码中的实际默认值/实现
- 涉及概念性判断: 从源文件重新 Read 相关定义/上下文
- 对比 Round 1 判断 vs Round 2-3 新发现
- 有矛盾: 回到 Round 1 重新 Read 并修正
  **最多回退 2 次。第 2 次仍有矛盾 → 标注 [UNRESOLVED] 进入 Round 4**

═══ Round 4: 结论 ═══
- 仅在 Round 1-3 全部完成后才给出结论
- 格式:
  判定: [已证明 / 已否定 / 未测试 / 数据不足]
  引用: file:line (至少 2 处独立引用)
  置信度: HIGH (3轮一致) / MEDIUM (有小矛盾但已解决) / LOW (含 UNVERIFIED 或 UNRESOLVED 或数据缺失)
  如果 LOW: [NEEDS: 具体缺什么]
  证据表:
    | 轮次 | 工具调用 | 发现 |
    | R1 | Read file:lines | ... |
    | R2 | Grep pattern | ... |
    | R3 | Read file:lines (验算) | ... |
```

### 2.3 终止保证 (Codex FAIL #5 修正)

硬性上限:
- 每个子 agent 的 Round 3→Round 1 回退: **最多 2 次**
- LOW 置信度的 SendMessage 继续: **最多 1 次**
- Stage 3 仲裁重试: **最多 1 次**
- 超过任何上限 → 标注 [UNRESOLVED] 写入最终报告，不再循环
- 如果 >50% 子问题为 LOW/UNRESOLVED → **暂停并征求用户意见**

---

## Stage 3: 交叉验证 + 最终报告

### 3.1 协调者引用抽查 (Codex FAIL #8 修正)

在汇总前，协调者对每个子 agent 的关键结论:
- 随机抽查 1-2 个 file:line 引用 → 自己 Read 确认引用准确
- 如果引用不准确 → 该子 agent 结论降级为 LOW

### 3.2 矛盾检测与仲裁

检查不同子 agent 的结论是否矛盾。

如果矛盾: 启动**仲裁 agent**:
- **不给仲裁者看原始结论文本**——只给它一个标准化的争议描述:
  "关于 X 参数，存在两种判断: 判断 A (值=Y) vs 判断 B (值=Z)。请从源文件独立判断。"
- 给它源文件列表
- 让它独立 Read 源文件判断
- 仲裁 agent 也遵循四轮循环规则

### 3.3 汇总

```
=== DEEP AUDIT REPORT ===
主题: <审计主题>
日期: YYYY-MM-DD
性质: 咨询性 (advisory) — 不替代 /dev-cycle 或 /axiom-audit 的正式门禁

Q1-QN: 每个子问题的判定 + 引用 + 置信度 + 证据表

矛盾与分歧: (如有矛盾，附仲裁结果)
未解决项: (所有 LOW/UNRESOLVED 的汇总)
后续行动建议: (如需正式门禁，指向 /dev-cycle 或 /axiom-audit)
结论: <一段话总结>
```

### 3.4 落盘 + 索引更新

1. 写入 `reports/audits_and_insights/YYYY-MM-DD_deep_audit_<topic>.md`
2. 更新 `reports/audits_and_insights/INDEX.md` 添加新报告条目

---

## 与现有 Harness 的关系 (Codex FAIL #7 修正)

| 工具 | 场景 | 产出性质 | 迭代? |
|------|------|---------|-------|
| `/dev-cycle` | 开发新代码/新 Phase | **正式门禁** (PASS/FAIL) | 是 (3次上限) |
| `/axiom-audit` | 物理公理不变性 | **正式门禁** (PASS/FAIL) | 否 |
| `/deep-audit` | 质疑根本假设 | **咨询性** (advisory) | **是 (多轮迭代)** |
| 三方外审 | 外部独立意见 | **正式门禁** (PASS/FAIL) | 否 |

**非替代声明**: `/deep-audit` 不替代任何 CLAUDE.md 规定的强制流程。
如果 `/deep-audit` 的发现需要执行 (改代码/改 spec)，必须走 `/dev-cycle`。
如果发现涉及物理公理，必须走 `/axiom-audit`。
`/deep-audit` 的独特价值是**迭代深度**——其他工具在审计环节是单轮的。

---

## MCP 决策

**当前不建 MCP server。** Claude Code 内置 Read/Grep 每次调用都访问真实文件。
通过 INDEX 导航 + 精确 Read 段落可以高效访问全部文档。
如果未来文档规模增长到 INDEX 导航失效的程度，再考虑 MCP。
