---
name: handover-update
description: 更新 handover/LATEST.md — 会话结束前强制执行，确保跨会话连续性
user_invocable: true
---

# /handover-update — Session Handover

会话结束前强制执行。确保下一个 session 能快速接续当前工作。

## Procedure

### 1. Gather State（收集状态）

- 读取当前 `handover/LATEST.md`
- `git log --oneline -10` 查看本次会话的 commits
- `git diff --stat` 查看未提交的变更
- 回顾本次会话的关键决策
- **扫描未记录错误（Karpathy 兜底）**：
  - 读取 `logs/session_errors.jsonl`，检查 `"recorded": false` 的条目
  - 如有未记录错误，**必须先写入 OMEGA_LESSONS.md 并执行 /lesson-to-rule**，然后再继续 handover
  - 将已处理的条目标记为 `"recorded": true`
- 检查远程节点状态（如本次会话涉及 ETL/部署）：
  - `ssh linux1-lx 'ps aux | grep python3 | grep -v grep; df -h /omega_pool'` (如可达)
  - `ssh windows1-w1 'ps aux | grep python3 | grep -v grep; df -h /omega_pool'` (如可达)

### 2. Draft Update（草拟更新）

更新 `handover/LATEST.md`，格式：

```
# Omega Pure V3 - Project LATEST Handover State
Last Updated: YYYY-MM-DD — **STATUS: [一句话当前状态]**

## Current State
- [当前什么在运行/已完成]
- [什么坏了/不完整]
- [ETL/训练进度（如有）]

## Changes This Session
- [变更 1，附 commit ref]
- [变更 2]

## Key Decisions
- [决策 1]: [理由]

## Next Steps
1. [最高优先级]
2. [次要任务]

## Warnings
- [下个 session 必须知道的事]

## Remote Node Status
- linux1: [进程状态, 磁盘, 内存]
- windows1: [进程状态, 磁盘, 内存]
（如本次未涉及远程操作，标注「本次会话未涉及远程节点」）

## Architect Insights (本次会话)
- [INS-NNN 标题]: 一句话浓缩 → 已归档到 architect/insights/INS-NNN_xxx.md
（如无新洞察，标注「本次会话无新架构洞察」）
```

### 3. Present for Review（展示草稿）

将草稿展示给用户。**不可自动写入，必须等用户确认。**

### 4. Write & Commit（写入并提交）

用户确认后：
1. 写入 `handover/LATEST.md`
2. 建议 commit：`git add handover/LATEST.md && git commit -m "docs: update handover state"`
3. 等待用户确认后才执行 commit
