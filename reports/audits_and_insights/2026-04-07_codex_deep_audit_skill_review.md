# Codex Review: `/deep-audit` Claude Code Skill Design

Audit target: `.claude/skills/deep-audit/deep-audit.md`

Context checked: `CLAUDE.md` sections 15b/16 and Living Harness architecture, `OMEGA_LESSONS.md`, representative `rules/active/*.yaml`, `architect/INDEX.md`, `architect/insights/INDEX.md`, and the existing `/dev-cycle`, `/axiom-audit`, and `/harness-reflect` skill files.

## 1. Four-round iteration loop (Round 1-4)

**Verdict: WARNING**

**Reasoning:** The skill has a strong prompt-level guard: its core principles require `file:line` citations, re-reading after computation/reasoning, and self-reading of key data rather than trusting other agents (`deep-audit.md:16-20`). The four-round prompt also requires Round 1 Read extraction, Round 2 adversarial Grep, Round 3 re-reading numeric source values, and Round 4 conclusions only after Rounds 1-3 (`deep-audit.md:86-117`). However, this is not a hard enforcement mechanism: Round 4 asks for a "验证轨迹" but does not require the coordinator to inspect actual Read/Grep tool traces before accepting it (`deep-audit.md:109-117`). There are loopholes: Round 2 allows "搜索无结果: 标注 [UNVERIFIED]" without a next mandatory source read, and Round 3 only forces re-read for numeric claims while code claims use Grep and non-numeric conceptual claims have no explicit re-read trigger unless a contradiction appears (`deep-audit.md:98-107`).

**Recommendation:** Add a coordinator-side acceptance gate: each sub-agent conclusion must include a per-round evidence table with cited Read/Grep calls, and the coordinator must spot-check at least one citation per key claim before accepting Round 4. Require `[UNVERIFIED]` items to become `LOW` confidence automatically, not silently pass into the final report.

## 2. Sub-agent context isolation

**Verdict: WARNING**

**Reasoning:** The skill claims each subproblem starts an independent `general-purpose` sub-agent and states the child context is "完全隔离" and cannot remember others' reads (`deep-audit.md:73-80`). **UNKNOWN:** I cannot verify from this skill file whether Claude Code's sub-agent implementation guarantees complete context isolation, because the skill gives no invocation syntax, API flag, or execution contract beyond the textual assertion in Stage 2.1 (`deep-audit.md:75-80`). Even if context isolation exists, the prompt can still inject framing: Stage 2.2 sends the child specified files and the four-round instructions, and Stage 3 arbitration sends "两个矛盾结论" to the arbitrator, so the agents are not source-only by construction (`deep-audit.md:84-90`, `deep-audit.md:133-136`).

**Recommendation:** Replace absolute wording like "不可能记住" with a concrete invocation recipe and an `UNKNOWN/ASSUMED` caveat. Add a rule that sub-agents receive only the question, source file list, and required citation format when possible; if prior conclusions are provided, label that as a bias risk.

## 3. Stage 1 audit planning

**Verdict: WARNING**

**Reasoning:** Stage 1 correctly separates planning from full reading and instructs the coordinator to read navigation files first (`deep-audit.md:33-43`). It then requires 3-5 subquestions with exact files, paragraph ranges, numeric/formula/logical checks, and validation methods (`deep-audit.md:45-52`). The weak point is that it forbids immediate full document reading but still asks for precise line/paragraph ranges from indexes alone; the listed indexes may link to files, but the skill does not define a fallback when an index is stale, missing, or insufficient to identify concrete ranges (`deep-audit.md:35-43`, `deep-audit.md:49-52`). It also omits key navigation sources from the project's Meta-Harness architecture: `CLAUDE.md` identifies `OMEGA_LESSONS.md`, `incidents/`, `rules/active/`, and `architect/chain_of_custody.yaml` as core context, while Stage 1 only lists handover/reports/architect timeline indexes (`CLAUDE.md:124-129`, `deep-audit.md:39-43`).

**Recommendation:** Add a Stage 1.1b "navigation expansion" step: read `architect/insights/INDEX.md`, `architect/chain_of_custody.yaml`, and topic-relevant `OMEGA_LESSONS.md` sections before finalizing subquestions. Allow a small targeted preview read of candidate files' headings around linked sections so the plan's line ranges are grounded rather than guessed.

## 4. Stage 3 arbitration mechanism

**Verdict: WARNING**

**Reasoning:** Stage 3 detects contradictions across sub-agent conclusions and starts an arbitration agent when a contradiction is found (`deep-audit.md:127-136`). The arbitrator receives two conflicting conclusions without labels, a source file list, and an instruction to independently Read source files rather than trusting summaries (`deep-audit.md:133-136`). Not labeling "who is who" only reduces one bias channel; it does not remove bias from wording, citation choices, confidence language, or argument structure because the skill still gives the arbitrator the prior conclusions themselves (`deep-audit.md:133-136`). The final report template only says to include arbitration results under "矛盾与分歧" and does not specify an arbitration rubric, tie-break rule, or required citation verification depth (`deep-audit.md:138-150`).

**Recommendation:** Normalize conflicting claims into a citation-stripped issue table before arbitration, and make the arbitrator independently reconstruct the evidence from sources before seeing the original conclusions. Add a rubric: factual conflict, interpretation conflict, missing evidence, and final status with required citations.

## 5. Termination guarantees

**Verdict: FAIL**

**Reasoning:** The four-round loop can recurse without a bound: Round 3 says contradictions send the agent back to Round 1, but the skill gives no maximum retry count, time budget, or escalation threshold (`deep-audit.md:102-107`). LOW confidence handling is also unbounded: the coordinator may supplement materials and continue the same agent or start a new agent, again with no cap (`deep-audit.md:119-124`). Stage 1 intentionally waits for user plan confirmation, which is acceptable as a human gate, but after Stage 2 begins there is no comparable stop condition for repeated contradiction/LOW cycles (`deep-audit.md:67`, `deep-audit.md:119-124`). This is weaker than the existing `/dev-cycle`, which explicitly caps audit/fix loops at 3 and pauses for user input (`.claude/skills/dev-cycle/SKILL.md:100-105`, `.claude/skills/dev-cycle/SKILL.md:139-144`, `.claude/skills/dev-cycle/SKILL.md:243-249`).

**Recommendation:** Add hard limits: maximum 2 re-read loops per sub-agent, maximum 1 arbitration retry per contradiction, and maximum 1 LOW-confidence continuation before escalation to the final report as unresolved. Require the coordinator to stop and ask the user if the limits are reached.

## 6. Hardcoded specifics

**Verdict: PASS**

**Reasoning:** The skill hardcodes project navigation files and the output path template, but those are appropriate for a repository-local skill whose core method is INDEX navigation and whose report destination is fixed (`deep-audit.md:13-14`, `deep-audit.md:39-43`, `deep-audit.md:152-155`). The examples of audit topics are generic and do not pin the workflow to a specific Phase, experiment number, or brittle line number (`deep-audit.md:24-30`). The relationship section names `/dev-cycle`, `/axiom-audit`, `/deep-audit`, and three-way external audit categories, which is appropriate workflow taxonomy rather than an accidental hardcoded Phase dependency (`deep-audit.md:158-166`). I did not find inappropriate hardcoded line numbers or Phase numbers in the skill's operative instructions (`deep-audit.md:33-155`).

**Recommendation:** None.

## 7. Overlap with existing workflows

**Verdict: FAIL**

**Reasoning:** The skill's relationship section tries to scope `/dev-cycle` to new code, `/axiom-audit` to physical axiom invariance, and `/deep-audit` to fundamental assumptions (`deep-audit.md:158-163`). But the skill's own input examples include "某个代码实现是否与 spec 对齐?", which overlaps directly with `/dev-cycle` Stage 8.5 spec-code alignment and `/axiom-audit` Layer B spec-code consistency (`deep-audit.md:26-30`, `.claude/skills/dev-cycle/SKILL.md:186-220`, `.claude/skills/axiom-audit/SKILL.md:40-51`). It also says existing tools are all "跑一次出结果" and `/deep-audit` is the only forced iterative loop, which is overbroad because `/dev-cycle` already loops on failed plan/code audits and caps retries (`deep-audit.md:165-166`, `.claude/skills/dev-cycle/SKILL.md:42`, `.claude/skills/dev-cycle/SKILL.md:98-105`, `.claude/skills/dev-cycle/SKILL.md:137-144`). Most importantly, the skill does not state that `/deep-audit` cannot replace `CLAUDE.md` section 15b's mandatory Codex+Gemini Plan/Spec external audit or section 16's mandatory `/dev-cycle` for new code/new Phase (`deep-audit.md:158-166`, `CLAUDE.md:62-70`).

**Recommendation:** Add a "non-substitution" gate: if the topic involves new code, new Phase, Plan/Spec changes, or spec-code alignment, `/deep-audit` may only produce advisory findings and must hand off to `/dev-cycle` and/or `/axiom-audit` for required PASS/FAIL gates. Rewrite the "现有工具都是跑一次出结果" claim to distinguish external one-shot audits from existing iterative workflows.

## 8. Missing elements

**Verdict: FAIL**

**Reasoning:** The skill lacks a coordinator verification step for citations: it requires sub-agents to produce citations, but Stage 3 only summarizes conclusions and does not require re-opening cited lines before the final report (`deep-audit.md:109-117`, `deep-audit.md:138-150`). It omits Living Harness inputs from planning even though `CLAUDE.md` defines the Meta-Harness memory layer, rule engine, evolution layer, and chain-of-custody as core architecture (`deep-audit.md:39-43`, `CLAUDE.md:98-128`). It does not mention `OMEGA_LESSONS.md` or `rules/active/`, despite the project constitution and lessons index treating them as the experience source and executable rule engine (`deep-audit.md:39-43`, `CLAUDE.md:19-21`, `OMEGA_LESSONS.md:25-52`). It also lacks a report index update step: the skill writes a report file but does not instruct updating `reports/audits_and_insights/INDEX.md`, even though Stage 3.3 defines a persistent report path (`deep-audit.md:152-155`).

**Recommendation:** Add a Stage 0 preflight that reads topic-relevant `OMEGA_LESSONS.md` entries, matching `rules/active/*.yaml`, and `architect/chain_of_custody.yaml` when the topic touches directives/spec/code. Add a finalization checklist: citation spot-check, unresolved LOW list, non-substitution workflow check, and optional `reports/audits_and_insights/INDEX.md` update.

## Overall Assessment

The `/deep-audit` skill is directionally useful as an advisory deep-review prompt because it explicitly pushes agents toward INDEX navigation, line-cited evidence, repeated source reads, adversarial search, and arbitration (`deep-audit.md:13-20`, `deep-audit.md:84-117`, `deep-audit.md:127-150`). It is not ready as a hard governance workflow because its most important controls are prompt-level only, context isolation is asserted but not technically specified, retry loops are unbounded, and overlap with `/dev-cycle` and `/axiom-audit` is not guarded against (`deep-audit.md:75-80`, `deep-audit.md:102-124`, `deep-audit.md:158-166`). Before relying on it for project-critical audit decisions, add bounded termination, coordinator-side citation verification, explicit non-substitution rules for `CLAUDE.md` 15b/16 gates, and integration with the Meta-Harness navigation sources (`CLAUDE.md:62-70`, `CLAUDE.md:98-128`, `deep-audit.md:39-43`).
