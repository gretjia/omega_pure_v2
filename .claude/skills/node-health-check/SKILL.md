---
name: node-health-check
description: SSH到集群节点检查磁盘/内存/进程/网络连通性，输出结构化健康报告
user-invocable: true
---

# Node Health Check

对 OMEGA 集群的所有工作节点执行健康检查。

## 步骤

1. **SSH 连通性测试**: 依次测试 `linux1-lx`, `windows1-w1`, `zephrymac-studio`
   ```bash
   ssh -o ConnectTimeout=5 <host> echo "alive"
   ```

2. **磁盘空间检查** (linux1-lx, windows1-w1):
   ```bash
   ssh <host> df -h / /omega_pool 2>/dev/null
   ```

3. **内存状态** (linux1-lx):
   ```bash
   ssh linux1-lx free -h
   ssh linux1-lx cat /proc/meminfo | head -5
   ```

4. **进程检查** (检查是否有遗留 ETL 或 Python 进程):
   ```bash
   ssh <host> ps aux | grep -E "python|etl|forge" | grep -v grep
   ```

5. **cgroup/slice 状态** (linux1-lx):
   ```bash
   ssh linux1-lx systemctl status heavy-workload.slice 2>/dev/null
   ssh linux1-lx cat /sys/fs/cgroup/user.slice/user-1000.slice/cpu.max 2>/dev/null
   ```

6. **网络连通性** (omega-vm 到各节点延迟):
   ```bash
   ssh -o ConnectTimeout=5 <host> echo "RTT test"
   ```

## 输出格式

```
=== OMEGA CLUSTER HEALTH REPORT ===
Timestamp: <ISO timestamp>

[linux1-lx]
  SSH:    OK / FAIL
  Disk:   /       XX% used (XX GB free)
          /omega_pool  XX% used (XX GB free)
  Memory: XX GB used / 128 GB total
  ETL Processes: None / <PID list>
  Slice:  heavy-workload.slice <active/inactive>

[windows1-w1]
  SSH:    OK / FAIL
  Disk:   ...
  ...

[zephrymac-studio]
  SSH:    OK / FAIL

=== VERDICT: ALL HEALTHY / ISSUES FOUND ===
```

## 注意事项

- 如果某节点 SSH 超时，标记为 FAIL 并继续检查其他节点
- 不执行任何修改操作，纯只读检查
- 如果发现磁盘 > 90% 或内存 > 90%，在 VERDICT 中标记为 WARNING
