# OMEGA PURE V3 — 项目宪法

## WHAT: 项目定义

这是一个量化金融研究项目，使用 Finite Window Topological Attention 和 MDL 压缩从 A股 L1 tick 数据中提取机构主力行为信号。

### 技术栈
- Python 3.10+, PyTorch, PyArrow, WebDataset, NumPy, Numba
- 训练目标：GCP Vertex AI (L4/A100 GPU cluster)
- 数据规模：2.2TB raw L1 ticks → Volume-Clocked tensors

### 核心张量
- 形状：`[B, 160, 10, 7]` — Batch × Time(VolumeSteps) × Spatial(LOBDepth) × Features
- Features: `[Bid_P, Bid_V, Ask_P, Ask_V, Close, SRL_Residual, Epiplexity]`
- 完整规范见 `architect/current_spec.yaml`

### 文件地图
| 文件 | 角色 |
|------|------|
| `omega_epiplexity_plus_core.py` | 数学核心（SRL反演 + 拓扑注意力 + MDL损失） |
| `omega_webdataset_loader.py` | WebDataset 流式加载器 |
| `tools/omega_etl_v3_topo_forge.py` | V3 ETL 管线（原始数据→张量） |
| `tools/etl_lazy_sink_linux_optimized.py` | V2 ETL（已弃用但保留参考） |
| `tools/empirical_calibration.py` | 物理常数标定脚本 |
| `architect/current_spec.yaml` | 当前架构规范（动态公理源） |
| `omega_axioms.py` | 公理断言模块 |

---

## WHY: 核心哲学

### Taleb 反脆弱
- 尾部事件是信号，不是噪音
- 不对称收益比 > 3.0 是唯一的成功标准
- 小额试错 + 尾部暴利 = 正期望

### 压缩即智能
- MDL (Minimum Description Length): 用最短的描述长度解释数据
- 损失函数 = H_T (预测残差) + λ_s × S_T (结构复杂度)
- 模型被迫丢弃噪音，只保留可压缩的主力规则

### Karpathy 极简美学
- 一个文件能解决的不拆成两个
- 代码行数是负债，不是资产
- 简单 > 聪明

### Via Negativa（否定之道）
- 已证伪的路径记录在 `VIA_NEGATIVA.md`，永不重蹈
- 知道"什么不能做"比"什么能做"更有价值

---

## HOW: 不可违反的规则

### 物理公理（永恒，Layer 1）
1. δ = 0.5 — 平方根法则指数，宇宙拓扑常数，严禁修改或设为可学习参数
2. c — **已降级为 Layer 2** (per-stock 动态标定值，非永恒常数)。c_default=0.842 仅为 TSE 回退值。A股 c_i 通过 `tools/omega_srl_friction_calibrator.py` 实证标定
3. 空间轴不可被拍扁 — 张量必须保持 `[B, T, S, F]` 四维结构
4. 数值稳定性 — 输出不可包含 NaN 或 Inf

### 架构公理（可演进，Layer 2，从 `architect/current_spec.yaml` 读取）
5. 张量形状当前为 `[B, 160, 10, 7]`（以 spec 文件为准）
6. vol_threshold 冷启动默认值 = 50000
7. window_size = 160（ACF 衰减上限）
8. stride = 20（环形缓冲区步长）
9. adv_fraction = 0.02（动态阈值 = ADV × 此值）

### 破坏性操作红线
10. **删除数据文件** → 必须人工确认，无例外
11. **修改 δ=0.5** → 绝对禁止（c 已降级为 Layer 2 per-stock 标定值，可通过标定脚本更新）
12. **远程推送**（git push, scp 到生产节点）→ 必须人工确认
13. **修改 architect/current_spec.yaml** → 必须人工确认
14. **删除/覆盖已产出的 parquet/tar shard** → 必须人工确认
15. **同时运行多个 ETL 实例** → 禁止（单实例锁）

### 强制预检清单（部署任何东西之前）
16. 目标节点 SSH 连通性验证
17. 磁盘空间 > 20% 可用
18. 内存检查（无 OOM 风险）
19. `ps aux | grep python` — 无重复实例
20. 确认正确的节点（linux1 vs windows1 vs omega-vm）
21. 确认正确的 systemd slice（heavy-workload.slice）

### 工程规范
22. 重计算必须通过 `systemd-run --slice=heavy-workload.slice` 启动
23. 禁止紧密循环中的 `gc.collect()`
24. 禁止无条件 `use_threads=True`，必须先基准测试
25. ETL 脚本必须有单实例文件锁（fcntl.LOCK_EX）
26. PyArrow 读取必须用 `iter_batches`，禁止 `.collect()` 全量加载
27. batch_size 默认 500000，可通过环境变量 OMEGA_ETL_BATCH_SIZE 覆盖
28. **断点续传是强制要求** — 任何运行时间超过 1 小时的批处理脚本（ETL、标定、训练）必须实现断点续传机制：
    - 记录已完成的文件/batch/epoch 列表（checkpoint 文件或 shard 目录扫描）
    - 启动时自动检测已完成部分并跳过
    - 原因：CPython 内存碎片化（glibc malloc arena 不归还堆内存）导致长时间运行的进程 RSS 远超预期工作集。OOM 崩溃、SSH 断连、节点重启都会导致数十小时的工作归零。断点续传是唯一的工程保险

### 硬件拓扑（详见 `handover/HARDWARE_TOPOLOGY.md`）
29. **omega-vm** (当前节点): GCP US, 16GB RAM, 无 GPU — 控制节点
30. **linux1-lx**: AMD AI Max 395, 128GB RAM, 4TB+8TB SSD — 重计算节点
31. **windows1-w1**: AMD AI Max 395, 128GB RAM, 4TB+8TB SSD — 重计算节点
32. **zephrymac-studio**: Apple M4, 32GB — 架构师控制台

### SSH 路由
33. omega-vm → linux1: `ssh linux1-lx`
34. omega-vm → windows1: `ssh windows1-w1`
35. omega-vm → mac: `ssh zephrymac-studio`
36. 详细路由表见 `handover/HARDWARE_TOPOLOGY.md`

### 上下文管理
37. `handover/LATEST.md` — 当前项目状态的单一真相源
38. `VIA_NEGATIVA.md` — 已证伪路径（新 agent 必读）
39. `audit/` — 灾难复盘存档
40. `architect/current_spec.yaml` — 当前架构规范
41. `architect/INDEX.md` — 架构师指令时间线
42. `architect/insights/INDEX.md` — 架构师洞察索引（结构化决策卡片，可按 ID/类别快速检索）
    - `architect/insights/INS-NNN_*.md` — 原子化设计决策，每个裁决一张卡片
    - 与 `architect/directives/` 的区别：directives 是原始归档（完整原文），insights 是提炼后的结构化查询接口

### 灾难教训速查（完整版见 `audit/gemini_bitter_lessons.md`）
43. 物理常数由人类锁定，AI 只提供参考区间
44. 接收架构师指令 ≠ 授权执行
45. AI 不可自测自验（烟测独立于被测代码）
46. SSH 会话不继承 OOM 保护
47. V_old 数据在 V_new 验证完成前不可删除

### 用户画像
48. 独狼量化研究员，零编程基础 vibe coder
49. 优势是品味、市场洞察、Taleb 反脆弱哲学
50. 沟通偏好：中文为主，技术术语可用英文
51. 对代码解释需要简明扼要，避免过度技术化
