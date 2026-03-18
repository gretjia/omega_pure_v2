---
name: dev-cycle
description: 完整开发周期 — Plan/Audit/Fix/Code/Audit/Fix/Axiom/Summary 八阶段自动编排
user-invocable: true
---

# Dev Cycle（完整开发周期）

自动编排从计划到代码完成的完整开发周期。用户只需在关键节点确认。

## 输入

用户提供任务描述，例如：
- `/dev-cycle 实现新的特征维度 Epiplexity`
- `/dev-cycle 修复 ETL 窗口边界问题`

如果没有提供描述，询问用户要做什么。

## 六阶段流程

每个阶段间有 PASS/FAIL 门禁。FAIL 时循环修复，不跳过。

### Stage 1: PLAN

1. 读取 `architect/current_spec.yaml` 获取当前规范
2. 读取 `architect/INDEX.md` 检查是否有待执行的架构师指令
3. 读取 `VIA_NEGATIVA.md` 确保计划不重蹈覆辙
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

### Stage 8: SUMMARY

输出变更摘要：
```
=== DEV CYCLE COMPLETE ===

Task: <任务描述>
Stages: PLAN ✓ → AUDIT ✓ → CODE ✓ → AUDIT ✓ → AXIOM ✓

Modified files:
  - <file1>: <变更描述>
  - <file2>: <变更描述>

Axiom status: ALL PASSED

Ready to commit? (yes/no)
```

等待用户确认后执行 git commit。

## 安全约束

- 计划阶段不执行任何代码变更
- 代码阶段不跳过审计
- 公理检查是最终门禁，不可跳过
- Layer 1 物理常数在任何阶段都不可修改
- 如果审计循环超过 3 次，暂停并征求用户意见
