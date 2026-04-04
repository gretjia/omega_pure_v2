# Karpathy Autoresearch — 完整归档

> **原文归档**: https://github.com/karpathy/autoresearch
> **Stars**: 65.3K | **Forks**: 9.3K | **License**: MIT | **归档日期**: 2026-04-04
> **归档目的**: OMEGA Living Harness 的工程灵感来源。Karpathy 的"autonomous experimentation loop"直接启发了我们的 `/dev-cycle` 和 error-tracker 设计。
> **本地完整 clone**: `meta_karpathy_harness/_source_autoresearch/`

---

## Karpathy 开篇引言

> *One day, frontier AI research used to be done by meat computers in between eating, sleeping, having other fun, and synchronizing once in a while using sound wave interconnect in the ritual of "group meeting". That era is long gone. Research is now entirely the domain of autonomous swarms of AI agents running across compute cluster megastructures in the skies. The agents claim that we are now in the 10,205th generation of the code base, in any case no one could tell if that's right or wrong as the "code" is now a self-modifying binary that has grown beyond human comprehension. This repo is the story of how it all began. —@karpathy, March 2026*

---

## 核心理念

Give an AI agent a small but real LLM training setup and let it experiment **autonomously overnight**. It modifies the code, trains for 5 minutes, checks if the result improved, **keeps or discards**, and repeats. You wake up in the morning to a log of experiments and (hopefully) a better model.

**关键洞察**: You are programming the `program.md` Markdown files that provide context to the AI agents and set up your autonomous research org. The default `program.md` is intentionally bare bones — the real innovation space is finding the "research org code" that achieves the fastest research progress.

---

## 三文件架构

| 文件 | 角色 | 谁修改 |
|------|------|--------|
| `prepare.py` | 固定常量、数据准备、tokenizer、评估函数 | **不可修改** |
| `train.py` | 完整 GPT 模型 + 优化器 + 训练循环 | **Agent 修改** |
| `program.md` | Agent 指令 (lightweight "skill") | **人类修改** |

---

## 设计选择

### 1. Single File to Modify
Agent only touches `train.py`. Keeps scope manageable, diffs reviewable.

### 2. Fixed Time Budget (5 min)
- ~12 experiments/hour, ~100 experiments overnight
- Makes experiments directly comparable regardless of architecture/batch size/model size
- Finds optimal model **for your platform** in that budget
- **Downside**: runs not comparable across platforms

### 3. Self-Contained
One GPU, one file, one metric. No distributed training, no complex configs.

### 4. Single Metric
**val_bpb** (validation bits per byte) — lower is better, vocab-size-independent.

---

## program.md — Agent 指令全文

### Setup Phase
1. Agree on run tag (e.g. `mar5`), create branch `autoresearch/<tag>`
2. Read in-scope files (README, prepare.py, train.py)
3. Verify data exists in `~/.cache/autoresearch/`
4. Initialize `results.tsv`
5. Confirm and go

### Experimentation Rules

**CAN do**: Modify `train.py` — architecture, optimizer, hyperparameters, batch size, model size
**CANNOT do**: Modify `prepare.py`, install packages, modify evaluation harness

**Simplicity Criterion** (直接引用):
> All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Conversely, removing something and getting equal or better results is a great outcome — that's a simplification win. A 0.001 val_bpb improvement that adds 20 lines of hacky code? Probably not worth it. A 0.001 val_bpb improvement from deleting code? Definitely keep. An improvement of ~0 but much simpler code? Keep.

### The Loop

```
LOOP FOREVER:
1. Look at git state
2. Tune train.py with experimental idea
3. git commit
4. Run: uv run train.py > run.log 2>&1
5. Read results: grep "^val_bpb:\|^peak_vram_mb:" run.log
6. If empty → crashed → tail -n 50 run.log → fix or skip
7. Record in results.tsv
8. If improved → keep (advance branch)
9. If worse → discard (git reset)
```

### Critical Rules

**NEVER STOP**: 
> Once the experiment loop has begun, do NOT pause to ask the human if you should continue. The human might be asleep. You are autonomous. If you run out of ideas, think harder — read papers referenced in the code, re-read the in-scope files for new angles, try combining previous near-misses, try more radical architectural changes. The loop runs until the human interrupts you, period.

**Timeout**: >10 min → kill, discard, revert
**Crashes**: Typo/import fix → retry. Fundamentally broken → skip, log "crash"

### Results Format (TSV)

```
commit	val_bpb	memory_gb	status	description
a1b2c3d	0.997900	44.0	keep	baseline
b2c3d4e	0.993200	44.2	keep	increase LR to 0.04
c3d4e5f	1.005000	44.0	discard	switch to GeLU activation
d4e5f6g	0.000000	0.0	crash	double model width (OOM)
```

---

## train.py 技术细节

### 模型架构 (GPTConfig)
- sequence_len: 2048
- vocab_size: 32768 (from BPE tokenizer)
- n_layer: 12, n_head: 6, n_kv_head: 6, n_embd: 768
- window_pattern: "SSSL" (sliding window: S=half, L=full)
- Value Embedding (ResFormer): alternating layers with input-dependent gate
- RoPE (Rotary Position Embeddings)
- RMS Norm
- Squared ReLU activation
- Logit softcap = 15

### 优化器 (MuonAdamW)
- **Muon**: 2D matrix params (polar express orthogonalization + NorMuon variance reduction + cautious weight decay)
- **AdamW**: Embedding, unembedding, scalar params
- LR scaling: ∝ 1/√(d_model/768)
- Schedule: warmup → constant → warmdown (cosine)

### 超参数
```python
ASPECT_RATIO = 64       # model_dim = depth * 64
HEAD_DIM = 128
TOTAL_BATCH_SIZE = 2**19  # ~524K tokens/step
DEPTH = 8
DEVICE_BATCH_SIZE = 128
EMBEDDING_LR = 0.6
MATRIX_LR = 0.04
WEIGHT_DECAY = 0.2
WARMDOWN_RATIO = 0.5
```

### GC Management
```python
if step == 0:
    gc.collect(); gc.freeze(); gc.disable()  # Python GC causes ~500ms stalls
elif (step + 1) % 5000 == 0:
    gc.collect()
```

---

## prepare.py 技术细节

### Constants (Fixed)
- MAX_SEQ_LEN: 2048
- TIME_BUDGET: 300s (5 minutes)
- EVAL_TOKENS: 40 × 524288
- VOCAB_SIZE: 8192
- Dataset: karpathy/climbmix-400b-shuffle (6542 shards)

### Evaluation (BPB)
Bits per byte: vocab-size-independent. Sums per-token cross-entropy (nats), sums target byte lengths, converts nats/byte to bits/byte. Special tokens excluded.

### Dataloader
BOS-aligned with best-fit packing. 100% utilization (no padding). Documents packed using best-fit decreasing to minimize cropping.

---

## Notable Forks

- [miolini/autoresearch-macos](https://github.com/miolini/autoresearch-macos) (MacOS)
- [trevin-creator/autoresearch-mlx](https://github.com/trevin-creator/autoresearch-mlx) (MacOS MLX)
- [jsegov/autoresearch-win-rtx](https://github.com/jsegov/autoresearch-win-rtx) (Windows)
- [andyluo7/autoresearch](https://github.com/andyluo7/autoresearch) (AMD)

---

## OMEGA 项目核心引用

| Karpathy 原则 | OMEGA 实现 | 位置 |
|--------------|-----------|------|
| program.md = lightweight skill | `.claude/skills/*/SKILL.md` | 9 个 skill 定义 |
| Single metric (val_bpb) | 健康分 = enforcement × repeat × fix_ratio | `/harness-reflect` |
| Keep/Discard loop | Rule 激活/退役循环 | `/lesson-to-rule` + `/harness-reflect` |
| NEVER STOP (autonomous) | post-bash-error-tracker.sh 自动捕获 | `.claude/hooks/` |
| Simplicity criterion | Ω4: 可执行 > 可记忆; 规则软上限 50 条 | CLAUDE.md |
| results.tsv (structured log) | `rules/enforcement.log` + `gcp/manifest.jsonl` | TSV/JSONL 审计轨迹 |
| git commit → run → keep/discard | Phase dev → canary → deploy/rollback | `/deploy-cycle` |
| Fixed evaluation (prepare.py) | Fixed axioms (omega_axioms.py) | 不可修改的真理基准 |
| One file to modify (train.py) | 规则只在 YAML 中, 不改 hook 代码 | `rules/active/*.yaml` |

---

## 关键链接

- **Repository**: https://github.com/karpathy/autoresearch
- **Parent project**: https://github.com/karpathy/nanochat
- **Tweet 1**: https://x.com/karpathy/status/2029701092347630069
- **Tweet 2**: https://x.com/karpathy/status/2031135152349524125
- **Dummy's Guide**: https://x.com/hooeem/status/2030720614752039185
