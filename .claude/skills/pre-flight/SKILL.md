---
name: pre-flight
description: 部署前预检 — 检查目标节点依赖、路径、单实例锁、配额状态，输出GO/NO-GO
user-invocable: true
---

# Pre-Flight Deployment Check

在执行任何部署、ETL 启动或远程操作之前，运行此预检清单。

## 步骤

1. **确认目标节点**: 向用户确认操作目标是 `linux1-lx` 还是 `windows1-w1`

2. **SSH 连通性**:
   ```bash
   ssh -o ConnectTimeout=5 <target> echo "connected"
   ```

3. **磁盘空间** (必须 > 20% 可用):
   ```bash
   ssh <target> df -h <data_dir>
   ```

4. **内存状态** (linux1 必须 < 80% 使用):
   ```bash
   ssh <target> free -h
   ```

5. **重复实例检查** (必须无 ETL/forge 进程):
   ```bash
   ssh <target> ps aux | grep -E "python.*etl|python.*forge" | grep -v grep
   ```

6. **Python 依赖** (检查关键包):
   ```bash
   ssh <target> python3 -c "import pyarrow; import numpy; import webdataset; print('deps OK')"
   ```

7. **数据路径存在性**:
   ```bash
   ssh <target> ls -la <input_dir> | head -5
   ssh <target> ls -la <output_dir> 2>/dev/null || echo "output dir will be created"
   ```

8. **systemd slice 状态** (仅 linux1):
   ```bash
   ssh linux1-lx systemctl status heavy-workload.slice
   ```

9. **OOM 保护检查** (仅 linux1，确认 SSH session 不继承 -1000):
   ```bash
   ssh linux1-lx cat /proc/self/oom_score_adj
   ```
   预期结果: `0` (不是 `-1000`)

## 输出格式

```
=== PRE-FLIGHT CHECK: <target_node> ===
Timestamp: <ISO timestamp>
Operation: <description>

[ ] SSH connectivity ............ PASS / FAIL
[ ] Disk space (> 20% free) ..... PASS / FAIL (XX% used)
[ ] Memory (< 80% used) ......... PASS / FAIL (XX% used)
[ ] No duplicate processes ....... PASS / FAIL
[ ] Python dependencies ......... PASS / FAIL
[ ] Data paths exist ............ PASS / FAIL
[ ] systemd slice active ........ PASS / FAIL / N/A
[ ] OOM score = 0 ............... PASS / FAIL

=== VERDICT: GO / NO-GO ===
```

## 判定规则

- **任何一项 FAIL → NO-GO**，必须先修复再部署
- NO-GO 时列出每个失败项的修复建议
- 所有项 PASS → GO，可以继续部署
