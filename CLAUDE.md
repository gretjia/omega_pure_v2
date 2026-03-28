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
10. **删除/覆盖数据文件**（含 parquet/tar shard）→ 必须人工确认，无例外
11. **远程推送**（git push, scp 到生产节点）→ 必须人工确认
12. **修改 architect/current_spec.yaml** → 必须人工确认
13. **同时运行多个 ETL 实例** → 禁止（单实例锁）

### 强制预检清单（部署任何东西之前）
14. 目标节点 SSH 连通性验证
15. 磁盘空间 > 20% 可用
16. 内存检查（无 OOM 风险）
17. `ps aux | grep python` — 无重复实例
18. 确认正确的节点（linux1 vs windows1 vs omega-vm）
19. 确认正确的 systemd slice（heavy-workload.slice）

### 云资源与训练部署
20. **云资源分配先算后申请** — 磁盘/内存/配额必须计算实际需求 + 2x 安全余量，禁止猜测
21. **失败后排查根因** — 连续失败时分析 WHY 而非回退到次优方案
22. **checkpoint = 随时可中断优化** — 慢速运行的 job 如果有 checkpoint，应主动建议中断改进再 resume，不被沉没成本绑架

### 工程规范
23. 重计算必须通过 `systemd-run --slice=heavy-workload.slice` 启动
24. 禁止紧密循环中的 `gc.collect()`
25. 禁止无条件 `use_threads=True`，必须先基准测试
26. ETL 脚本必须有单实例文件锁（fcntl.LOCK_EX）
27. PyArrow 读取必须用 `iter_batches`，禁止 `.collect()` 全量加载
28. batch_size 默认 500000，可通过环境变量 OMEGA_ETL_BATCH_SIZE 覆盖
29. **断点续传是强制要求** — >1h 批处理必须实现 checkpoint（OOM/断连/重启时零工作损失）

### 硬件拓扑与 SSH（详见 `handover/HARDWARE_TOPOLOGY.md`）
27. 四节点：omega-vm（控制，16GB，无GPU）→ linux1-lx / windows1-w1（计算，AMD AI Max 395，128GB）→ zephrymac-studio（架构师，M4，32GB）
28. SSH 别名：`ssh linux1-lx` | `ssh windows1-w1` | `ssh zephrymac-studio`

### 上下文管理
29. `handover/LATEST.md` — 当前项目状态的单一真相源
30. `VIA_NEGATIVA.md` — 已证伪路径（新 agent 必读）
31. `audit/` — 灾难复盘存档
32. `architect/current_spec.yaml` — 当前架构规范
33. `architect/INDEX.md` — 架构师指令时间线
34. `architect/insights/INDEX.md` — 结构化决策卡片（directives = 原始归档，insights = 提炼后查询接口）
35. 审计等重输出通过 Agent 子进程执行，仅返回 verdict + 关键发现，防止主上下文膨胀

### 灾难教训速查（完整版见 `audit/gemini_bitter_lessons.md`）
36. 物理常数由人类锁定，AI 只提供参考区间
37. 接收架构师指令 ≠ 授权执行
38. AI 不可自测自验（烟测独立于被测代码）
39. SSH 会话不继承 OOM 保护
40. V_old 数据在 V_new 验证完成前不可删除

### 用户画像
41. 独狼量化研究员，零编程基础 vibe coder
42. 优势是品味、市场洞察、Taleb 反脆弱哲学
43. 沟通偏好：中文为主，技术术语可用英文
44. 对代码解释需要简明扼要，避免过度技术化
