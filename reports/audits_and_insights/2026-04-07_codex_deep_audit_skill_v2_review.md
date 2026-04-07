# Deep-Audit Skill V2 Second-Round Audit

Date: 2026-04-07
File audited: `.claude/skills/deep-audit/deep-audit.md`
Audit type: second-round verification of claimed V2 fixes

Project context checked: `CLAUDE.md` Ω5 external audit rules, `/dev-cycle`, `/axiom-audit`, and Rule Engine/Living Harness references; prior audit report `reports/audits_and_insights/2026-04-07_codex_deep_audit_skill_review.md`.

## Per-Item Verification

### FAIL#5 — Termination guarantee
**Claimed fix**: Added hard caps: 2 Round 3 to Round 1 fallbacks, 1 LOW-confidence continuation, 1 arbitration retry.
**Evidence in V2**:
> `.claude/skills/deep-audit/deep-audit.md:149-156`: "### 2.3 终止保证 (Codex FAIL #5 修正)" ... "每个子 agent 的 Round 3→Round 1 回退: **最多 2 次**" ... "LOW 置信度的 SendMessage 继续: **最多 1 次**" ... "Stage 3 仲裁重试: **最多 1 次**" ... "超过任何上限 → 标注 [UNRESOLVED] 写入最终报告，不再循环" ... "如果 >50% 子问题为 LOW/UNRESOLVED → **暂停并征求用户意见**"
**Verdict**: PASS
**Notes**: The unbounded loop from the prior audit is directly addressed by explicit retry caps plus a required stop state in `deep-audit.md:151-156`. The `SendMessage` continuation mechanism is not otherwise expanded, but the stop rule in `deep-audit.md:155` is sufficient for the claimed termination guarantee.

### FAIL#7 — Overlap with existing workflows
**Claimed fix**: Added advisory positioning and a non-replacement declaration.
**Evidence in V2**:
> `.claude/skills/deep-audit/deep-audit.md:30-33`: "`/deep-audit` 仅产出**咨询性 (advisory) 发现**" ... "如果审计涉及新代码、新 Phase、Plan/Spec 变更或 spec-code 对齐，`/deep-audit` 的发现必须交由 `/dev-cycle` 或 `/axiom-audit` 做正式 PASS/FAIL 门禁。" ... "`/deep-audit` 不替代 CLAUDE.md 规定的 Codex+Gemini 外部审计。"
>
> `.claude/skills/deep-audit/deep-audit.md:204-214`: the relationship table marks `/dev-cycle` and `/axiom-audit` as "**正式门禁** (PASS/FAIL)" and `/deep-audit` as "**咨询性** (advisory)", followed by "**非替代声明**: `/deep-audit` 不替代任何 CLAUDE.md 规定的强制流程。"
**Verdict**: PASS
**Notes**: This now aligns with `CLAUDE.md:62-70`, which requires Codex+Gemini external audit for Plan/Spec changes and `/dev-cycle` for new code/new Phase; `/dev-cycle` itself defines PASS/FAIL gates and external audit stages in `.claude/skills/dev-cycle/SKILL.md:40-43` and `.claude/skills/dev-cycle/SKILL.md:161-185`. It also avoids replacing the Rule Engine because V2 only checks `rules/active/` during Stage 0 (`deep-audit.md:41-44`), while `CLAUDE.md:87-91` and `CLAUDE.md:98-104` define the Rule Engine as a separate Hook/script-enforced layer. Minor wording remains in `deep-audit.md:214` claiming other tools are single-round in the audit step, but the formal non-replacement gate is sufficient to fix the previous workflow-overlap FAIL.

### FAIL#8 — Omissions
**Claimed fix**: Added Stage 0 pre-check, coordinator citation spot-check, and `INDEX` update.
**Evidence in V2**:
> `.claude/skills/deep-audit/deep-audit.md:37-44`: "## Stage 0: 预检 (Codex FAIL #8 修正)" ... search `OMEGA_LESSONS.md`, check `rules/active/`, check `architect/chain_of_custody.yaml`, and record related findings.
>
> `.claude/skills/deep-audit/deep-audit.md:162-167`: "### 3.1 协调者引用抽查 (Codex FAIL #8 修正)" ... "随机抽查 1-2 个 file:line 引用 → 自己 Read 确认引用准确" ... "如果引用不准确 → 该子 agent 结论降级为 LOW"
>
> `.claude/skills/deep-audit/deep-audit.md:195-199`: "### 3.4 落盘 + 索引更新" ... write the report under `reports/audits_and_insights/` and update `reports/audits_and_insights/INDEX.md`.
**Verdict**: PASS
**Notes**: The three missing controls named in the claimed fix are present and operational: Harness pre-check inputs in `deep-audit.md:41-44`, coordinator-side citation validation in `deep-audit.md:164-167`, and report index update in `deep-audit.md:195-199`. V2 still does not explicitly mention `incidents/`, but the prior concrete recommendation centered on `OMEGA_LESSONS.md`, `rules/active/`, `chain_of_custody`, citation spot-checking, and report indexing, all of which are now covered.

### WARNING#1 — Loop hole for UNVERIFIED and evidence trail
**Claimed fix**: `UNVERIFIED` auto-downgrades to `LOW` and the final output includes an evidence table.
**Evidence in V2**:
> `.claude/skills/deep-audit/deep-audit.md:124`: "搜索无结果: 标注 [UNVERIFIED] → 自动降级为 LOW 置信度"
>
> `.claude/skills/deep-audit/deep-audit.md:127-133`: Round 3 requires re-reading source numbers, source definitions/context for conceptual judgments, and sending contradictions back to Round 1 with a maximum of 2 fallbacks.
>
> `.claude/skills/deep-audit/deep-audit.md:140-147`: the conclusion format includes confidence labels and a "证据表" with R1/R2/R3 tool-call rows.
**Verdict**: PARTIAL
**Notes**: The auto-downgrade and evidence table are present in `deep-audit.md:124` and `deep-audit.md:142-147`. However, V2 introduces an internal contradiction: `deep-audit.md:124` says `UNVERIFIED` becomes `LOW`, while `deep-audit.md:140` says `MEDIUM` includes "有小矛盾或 UNVERIFIED". This weakens the sufficiency of the fix because the final confidence rubric can override the earlier auto-downgrade.

### WARNING#2 — Sub-agent context isolation
**Claimed fix**: Do not give sub-agents other agents' conclusions; provide only the problem and file list.
**Evidence in V2**:
> `.claude/skills/deep-audit/deep-audit.md:102-104`: "子 agent 通过 Claude Code 的 Agent 工具启动，获得独立上下文。" ... "每个子 agent 只收到: (1) 它负责的子问题 (2) 源文件列表 (3) 四轮循环规则。" ... "**不给子 agent 发送其他 agent 的结论或父级的分析——防止偏见注入。**"
**Verdict**: PARTIAL
**Notes**: V2 fixes the prompt-level conclusion leakage by restricting child-agent inputs in `deep-audit.md:103-104`. The remaining gap is technical: `deep-audit.md:102` still asserts "获得独立上下文" without an invocation recipe, API guarantee, or `ASSUMED/UNKNOWN` caveat, so the implementation-level context-isolation part of the prior warning is not fully resolved from the skill text alone.

### WARNING#3 — Stage 1 navigation
**Claimed fix**: Added `architect/insights/INDEX.md`, `chain_of_custody`, and candidate file preview.
**Evidence in V2**:
> `.claude/skills/deep-audit/deep-audit.md:41-44`: Stage 0 searches lessons, rules, and `architect/chain_of_custody.yaml`, then records findings for Stage 1 planning.
>
> `.claude/skills/deep-audit/deep-audit.md:54-62`: Stage 1 reads navigation files including `reports/audits_and_insights/INDEX.md`, `architect/INDEX.md`, and `architect/insights/INDEX.md`; for candidate files, it allows reading titles/table of contents in the first 30 lines to confirm ranges and avoid guessing line numbers from indexes.
>
> `.claude/skills/deep-audit/deep-audit.md:66`: subquestions are derived from "审计主题 + Stage 0 发现".
**Verdict**: PASS
**Notes**: The new navigation inputs are present and connected to planning. `chain_of_custody` is in Stage 0 rather than the Stage 1 list, but `deep-audit.md:66` explicitly feeds Stage 0 findings into Stage 1 subproblem decomposition, so the fix is sufficient.

### WARNING#4 — Arbitration bias
**Claimed fix**: Use a standardized dispute description and do not show raw conclusion text to the arbitrator.
**Evidence in V2**:
> `.claude/skills/deep-audit/deep-audit.md:172-178`: when contradictions exist, the workflow starts an arbitration agent and "**不给仲裁者看原始结论文本**", giving only a standardized dispute description such as "关于 X 参数，存在两种判断: 判断 A (值=Y) vs 判断 B (值=Z)。请从源文件独立判断。", plus source files and the four-round loop rule.
**Verdict**: PASS
**Notes**: This directly addresses the prior bias channel from raw conclusion text. The arbitrator still sees the existence of two candidate judgments in `deep-audit.md:173-174`, but that is necessary to define the dispute and is materially less biased than forwarding full agent conclusions.

## New Issues Introduced by V2

1. **Conflicting `UNVERIFIED` confidence semantics.** V2 adds the desired auto-LOW rule in `deep-audit.md:124`, but the Round 4 rubric in `deep-audit.md:140` simultaneously classifies `UNVERIFIED` as `MEDIUM`. This appears V2-specific because it is tied to the newly added auto-downgrade/evidence-table fix and creates ambiguity at final report time.

No other new V2-specific issue was found that is both material and directly supported by the skill text.

## Summary Table

| item | claimed fix | verdict |
|---|---|---|
| FAIL#5 | hard caps: 2 fallbacks / 1 LOW continuation / 1 arbitration retry | PASS |
| FAIL#7 | advisory positioning + non-replacement declaration | PASS |
| FAIL#8 | Stage 0 pre-check + coordinator citation spot-check + INDEX update | PASS |
| WARNING#1 | `UNVERIFIED` auto-downgrades to LOW + evidence table | PARTIAL |
| WARNING#2 | sub-agents receive only problem/file list/rules, not others' conclusions | PARTIAL |
| WARNING#3 | insights INDEX + chain_of_custody + candidate file preview | PASS |
| WARNING#4 | standardized dispute description, no raw conclusion text | PASS |

## Overall Verdict

Overall verdict: **PARTIAL PASS**.

Recommendation: accept V2 as materially improved for advisory use after two text edits: make `UNVERIFIED` consistently `LOW` in the Round 4 confidence rubric (`deep-audit.md:140`), and add a short caveat or invocation recipe for the claimed independent child-agent context (`deep-audit.md:102-104`). The three prior FAIL items are fixed sufficiently in V2; no item remains `STILL-FAIL`.
