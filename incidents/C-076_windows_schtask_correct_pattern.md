# C-076: Windows Scheduled Task 正确模式

## 问题
多次尝试在 windows1 上通过 SSH 启动长任务全部失败，浪费 4+ 小时。

## 失败路径（按时间顺序）
1. SSH 前台 `nohup ssh windows1 "python ..."` → SSH 断连杀进程 (C-072)
2. Monitor 用 tasklist 判断完成 → SSH 超时误判 (C-073)  
3. VBS / PowerShell Start-Process / DETACHED_PROCESS → sshd Job Object 内全死
4. WMI Invoke-CimMethod → SYSTEM 运行成功但以为不能访问 D:（实际可以）
5. schtasks /create /tr "python ..." → 引号转义崩坏
6. schtasks /ru USER /rp PASSWORD → 密码不匹配
7. PowerShell Register-ScheduledTask 内联 → SSH 多行转义损坏

## 根因（三层）
1. **CRLF**: scp 从 Linux 传的 .cmd 是 LF，cmd.exe 静默失败不报错
2. **引号地狱**: 把命令塞进 /tr 或 SSH 内联 PowerShell，层层转义必崩
3. **未 research 历史**: 仓库 v62/v63 已有成功模式（PowerShell API + wrapper）

## 正确模式（已验证 2026-04-05）
```
1. scp wrapper.cmd → 修 CRLF
2. scp register.ps1 → New-ScheduledTaskAction + WorkingDirectory
3. powershell -ExecutionPolicy Bypass -File register.ps1
4. 用 Python 读日志监控（type 命令看不到 UTF-8）
```

## 关键发现
- SYSTEM 可以访问本地 USB SSD (D:)，只是不能访问网络映射盘
- schtasks /run 返回 0 ≠ 脚本跑了，只表示调度器接受了任务定义
- cmd.exe 对 LF 换行的 .cmd 文件静默失败（最隐蔽的 bug）
