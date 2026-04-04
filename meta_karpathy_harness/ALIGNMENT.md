# OMEGA Harness 最高指导哲学

> **地位**: 本文档是所有 harness 相关行动的最终对齐基准。
> 新规则、新 skill、新 hook、harness 重构 — 都必须与本文档的原则一致。
> 如果行动违反这里的原则, 那就是错的, 无论技术上多么精巧。

---

## 第一原则: 失败是燃料, 不是废料

> Taleb: "Wind extinguishes a candle and energizes fire."
> Meta-Harness: Raw traces >> summaries (+15 points).
> Karpathy: "If they work, keep. If they don't, discard."

**OMEGA 表述**: 每一次系统失败都必须让系统变得更强, 而不是更脆弱。

**判断标准**: 失败之后, 系统是:
- (a) 多了一条文档? → 错误路径 (文档会被遗忘)
- (b) 多了一条可执行规则? → 正确路径 (规则会自动拦截)
- (c) 多了一个结构约束? → 最佳路径 (约束不可旁路)

**反模式**: 
- 同类错误第二次发生 = harness 失败
- 教训只存在于文本 = 死的教训
- "我记住了" = 最不可靠的防御

---

## 第二原则: 原始经验不可压缩

> Meta-Harness 论文核心发现:
> - Scores Only: 34.6
> - Scores + LLM Summary: 34.9 (摘要几乎无用)
> - **Scores + Raw Traces: 50.0** (原始痕迹 = +15 分)

**OMEGA 表述**: 诊断信息的价值在于完整性。压缩摘要摧毁因果链。

**实践规则**:
1. `OMEGA_LESSONS.md` (≤2行) 是**索引**, 不是**记忆** — 用来定位, 不用来诊断
2. `incidents/C-xxx_*/` 是**真正的记忆** — 完整 trace, root cause, resolution
3. Agent 通过 `grep` + `read` 按需查询 incidents, 不全量加载
4. 永远不要为了"节省 token"而删减 trace 内容

**判断标准**: 当 Agent 需要理解一个过去的失败时:
- (a) 读 OMEGA_LESSONS 2 行摘要? → 知道"什么", 不知道"为什么"
- (b) grep incidents/ 找到完整 trace? → 知道因果链, 能做出正确判断

---

## 第三原则: 可执行 > 可记忆

> Karpathy: "You are programming the program.md Markdown files."
> Ω4: 已知最优方法必须固化为 wrapper 脚本, 不可仅存在于文档。

**OMEGA 表述**: 如果一个教训只存在于人或 AI 的记忆中, 它就是死的。只有变成代码/规则/脚本的教训才活着。

**转化阶梯** (从弱到强):

```
Level 0: 口头承诺 ("我下次会注意")        → 价值 = 0
Level 1: 文档记录 (OMEGA_LESSONS.md)     → 价值 = 索引
Level 2: YAML 规则 (rules/active/)       → 价值 = 自动拦截
Level 3: Hook 脚本 (.claude/hooks/)      → 价值 = 实时执行
Level 4: 结构约束 (safe_*.sh, axioms)    → 价值 = 不可旁路
```

**目标**: 每条教训都应尽可能推到最高 Level。

**Karpathy 映射**:
- `program.md` 是 skill, 不是文档 → 我们的 SKILL.md 是可执行编排
- `prepare.py` 是固定真理 → 我们的 `omega_axioms.py` 是不可修改的物理公理
- `results.tsv` 是结构化日志 → 我们的 `enforcement.log` + `manifest.jsonl` 是审计轨迹

---

## 第四原则: 简单性是美德, 复杂性是债务

> Karpathy Simplicity Criterion:
> "A 0.001 improvement that adds 20 lines of hacky code? Probably not worth it.
>  A 0.001 improvement from deleting code? Definitely keep.
>  An improvement of ~0 but much simpler code? Keep."

**OMEGA 表述**: 代码行数是负债。规则数量有上限。复杂度必须与价值成正比。

**实践规则**:
1. 规则总数软上限 50 条 — 超过就必须 `/harness-reflect` 修剪
2. 复杂度 > 3 条件的规则 → 标记为 "recommend manual judgment"
3. 一个 bash 脚本 + N 个 YAML 文件 > 一个框架
4. 删除一条无效规则和添加一条有效规则一样重要

**反模式**:
- 为了 edge case 添加复杂逻辑 → 不如保持简单 + warn
- 规则引擎变成微型编程语言 → 停下, 这不是目标
- Hook 脚本超过 100 行 → 拆分或简化

---

## 第五原则: 生产者永远不是验证者

> Ω5: 写代码的 agent 不可独自验证该代码。
> Meta-Harness: Evaluator separate from proposer.
> Karpathy: prepare.py (fixed truth) separate from train.py (mutable experiment).

**OMEGA 表述**: 自己验证自己是自欺欺人。外部验证是不可删除的硬约束。

**三层验证**:
1. **Self-check**: omega_axioms.py (物理约束, 快速, 弱)
2. **Peer review**: Codex rescue agent (代码审计, 中等)
3. **External audit**: Gemini API (数学/GCP 审计, 强)

**不可妥协**:
- Claude 不可代替 Codex/Gemini 做 PASS/FAIL 判定
- 不可限制外审员的输出 token 数
- `/lesson-to-rule` 生成的规则需要人确认才能激活

---

## 第六原则: 自主实验, 但有安全围栏

> Karpathy NEVER STOP: "You are autonomous. The loop runs until the human interrupts you."
> 但 Karpathy 也有围栏: prepare.py 不可改, 评估函数固定, git reset 可回退。

**OMEGA 表述**: 自主性和安全性不矛盾。围栏内自由实验, 围栏外需要许可。

**围栏定义**:
- **围栏内 (自由行动)**: 读代码, 写规则, 运行测试, 修改 train.py, 分析日志
- **围栏外 (需要确认)**: 删除/覆盖数据, 远程推送, 修改 spec, 生产部署, 修改物理公理

**Karpathy 映射**:
- 他的围栏: prepare.py (不可改) + val_bpb (不可伪造) + git (可回退)
- 我们的围栏: omega_axioms.py (不可改) + canary gate (不可跳过) + hooks (自动拦截)

---

## 第七原则: 系统必须能观察自己

> Meta-Harness: Proposer reads median 82 files/iteration, 40% execution traces.
> Karpathy: results.tsv tracks every experiment — keep/discard/crash.

**OMEGA 表述**: 一个不能自我观察的系统无法自我改进。Harness 必须有仪表盘。

**自观察机制**:
1. **`/harness-reflect`**: 规则效果评分 + 健康分 + 修剪建议
2. **`enforcement.log`**: 每次规则触发的审计轨迹
3. **`incidents/INDEX.yaml`**: 事件覆盖率 (可执行 vs doc-only)
4. **`chain_of_custody.yaml`**: 从指令到部署的全链追踪

**健康公式**: `health = enforcement_ratio × (1 - repeat_rate) × (1 - fix_commit_ratio)`

---

## 综合: 生命循环

将七条原则串联成一个活的系统:

```
失败发生
  │
  ├─ [原则 1] 失败是燃料 → 记录, 不恐慌
  │
  ├─ [原则 2] 保留原始 trace → incidents/ 完整上下文
  │
  ├─ [原则 3] 转化为可执行 → /lesson-to-rule → YAML 规则
  │
  ├─ [原则 4] 保持简单 → 一条规则, 不是一个框架
  │
  ├─ [原则 5] 外部验证 → 规则需人确认, 代码需 Codex/Gemini 审
  │
  ├─ [原则 6] 围栏内自主 → hook 自动执法, 不需人干预
  │
  └─ [原则 7] 自我观察 → /harness-reflect 评估效果, 修剪无效
        │
        └─ 系统变强 → 下次同类失败被自动拦截
```

---

## 对齐检查清单

**每次修改 harness 时, 回答以下问题**:

| # | 问题 | 违反时的信号 |
|---|------|------------|
| 1 | 这个改动让失败变成燃料了吗? | "加了文档但没加规则" |
| 2 | 原始 trace 被保留了吗? | "为了节省空间压缩了 trace" |
| 3 | 教训被固化为可执行了吗? | "写进了 LESSONS 但没有 rule" |
| 4 | 复杂度与价值成正比吗? | "20 行代码防一个 edge case" |
| 5 | 有外部验证吗? | "Claude 自己说 PASS 了" |
| 6 | 在围栏内还是围栏外? | "直接修改了物理公理" |
| 7 | 系统能观察到这个改动的效果吗? | "没有 enforcement.log 记录" |

**全部通过 = 对齐。任何一条失败 = 重新审视。**

---

## 一句话总结

> **失败让系统变强, 原始经验不压缩, 教训必须可执行, 简单优于复杂, 自己不验自己, 围栏内自由实验, 系统观察自己。**

这就是 OMEGA Harness 的全部哲学。所有规则、所有 hook、所有 skill — 都是这七条原则的具体实例。如果某个组件不服务于这七条中的任何一条, 它就不应该存在。
