# C-072/C-073: SSH 前台执行被杀 + 监控误判完成

## 事件链
1. ETL v4 通过 `nohup ssh windows1-w1 "python ..."` 在 SSH 前台启动，8 workers
2. 1.5h 后 SSH 连接断开 (`Connection to localhost closed by remote host`)
3. windows1 上的 Python 进程随 SSH 会话终止
4. Monitor 脚本每 2min 通过 `ssh windows1 tasklist | grep python` 检查进程
5. SSH 连接超时 → tasklist 返回空 → Monitor 误判为 "0 进程 = ETL 完成"
6. Monitor 双重确认也因 SSH 超时返回空 → 确认"完成"
7. Monitor 触发 upload_v4_shards_to_gcs.py → merge_worker_shards 把 335 个 partial shard 从 worker dirs 移到根目录
8. upload SSH 也超时 → 上传没实际执行，但 merge 已破坏 worker 目录结构
9. 多次尝试通过 schtasks/PowerShell/bat 脱离 SSH 重启 ETL 失败

## 根因
1. **SSH 前台 = 进程生命绑定在网络连接上** — 跨 GFW 隧道(omega-vm→HK→windows1)延迟大、不稳定
2. **Monitor 用 SSH 连通性做存活代理** — 违反 Ω1（只信实测），SSH 失败被等价于进程不存在
3. **缺乏 Windows 后台执行经验** — Linux 有 tmux/screen/nohup，Windows 等价方案不熟悉

## 损失
- ~1.5h 计算时间 + 335 个 shard（需重跑）
- ~30min 调试重启
- 数据目录被 merge 污染，需清空重来

## 修复
- C-072 → R-019: 禁止 SSH 前台执行 >30min 任务
- C-073 → R-020: 监控必须检查文件标志，不可用进程列表
- 操作手册更新: 远程节点操作增加持久化执行方法
