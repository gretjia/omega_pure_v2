---
name: deploy-cycle
description: 部署周期 — Pre-flight/Axiom/NodeHealth/Deploy/Verify/Document 六阶段自动编排
user-invocable: true
---

# Deploy Cycle（部署周期）

自动编排从预检到部署完成的完整部署周期。

## 输入

用户提供目标节点，例如：
- `/deploy-cycle linux1`
- `/deploy-cycle windows1`

如果没有提供目标，询问用户部署到哪个节点。

节点别名映射：
- `linux1` → `linux1-lx`
- `windows1` → `windows1-w1`

## 六阶段流程

### Stage 1: PRE-FLIGHT

调用 `/pre-flight` skill，对目标节点执行 9 项预检：
1. SSH 连通性
2. 磁盘空间 > 20%
3. 内存 < 80%
4. 无重复进程
5. Python 依赖
6. 数据路径存在
7. systemd slice 状态
8. OOM 保护
9. 确认正确节点

输出：
```
=== STAGE 1: PRE-FLIGHT ===
Target: <node>
Verdict: GO / NO-GO
```

**如果 NO-GO → 停止并报告，等待用户修复后重试**

### Stage 2: AXIOM AUDIT

调用 `/axiom-audit` skill，运行完整公理检查：
```bash
python3 omega_axioms.py --verbose
```

输出：
```
=== STAGE 2: AXIOM AUDIT ===
Verdict: PASS / FAIL
```

**如果 FAIL → 停止，不允许部署有公理违规的代码**

### Stage 3: NODE HEALTH

调用 `/node-health-check` skill，检查集群健康：

输出：
```
=== STAGE 3: NODE HEALTH ===
<集群健康报告>
```

### Stage 4: DEPLOY

**此阶段需要用户明确确认后才执行。**

1. 确认要部署的文件列表
2. 用户确认后，SCP 文件到目标节点：
   ```bash
   scp <files> <target>:<deploy_path>/
   ```
3. 如果需要启动进程，使用 systemd-run：
   ```bash
   ssh <target> systemd-run --slice=heavy-workload.slice --scope python3 <script>
   ```

输出：
```
=== STAGE 4: DEPLOY ===
Files deployed:
  - <file1> → <target>:<path>
Status: DEPLOYED
```

### Stage 5: VERIFY

部署后验证：
1. 确认进程在目标节点运行：
   ```bash
   ssh <target> ps aux | grep python
   ```
2. 检查初始日志输出（前 20 行）
3. 确认无立即错误

输出：
```
=== STAGE 5: VERIFY ===
Process: RUNNING (PID: <pid>)
Initial output: <summary>
Verdict: HEALTHY / ERROR
```

### Stage 6: DOCUMENT

1. 更新 `handover/LATEST.md` 记录本次部署：
   - 时间戳
   - 目标节点
   - 部署的文件
   - 当前状态
2. 提示用户是否要 commit 这些变更

输出：
```
=== DEPLOY CYCLE COMPLETE ===

Target: <node>
Stages: PRE-FLIGHT ✓ → AXIOM ✓ → HEALTH ✓ → DEPLOY ✓ → VERIFY ✓ → DOCUMENT ✓

Deployed files:
  - <file1>

Process status: RUNNING

handover/LATEST.md updated.
Ready to commit? (yes/no)
```

## 安全约束

- Pre-flight 必须全部 PASS 才能继续
- 公理违规时绝不部署
- 部署操作（SCP + systemd-run）需要用户明确确认
- 使用 `systemd-run --slice=heavy-workload.slice` 启动重计算
- 不可同时运行多个 ETL 实例（单实例锁）
- 远程推送（git push, scp 到生产节点）需要用户确认
