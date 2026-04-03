---
name: dev-cycle
description: 完整开发周期 — PreMortem/Plan/Audit/Fix/Code/Audit/Fix/Axiom/ExternalAudit/Summary 十阶段自动编排
user-invocable: true
---

# Dev Cycle（完整开发周期）

自动编排从计划到代码完成的完整开发周期。用户只需在关键节点确认。

## 输入

用户提供任务描述，例如：
- `/dev-cycle 实现新的特征维度 Epiplexity`
- `/dev-cycle 修复 ETL 窗口边界问题`

如果没有提供描述，询问用户要做什么。

## 十阶段流程

每个阶段间有 PASS/FAIL 门禁。FAIL 时循环修复，不跳过。

### Stage 0: PRE-MORTEM（Ω4 + Ω2）

**在写任何代码之前**，强制执行：

1. 读取 `OMEGA_LESSONS.md` 中相关场景的操作手册
2. 列出 **3 个可能的实现方案**（不是 1 个）
3. 对每个方案列出 **2-3 个可能的失败模式**
4. 选择最优方案并说明理由
5. 执行 Ω2 量化：`du -sh` 数据量、`df -h` 磁盘、预估 ETA

输出：
```
=== STAGE 0: PRE-MORTEM ===
方案 A: ... → 失败风险: ...
方案 B: ... → 失败风险: ...
方案 C: ... → 失败风险: ...
选择: 方案 X，理由: ...
量化: 数据 Xg GB, 磁盘 Y GB, 预估 ETA Z h
```

### Stage 1: PLAN

1. 读取 `architect/current_spec.yaml` 获取当前规范
2. 读取 `architect/INDEX.md` 检查是否有待执行的架构师指令
3. 读取 `OMEGA_LESSONS.md` 确保计划不重蹈覆辙（案例库 C-001 至 C-023）
4. 进入 Plan Mode（使用 EnterPlanMode 工具）
5. 草拟实现计划，包括：
   - 需要修改的文件列表
   - 每个文件的具体变更
   - 潜在风险和缓解措施
   - 是否涉及公理相关参数

输出：
```
=== STAGE 1: PLAN ===
<实现计划>
```

### Stage 2: AUDIT PLAN

1. 调用 `recursive-auditor` agent 审计计划
2. Agent 检查：
   - 计划是否与 current_spec.yaml 对齐
   - 计划是否违反 VIA_NEGATIVA 中的已证伪路径
   - 计划是否涉及 Layer 1 物理常数（如果是，FAIL）
   - 张量形状变更是否自洽

输出：
```
=== STAGE 2: AUDIT PLAN ===
Verdict: PASS / FAIL
<审计详情>
```

**如果 FAIL → 进入 Stage 3 修复，然后回到 Stage 2 重新审计**

### Stage 3: FIX PLAN（仅在 Stage 2 FAIL 时执行）

1. 根据审计反馈修正计划
2. 返回 Stage 2 重新审计
3. 最多循环 3 次，超过则暂停并征求用户意见

### Stage 4: CODE

1. 退出 Plan Mode（使用 ExitPlanMode 工具）
2. 按照审计通过的计划执行代码变更
3. 每个文件变更后，PostToolUse hook 会自动运行公理检查（如果是核心文件）

输出：
```
=== STAGE 4: CODE ===
Modified files:
  - <file1>: <变更描述>
  - <file2>: <变更描述>
```

### Stage 5: AUDIT CODE

1. 调用 `recursive-auditor` agent 审计代码变更
2. Agent 检查：
   - 实际代码是否与计划一致
   - 物理常数未被修改
   - 张量形状与 spec 对齐
   - 无 NaN/Inf 风险
   - 无静默失败路径

输出：
```
=== STAGE 5: AUDIT CODE ===
Verdict: PASS / FAIL
<审计详情>
```

**如果 FAIL → 进入 Stage 6 修复，然后回到 Stage 5 重新审计**

### Stage 6: FIX CODE（仅在 Stage 5 FAIL 时执行）

1. 根据审计反馈修正代码
2. 返回 Stage 5 重新审计
3. 最多循环 3 次，超过则暂停并征求用户意见

### Stage 7: AXIOM CHECK

运行完整公理检查：
```bash
cd /home/zephryj/projects/omega_pure_v2 && python3 omega_axioms.py --verbose
```

输出：
```
=== STAGE 7: AXIOM CHECK ===
<omega_axioms.py 输出>
Verdict: PASS / FAIL
```

**如果 FAIL → 回到 Stage 6 修复代码，然后重新运行公理检查**

### Stage 8: EXTERNAL AUDIT（独立交叉验证）

使用外部 LLM 进行独立审计，防止 AI 自测自验 (Bitter Lesson #7)。

1. **Codex recursive audit**（spec/代码一致性）:
   ```bash
   codex exec --full-auto "<审计 prompt，比对 spec vs 代码变更>"
   ```
   验证代码变更是否与 `architect/current_spec.yaml` 和 `architect/gdocs/` 对齐。

2. **Gemini 数学推理审计**（仅在涉及数学核心/物理公式时）:
   ```bash
   cat <变更文件> | gemini -p "对以下代码进行纯数学推理审计..."
   ```
   验证公式推导、量纲一致性、梯度闭环。

输出：
```
=== STAGE 8: EXTERNAL AUDIT ===
Codex (GPT 5.4): PASS/FAIL
Gemini (math): PASS/FAIL/SKIP (非数学变更跳过)
```

**如果任一 FAIL → 回到 Stage 6 修复，重新走 Stage 7-8**

### Stage 8.5: SPEC-CODE ALIGNMENT（防漂移门禁 — Meta-Harness V3）

**此阶段防止 C-057 类漂移: spec 写了一套, 代码实际跑另一套。**

1. 读取 `architect/current_spec.yaml` 中标记 `[DRAFT — pending audit]` 的字段
2. 如果外部审计全部 PASS:
   - 移除 `[DRAFT]` 标记 → 变为 final
   - 更新对应 INS-* 的 `audit_status: draft` → `audit_status: final`
3. 运行 spec-code 对齐检查:
   ```
   遍历 spec 中的关键参数:
     - window_size_s: spec 值 vs `grep "window_size_s.*default" train.py gcp/train.py`
     - lambda_s: spec 值 vs `grep "lambda_s.*default" train.py gcp/train.py`
     - hidden_dim: spec 值 vs `grep "hidden_dim.*default" train.py gcp/train.py`
     - loss_function: spec 描述 vs 代码实际实现
   对比不一致 → 列出差异 → 必须修复后才能通过
   ```
4. 验证 INS 中的 `前提假设` 部分:
   - 如果 INS 假设 target 单位为 X → `grep` ETL 源码验证
   - 如果 INS 假设某个函数存在 → `grep` 代码验证
   - 假设不成立 → FAIL（C-059 教训: 假设不验证 = 定时炸弹）

输出：
```
=== STAGE 8.5: SPEC-CODE ALIGNMENT ===
Spec drafts finalized: N fields
Alignment check:
  ✓ window_size_s: spec=10, code=10
  ✓ lambda_s: spec=1e-4, code=1e-4
  ✗ hidden_dim: spec=64, code=32 → MUST FIX
Assumptions verified: M/N passed
Verdict: PASS / FAIL
```

**如果 FAIL → 修复代码使其与 spec 对齐，然后重新检查**

### Stage 9: SUMMARY

输出变更摘要：
```
=== DEV CYCLE COMPLETE ===

Task: <任务描述>
Stages: PLAN ✓ → AUDIT ✓ → CODE ✓ → AUDIT ✓ → AXIOM ✓ → EXTERNAL ✓

Modified files:
  - <file1>: <变更描述>
  - <file2>: <变更描述>

Axiom status: ALL PASSED (37 checks)
External audit: Codex PASS, Gemini PASS/SKIP

Ready to commit? (yes/no)
```

等待用户确认后执行 git commit。

## 安全约束

- 计划阶段不执行任何代码变更
- 代码阶段不跳过审计
- 公理检查是最终门禁，不可跳过
- Layer 1 物理常数在任何阶段都不可修改
- 如果审计循环超过 3 次，暂停并征求用户意见
