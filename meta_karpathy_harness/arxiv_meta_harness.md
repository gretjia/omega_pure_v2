# Meta-Harness: End-to-End Optimization of Model Harnesses

> **原文归档**: https://arxiv.org/html/2603.28052v1
> **arXiv ID**: 2603.28052v1 | **Date**: March 30, 2026 | **License**: CC BY 4.0
> **归档目的**: OMEGA Living Harness 的学术灵感来源之一。核心洞察直接塑造了我们的 Trace Vault 和 filesystem-as-memory 设计。

---

## Authors

Yoonho Lee (Stanford), Roshen Nair (Stanford), Qizheng Zhang (Stanford), Kangwook Lee (KRAFTON), Omar Khattab (MIT), Chelsea Finn (Stanford)

---

## Abstract

The paper introduces Meta-Harness, a system that automates the optimization of harnesses — code determining what information LLMs store, retrieve, and receive. Unlike existing text optimizers that compress feedback aggressively, Meta-Harness uses an agentic proposer accessing prior candidates' source code, scores, and execution traces through a filesystem. Results demonstrate: 7.7-point improvement over ACE on online text classification using 4x fewer tokens; 4.7-point average gain across five models on 200 IMO-level math problems; and superior performance on TerminalBench-2 agentic coding tasks.

---

## 1. Introduction

Harness choice produces **6x performance gap on the same benchmark**. Current approaches rely on manual engineering. Meta-Harness exposes "full history through a filesystem, enabling selective diagnosis of raw prior code and execution traces rather than optimization from compressed per-candidate summaries."

Key innovations:
- Proposer reads **median of 82 files per iteration**, referencing 20+ prior candidates
- Single evaluations generate **up to 10,000,000 tokens** of diagnostic information
- Three orders of magnitude beyond prior text optimization budgets (0.002-0.026M tokens/iteration)

---

## 2. Related Work

Positioned at the intersection of:
- **External memory and adaptive access**: RAG, interleaved retrieval, memory-based agents
- **Executable code search**: Distinguished from prior program search (AlphaEvolve, OpenEvolve) by targeting domain-specific harnesses
- **Text optimization methods**: ProTeGi, TextGrad, OPRO, GEPA, AlphaEvolve, Feedback Descent — all use compressed feedback

---

## 3. Method: A Harness for Optimizing Harnesses

### Objective

```
H* = arg max_H E_{x~X, τ~p_M(H,x)} r(τ, x)
```

Where H = harness, M = fixed model, X = task distribution, r = reward function.

### Search Loop (Algorithm 1)

1. Initialize harness population H
2. Initialize empty filesystem D
3. For each harness H in initial population: evaluate and store results
4. For t = 1 to N iterations:
   - Proposer queries filesystem (grep, cat — selective, not monolithic)
   - Proposes k new harnesses
   - Validate and evaluate accepted harnesses
5. Return Pareto frontier

### Proposer

Claude Code with Opus-4.6 capabilities, guided by minimal domain-specific skills.

### Filesystem Structure

Each evaluated harness stores:
- **Source code**
- **Evaluation scores**
- **Execution traces** (prompts, tool calls, model outputs, state updates)

### Key Advantages

- Proposers can infer **"why"** harnesses failed, not just "that" they failed
- Inspection of execution traces enables **causal reasoning**
- Coding models produce **coherent algorithms** rather than brittle prompt strings
- Natural regularization bias toward **reusable procedures**

---

## 4. Experiments

### 4.1 Online Text Classification

**Base model**: GPT-OSS-120B | **Config**: 20 iterations x 2 candidates = 40 evaluations

| Harness | USPTO | S2D | Law | **Avg Acc** | Context (K) |
|---------|-------|-----|-----|-------------|-------------|
| Zero-Shot | 12.0 | 63.2 | 7.0 | 27.4 | 0 |
| Few-Shot (32) | 13.0 | 72.2 | 21.0 | 35.4 | 7.9 |
| MCE | 14.0 | 83.0 | 23.0 | 40.0 | 28.5 |
| ACE | 16.0 | 77.8 | 29.0 | 40.9 | 50.8 |
| **Meta-Harness** | **14.0** | **86.8** | **45.0** | **48.6** | **11.4** |

**+7.7 points over ACE, using 4x fewer tokens.**

### 4.2 Mathematical Reasoning (Retrieval-Augmented)

40 iterations on 250-problem search set → 109 candidates. Evaluated on 200 IMO-level problems.

| Method | GPT-5.4n | GPT-5.4m | Gem-3.1FL | Gem-3F | GPT-20B | **Avg** |
|--------|----------|----------|-----------|--------|---------|---------|
| No Retriever | 23.0 | 28.8 | 28.6 | 42.6 | 47.6 | 34.1 |
| Dense Ret. (k=5) | 31.1 | 28.3 | 37.1 | 47.2 | 46.7 | 38.1 |
| BM25 | 30.2 | 29.2 | 32.8 | 46.6 | 48.9 | 37.5 |
| **Meta-Harness** | **31.7** | **30.4** | **34.9** | **46.3** | **50.6** | **38.8** |

**+4.7 points average across 5 held-out models** — single discovered policy generalizes cross-model.

### 4.3 Agentic Coding (TerminalBench-2)

**Opus 4.6**: Meta-Harness 76.4% (#2), Terminus-KIRA 74.7%
**Haiku 4.5**: Meta-Harness 37.6% (#1 on leaderboard)

---

## 5. Ablation: Raw Traces Are Essential

> **OMEGA 核心引用 — 直接影响 Trace Vault 设计**

| Condition | Median Acc | Best Acc |
|-----------|-----------|----------|
| Scores Only | 34.6 | 41.3 |
| Scores + LLM Summary | 34.9 | 38.7 |
| **Scores + Raw Traces (Full Meta-Harness)** | **50.0** | **56.7** |

**结论**: LLM-generated summaries destroy diagnostic information. Raw traces (+15 points over summaries) are essential.

**OMEGA 映射**:
- `OMEGA_LESSONS.md` (≤2行/条) = Scores + Summary = **死的记忆**
- `incidents/` Trace Vault (完整上下文) = Raw Traces = **活的记忆**
- 两者并存: LESSONS 做索引, Trace Vault 做诊断

---

## 6. Qualitative Analysis: Causal Reasoning (Appendix A.2)

TerminalBench-2 search log demonstrates proposer:

1. **Iterations 1-2**: Bundles structural fixes with prompt changes → both regress from 64.4%
2. **Iteration 3**: Identifies confound — "Root cause: Prompt changes caused agent to delete necessary state"
3. **Iterations 4-6**: Tests causal hypothesis, continues regressing due to control-flow issues
4. **Iteration 7**: Pivots to **purely additive** environment bootstrapping → best result (67.3%)
5. **Iteration 8**: Composes winning additive fix with earlier structural changes
6. **Iteration 10**: References and transfers lessons across separate runs

**OMEGA 映射**: This is exactly what `/harness-reflect` + `/lesson-to-rule` does:
- Diagnose root cause from raw traces (not summaries)
- Isolate confounding variables
- Prefer additive improvements (new rules) over destructive rewrites
- Transfer lessons across sessions

---

## 7. File Access Statistics (Appendix A, Table 8)

| Statistic | Value |
|-----------|-------|
| Files read/iteration (median) | 82 |
| Files read/iteration (range) | 69-99 |
| **Harness source code** | **41%** |
| **Execution traces** | **40%** |
| Score/summary files | 6% |
| Other | 13% |

**结论**: 81% of reads go to source code + traces. Only 6% to summaries.

---

## 8. Discovered Harness Examples

### Text Classification (Pareto frontier, 8 variants)

**Label-Primed Query** (best accuracy):
- List all valid output labels upfront
- One query-relevant example per label
- Contrastive pairs: similar examples with different labels
- TF-IDF retrieval with query-anchored pairing
- 45.5K tokens, 48.6% accuracy

**Draft Verification** (best efficiency):
- Stage 1: Retrieve 5 nearest, make draft prediction
- Stage 2: Retrieve confirmers + challengers, verify/revise
- 5.4K tokens, 40.1% accuracy

### Math Retrieval

Four-route BM25 with lexical routing (Combinatorics/Geometry/Number Theory/Algebra), math-aware tokenizer preserving LaTeX as atomic units.

### TerminalBench-2

Main modification: **environment bootstrapping before agent loop** — snapshot working directory, list /app, detect available languages/package managers, check memory. Eliminates 2-4 exploratory turns. ~80 lines of code.

---

## 9. OOD Generalization (Table 5)

| Harness | Avg Acc (9 new datasets) | Context |
|---------|--------------------------|---------|
| Zero-shot | 67.0 | — |
| Few-shot (32) | 69.6 | 5.2 |
| ACE | 70.2 | 11.7 |
| **Meta-Harness** | **73.1** | **7.3** |

Discovered harness generalizes to unseen datasets, outperforming ACE by 2.9 points.

---

## 10. Key Equations & Statistics

- **Harness objective**: H* = arg max_H E_{x~X, τ~p_M(H,x)} r(τ,x)
- **Typical run**: ~60 harnesses over 20 iterations
- **Proposer reads**: median 82 files/iter (range 69-99)
- **Historical references**: 20+ prior candidates per proposal
- **Diagnostic tokens**: up to 10M per evaluation
- **Prior work budget**: 0.002-0.026M tokens/iter
- **Meta-Harness budget**: 10.0M tokens/iter (1000x more)

---

## OMEGA 项目核心引用

以下论文结论直接写入了本项目的设计：

| 论文发现 | OMEGA 实现 | 位置 |
|---------|-----------|------|
| Raw traces >> summaries (+15分) | incidents/ Trace Vault | `incidents/C-xxx_*/trace.md` |
| Filesystem selective access | Agent grep/read incidents | `rule-engine.sh`, `/lesson-to-rule` |
| Causal reasoning from traces | `/harness-reflect` gap analysis | `.claude/skills/harness-reflect/` |
| Additive > destructive changes | New rules (R-xxx) not harness rewrites | `rules/active/` |
| Proposer reads 82 files/iter | Claude reads incidents + rules + spec | Full harness |
| Code-space > prompt-space | YAML rules + bash hooks | `.claude/hooks/` |
| Pareto frontier (accuracy vs cost) | Block vs Warn rule severity | `rules/active/R-xxx.yaml` |

---

## References (Key subset)

- [AlphaEvolve] Novikov et al. "AlphaEvolve: A coding agent for scientific and algorithmic discovery" 2025
- [OpenEvolve] Saitoh et al. "OpenEvolve: Open-source evolutionary code optimization" 2025
- [DSPy] Khattab et al. "Optimizing LM programs" 2024
- [TextGrad] Yuksekgonul et al. "Automatic differentiation via text" 2024
- [OPRO] Yang et al. "Optimization by prompting" 2024
- [Karpathy autoresearch] github.com/karpathy/autoresearch — autonomous LLM experimentation

Full bibliography: 59 entries in original paper.
