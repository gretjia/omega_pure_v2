# OMEGA PURE V3 — 项目宪法

## WHAT: 项目定义

量化金融研究项目：Finite Window Topological Attention + MDL 压缩，从 A股 L1 tick 数据提取机构主力行为信号。

**技术栈**: Python 3.10+, PyTorch, PyArrow, WebDataset, NumPy, Numba | GCP Vertex AI (L4/A100) | 2.2TB raw → Volume-Clocked tensors

**核心张量**: `[B, 160, 10, 10]` — 完整规范见 `architect/current_spec.yaml`

**文件地图**:
| 文件 | 角色 |
|------|------|
| `omega_epiplexity_plus_core.py` | 数学核心（SRL反演 + 拓扑注意力 + MDL损失） |
| `omega_webdataset_loader.py` | WebDataset 流式加载器 |
| `tools/omega_etl_v3_topo_forge.py` | V3 ETL 管线 |
| `architect/current_spec.yaml` | 当前架构规范（动态公理源） |
| `omega_axioms.py` | 公理断言模块 |
| `OMEGA_LESSONS.md` | **唯一经验源**（元公理 + 操作手册 + 案例库） |

---

## WHY: 核心哲学

**Taleb 反脆弱**: 尾部事件是信号 | 不对称比 > 3.0 | 小额试错 + 尾部暴利

**压缩即智能**: MDL = H_T + λ_s × S_T | hd=64 物理瓶颈 > λ_s 正则化（INS-019）| 隐式压缩 > 显式压缩

**主力行为检测**: SRL 反演提取元订单流 → T+1 隔夜波段 | 低胜率可接受(>35%)，关键是肥尾不对称比

**Karpathy 极简**: 代码行数是负债 | 简单 > 聪明

---

## HOW: 不可违反的规则

### 元公理（Ω1-Ω6，详见 `OMEGA_LESSONS.md`）
1. **Ω1 只信实测** — 报告/状态/ETA 必须由命令输出生成
2. **Ω2 先量化后行动** — `du -sh` / `df -h` / 带宽实测，然后才承诺资源
3. **Ω3 测试环境=生产环境** — 本地 smoke 永不授权生产部署，canary 必须目标环境
4. **Ω4 可执行 > 可记忆** — 已知最优方法固化为 wrapper 脚本（`gcp/safe_*.sh`）
5. **Ω5 生产者 ≠ 验证者** — 外部审计不可删除（Codex 管代码，Gemini 管数学）
6. **Ω6 数据在哪计算在哪** — 大数据不搬运

### 物理公理（永恒，Layer 1）
7. δ = 0.5 — 平方根法则指数，严禁修改或设为可学习参数
8. 空间轴不可被拍扁 — 张量必须保持 `[B, T, S, F]` 四维结构
9. 数值稳定性 — 输出不可包含 NaN 或 Inf
10. c — Layer 2 per-stock 动态标定值。c_default=0.842 仅为回退值

### 架构公理（可演进，Layer 2，从 `architect/current_spec.yaml` 读取）
11. 张量形状当前为 `[B, 160, 10, 7]`（以 spec 文件为准）
12. vol_threshold 冷启动默认值 = 50000 | window_size = 160 | stride = 20 | adv_fraction = 0.02

### 破坏性操作红线
13. **删除/覆盖数据文件** → 必须人工确认，无例外
14. **远程推送** → 必须人工确认
15. **修改 architect/current_spec.yaml** → 必须人工确认

### 强制工作流（由 Hook + 脚本强制执行）
16. **新代码/新 Phase** → 走 `/dev-cycle`（含 Pre-mortem + 外部审计）
17. **Docker 构建 + 部署** → 走 `gcp/safe_build_and_canary.sh` + `gcp/safe_submit.sh`
18. **上传到 GCS** → 走 `gcp/safe_upload.sh`（旧 upload_shards.sh 已废弃）
19. **部署到远程节点** → 先 `/pre-flight`，重计算走 `heavy-workload.slice`
20. **Cron 报告** → 从 `gcp/manifest.jsonl` 读取 Job ID + Docker tag，不自造名字

### 热修复纪律（C-030 教训）
21. **配置报错时只改出错字段**，禁止重写整个文件。修复后必须 `diff` 原始版本，确认无静默丢失
22. **提交 Vertex AI Job 前**，人工检查 YAML 三项: (1) diskType 合法? (2) 关键性能配置(SSD/staging/cache)在? (3) 参数默认值是否安全(除零/边界)?

### 工程规范
21. 禁止紧密循环 `gc.collect()` | 禁止无条件 `use_threads=True`
22. ETL 单实例锁（fcntl.LOCK_EX） | PyArrow `iter_batches` 禁止 `.collect()`
23. 断点续传强制（>1h 批处理必须 checkpoint）
24. `PYTHONUNBUFFERED=1` 用于所有 nohup/后台任务

### 会话退出强制流程
25. **Session 结束前**，必须将本次会话遇到的**所有 debug、错误、失误**压缩记录到 `OMEGA_LESSONS.md` 案例库（编号递增，每条 ≤ 2 行，归因到 Ω 公理）。包括但不限于：配置错误、API 拒绝、参数遗漏、工程踩坑、费用误判。**不可遗漏，不可延迟到下个 session。**

### 上下文管理
26. `OMEGA_LESSONS.md` — **唯一经验源**（元公理 + 操作手册 + 案例库）
27. `handover/LATEST.md` — 当前项目状态（纯状态，不含经验）
28. `VIA_NEGATIVA.md` — 已冻结归档（原始证据，不再追加）
29. `architect/current_spec.yaml` — 架构规范 | `architect/INDEX.md` — 指令时间线

### 硬件拓扑（详见 `handover/HARDWARE_TOPOLOGY.md`）
30. 四节点: omega-vm(控制) → linux1-lx / windows1-w1(计算) → zephrymac-studio(架构师)
31. SSH 别名: `ssh linux1-lx` | `ssh windows1-w1` | `ssh zephrymac-studio`

### 用户画像
32. 独狼量化研究员，零编程基础 vibe coder
33. 优势: 品味、市场洞察、Taleb 哲学
34. 中文为主，技术术语可英文，简明扼要
