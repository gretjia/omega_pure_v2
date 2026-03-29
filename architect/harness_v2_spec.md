# Harness V2 Spec — 压缩即智能

**设计者**: Claude Opus 4.6 + Codex GPT-5.4 (独立审计)
**日期**: 2026-03-29
**状态**: SPEC (待用户批准后执行)

---

## 设计哲学

Phase 7 灾难的根因不是"经验不够"——VIA_NEGATIVA 已有 20 条经验，CLAUDE.md 已有 53 条规则，dev-cycle/deploy-cycle 技能已存在。**它们全部被绕过了。**

问题是 **知行分离**：智慧以文本形式存在，错误以代码形式重现。

解法不是写更多文档，而是：
> **把智慧编码进结构。让正确路径成为唯一路径，而非推荐路径。**

类比模型设计：hd=64 瓶颈比 λ_s 正则化更有效（INS-019）。物理约束 > 软性惩罚。

---

## 六条元公理（生成一切具体规则的规则）

从 Phase 1-7 全部灾难中蒸馏出的否定性智慧。每条公理对应一类反复发生的失败模式。

| # | 元公理 | 生成原理 | 它杀死的失败模式 |
|---|--------|---------|----------------|
| Ω1 | **只信实测，不信推断** | 报告必须由命令输出生成，不可由 agent 推断 | 200/200 虚假报告、ETA 猜测、"应该够" |
| Ω2 | **先量化，后行动** | 任何资源承诺前必须有 `du -sh` / `df -h` / 带宽测量 | 磁盘不足、ETA 55h vs 预估 2h、带宽反优化 |
| Ω3 | **测试环境 = 生产环境** | 本地 smoke 永不授权生产部署；canary 必须在目标环境用精确镜像 | CPU 通过 GPU 炸、13 版 Docker、HIP 不兼容 |
| Ω4 | **可执行 > 可记忆** | 已知最优方法必须固化为 wrapper 脚本，不可仅存在于文档或记忆 | 重复用被禁 SSH pipe、忘记 HK 路径、upload_shards.sh 还在用旧方法 |
| Ω5 | **生产者 ≠ 验证者** | 写代码的 agent 不可独自验证该代码；外部审计不可删除 | AI 自测自验、squeeze bug、try/except 位置错 |
| Ω6 | **数据在哪，计算在哪** | 大数据不搬运；计算靠近存储 | omega-vm 中转两次过海、linux1 CPU 跑 GCS 数据 |

**设计原则**：元公理数量严格 ≤ 8。如果需要新公理，先尝试归入已有公理。公理膨胀 = 压缩失败。

---

## 三层防御架构

```
Layer 3: 压缩知识（OMEGA_LESSONS.md）    ← 被动参考，最弱
Layer 2: 自动门禁（Hooks + Canary）       ← 主动拦截，中等
Layer 1: 可执行安全路径（Wrapper Scripts） ← 结构约束，最强
```

**Layer 1 是核心。** 如果 Layer 1 做对了，Layer 2/3 几乎不需要触发。

---

## Layer 1: 可执行安全路径（对应 Ω4）

### 原则
经验教训不能只写在文档里。它们必须**编码进脚本**，让 agent 调用脚本而非重新发明方法。

### L1-A: `gcp/safe_upload.sh` — 替换 `upload_shards.sh`

杀死的 bug: SSH pipe 空文件（3 次重现）、while read stdin 冲突、并行度过高

```bash
#!/bin/bash
# safe_upload.sh — 唯一授权的 shard 上传路径
# 编码了 VIA_NEGATIVA 和 Phase 7 全部上传教训
#
# 路径: linux1 → HK(反向隧道) → GCS（Ω6: 数据在哪计算在哪）
# 方法: mapfile + for + ssh -n（Ω4: 可执行的正确方法）
# 验证: 每个 shard 上传后自动检查 size > 0（Ω1: 只信实测）
# 并行: 单线程（带宽阈值内）
#
# Usage: bash gcp/safe_upload.sh <shard_list_file>
# Example: bash gcp/safe_upload.sh /tmp/empty_shards.txt
```

**关键**：旧的 `upload_shards.sh` 必须 **删除或重命名为 `upload_shards.sh.DEPRECATED_UNSAFE`**，防止任何人（包括 AI agent）调用。

### L1-B: `gcp/safe_build_and_canary.sh` — Docker 构建 + 目标环境 canary

杀死的 bug: 13 版 Docker 迭代、本地 smoke 通过但 GPU 炸

```bash
#!/bin/bash
# safe_build_and_canary.sh — 构建 + 目标环境验证，一步完成
#
# 步骤:
# 1. 本地语法检查 (python3 -m py_compile)
# 2. 本地 regression test (已知 bug 类: 空 shard、单 sample、迭代器异常)
# 3. Docker build + push
# 4. 提交 1-shard canary job 到 Vertex AI（Ω3: 测试环境=生产环境）
# 5. 等待 canary 完成，检查 exit code + 输出 > 0 行
# 6. Canary PASS → 输出 "CANARY PASSED, safe to submit full job"
# 7. Canary FAIL → 输出日志 + 阻止全量提交
#
# Usage: bash gcp/safe_build_and_canary.sh <phase> <version>
```

**关键**：全量 job 提交前，canary 必须 PASS。这不是文档建议，是脚本流程中的硬门禁。

### L1-C: `gcp/safe_submit.sh` — Job 提交 + manifest 追踪

杀死的 bug: v5/v12/v13 命名混乱、虚假报告

```bash
#!/bin/bash
# safe_submit.sh — 提交 Vertex AI job + 写入 manifest
#
# 步骤:
# 1. 检查 canary 是否已通过（读 manifest）（Ω3）
# 2. 计算磁盘需求 (gsutil du -sh)（Ω2: 先量化）
# 3. 提交 job
# 4. 写入 gcp/manifest.jsonl:
#    {"ts":"...", "job_id":"...", "docker":"...", "canary_job":"...", "disk_gb":..., "data_gb":...}
# 5. 所有 cron 报告从 manifest 读取，不自己起名字（Ω1）
#
# Usage: bash gcp/safe_submit.sh
```

### L1-D: Regression test suite — `tests/test_known_bugs.py`

杀死的 bug: 空 shard crash、单 sample squeeze、迭代器 ValueError

```python
# tests/test_known_bugs.py
# 每次 Docker build 前自动运行
# 每条 test 对应一个 VIA_NEGATIVA 案例编号

def test_empty_shard_tolerance():
    """C-003: 空 shard 不可导致 crash"""

def test_single_sample_no_squeeze():
    """C-008: 单 sample batch 不可维度坍塌"""

def test_iterator_exception_caught():
    """C-009: WebDataset 迭代器异常必须被 catch"""
```

**设计原则**：每个曾经导致 Docker rebuild 的 bug，都必须有一条对应的 regression test。这是把痛苦编码为免疫力。

---

## Layer 2: 自动门禁（对应 Ω1 Ω3 Ω5）

### L2-A: `pre-deploy-gate.sh` — PreToolUse Hook (Bash)

```bash
# 触发: command 包含 "gcloud ai custom-jobs create"
# 检查:
# 1. gcp/manifest.jsonl 最近一条 canary 是否 PASS（Ω3）
# 2. 如果不 PASS → exit 2 阻止提交，提示用 safe_build_and_canary.sh
```

这不是"提醒"，是 **硬阻止**。没有 canary pass 就不能提交全量 job。

### L2-B: `post-upload-verify.sh` — PostToolUse Hook (Bash)

```bash
# 触发: command 包含 "gsutil cp" 或 "gcloud storage cp"
# 行为: 自动执行 gsutil ls -l <目标路径> | awk '$1==0'
# 如果发现空文件 → exit 1 报告，不只是提醒（Ω1）
```

### L2-C: 外部审计保留（对应 Ω5）

**上次压缩错误地删除了外部审计。这次明确：**

外部审计是 Ω5 (生产者 ≠ 验证者) 的核心执行机制。它不是"nice-to-have"，是公理级要求。

保留规则：
- **Codex**: 代码质量 + spec 对齐审计（dev-cycle Stage 8）
- **Gemini**: 数学/金融/GCS 审计（dev-cycle Stage 8）
- **dev-cycle 技能**: 不可跳过。非 trivial 代码变更必须走 dev-cycle

压缩方式：不是删除外部审计，而是将其嵌入 `safe_build_and_canary.sh` 流程中——canary 之前自动触发 `codex exec` 审计，审计 FAIL 则不构建。

---

## Layer 3: 压缩知识（对应所有公理的被动参考层）

### L3-A: 统一经验源 — `OMEGA_LESSONS.md`

合并 VIA_NEGATIVA + LATEST.md Bitter Lesson + audit/gemini_bitter_lessons.md 精华。

结构：

```markdown
# OMEGA LESSONS

## 元公理
Ω1-Ω6（见上）

## 操作手册（按场景）
### 上传到 GCS → 用 gcp/safe_upload.sh
### 构建 + 部署 → 用 gcp/safe_build_and_canary.sh + gcp/safe_submit.sh
### 新代码开发 → 用 /dev-cycle

## 案例库（每条 ≤ 2 行，编号索引）
C-001: SSH OOM 继承 → heavy-workload.slice
C-002: gc.collect() 紧密循环 → 禁止
...
```

**关键变化**：操作手册不再描述"怎么做"，而是指向"用哪个脚本"。知识被压缩为指针。

### L3-B: CLAUDE.md 精简

从 53 条 → ~25 条：
- 删除规则 43-49（经验摘要 → 已在 OMEGA_LESSONS）
- 删除规则 32-33 的冗长解释 → 替换为：`"新代码必须走 /dev-cycle，部署必须走 safe_build_and_canary.sh"` — 一行即可，因为 Hook 强制执行
- 合并重复规则

### L3-C: VIA_NEGATIVA.md 保留但冻结

VIA_NEGATIVA 是原始证据库，有考古价值。不删除，但标记为"已归档，活跃经验见 OMEGA_LESSONS.md"。新经验只写入 OMEGA_LESSONS.md。

### L3-D: handover/LATEST.md 去经验化

去掉 "Bitter Lesson" 和 "未来推理任务 SOP" 章节（已迁入 OMEGA_LESSONS）。LATEST.md 回归纯状态文件，只包含：当前状态 + 变更记录 + 下一步 + 警告。

状态数据必须由命令输出生成（Ω1），不可由 agent 推断。例如 shard 修复状态必须附带 `gsutil ls -l | awk '$1==0' | wc -l` 的实际输出。

---

## Memory 层

保留 M1（操作知识记忆）但降级为补充：
- 主要知识在 OMEGA_LESSONS.md + wrapper 脚本中
- Memory 只存**脚本之外的上下文**：节点状态变化、临时认证路径、用户偏好
- 不存储"怎么做某事"——那是脚本的工作（Ω4）

---

## 删除/废弃清单

| 文件 | 动作 | 原因 |
|------|------|------|
| `gcp/upload_shards.sh` | 重命名 `.DEPRECATED_UNSAFE` | 包含被禁的 SSH pipe 模式 |
| CLAUDE.md 规则 43-49 | 删除 | 与 OMEGA_LESSONS 重复 |
| CLAUDE.md 规则 32-33 冗余文本 | 压缩为一行 | Hook 强制执行后无需解释 |
| LATEST.md Bitter Lesson 章节 | 迁移到 OMEGA_LESSONS | LATEST 回归纯状态 |
| LATEST.md 未来推理任务 SOP | 迁移到 OMEGA_LESSONS | 同上 |

---

## 实施顺序

按依赖关系排序，非优先级：

```
Phase A: 地基（先有可执行路径，再谈其他）
  A1. 写 tests/test_known_bugs.py          — regression tests
  A2. 写 gcp/safe_upload.sh                — 替换危险上传脚本
  A3. 写 gcp/safe_build_and_canary.sh      — Docker + canary
  A4. 写 gcp/safe_submit.sh + manifest     — job 提交 + 追踪
  A5. 废弃 gcp/upload_shards.sh            — 封堵旧路径

Phase B: 门禁（有了安全路径后，强制使用它）
  B1. 写 .claude/hooks/pre-deploy-gate.sh  — 阻止无 canary 部署
  B2. 写 .claude/hooks/post-upload-verify.sh — 自动验证上传
  B3. 更新 .claude/settings.json            — 注册新 hooks

Phase C: 知识压缩（最后做，因为有了脚本后内容自然精简）
  C1. 创建 OMEGA_LESSONS.md                 — 统一经验 + 指向脚本
  C2. 精简 CLAUDE.md                         — 53→~25 条
  C3. 冻结 VIA_NEGATIVA.md                   — 标记归档
  C4. 精简 LATEST.md                         — 去经验化
  C5. 更新 dev-cycle SKILL                   — 加 Stage 0 pre-mortem
```

---

## 成功标准

Harness V2 生效后，以下场景 **不可能** 再发生：

1. ❌ 用 SSH pipe 上传到 GCS → `upload_shards.sh` 已废弃，`safe_upload.sh` 是唯一路径
2. ❌ Docker build 13 次 → regression test + canary 拦截大部分 bug
3. ❌ 本地 smoke 通过就部署全量 → pre-deploy hook 阻止无 canary 的提交
4. ❌ 报告"200/200 完成"但实际未验证 → post-upload hook 自动检查
5. ❌ 忘记最优上传路径 → 路径编码在 `safe_upload.sh` 中，不需要记
6. ❌ 版本号混乱 → manifest.jsonl 是唯一真相源
7. ❌ 跳过外部审计 → dev-cycle Stage 8 + canary 流程内嵌 codex exec
8. ❌ 经验散落 4 个文件 → OMEGA_LESSONS.md 是唯一入口

## 压缩度量

| 指标 | V1 (现状) | V2 (目标) |
|------|----------|----------|
| CLAUDE.md 规则数 | 53 | ~25 |
| 经验文件数 | 4 (重叠) | 1 (OMEGA_LESSONS) + 1 (VIA_NEGATIVA 归档) |
| 元公理数 | 0 (全是具体规则) | 6 (生成具体规则) |
| 可执行安全路径 | 0 | 3 (upload/build/submit) |
| 自动门禁 | 1 (block-destructive) | 3 (+pre-deploy +post-upload) |
| 已知 bug 回归测试 | 0 | ≥5 |
| 危险遗留脚本 | 1 (upload_shards.sh) | 0 |
