# VIA NEGATIVA — 否定之道日志

已证伪路径的永久记录。这些是项目在 V1-V3 演化过程中付出真实代价证明"不能做"的事情。任何未来的 AI agent 或架构变更都不得重蹈这些覆辙。

---

## 数学与架构

### Wall-Clock 时间轴 (V1) → 拓扑撕裂
- **证伪时间**: V1 全阶段
- **做了什么**: 使用物理时间（1分钟K线）作为时间轴
- **为什么失败**: 高流动性股票数据过密，低流动性股票数据过疏。神经网络接收到几何上不等价的 2D 矩阵，注意力机制无法对齐跨资产的微观结构
- **结论**: 时间轴必须是 Volume-Clock（容量时钟），不可用 Wall-Clock

### 拍扁空间轴 [160,7] (V2) → 维度坍缩
- **证伪时间**: V2 递归审计（架构师 Doc ID 1）
- **做了什么**: 将 LOB 深度维度拍扁，输出 `[160, 7]` 而非 `[160, 10, 7]`
- **为什么失败**: `FiniteWindowTopologicalAttention` 核心需要原生 2D 空间拓扑。拍扁空间轴 = 丢弃订单簿深度信息 = 模型退化为 1D 序列模型
- **结论**: 空间轴不可被拍扁。张量必须保持 `[B, T, S, F]` 四维结构

### 固定绝对容量阈值 (V2) → 大小盘不可比
- **证伪时间**: V2 中后期
- **做了什么**: 所有股票使用同一个 `vol_threshold=50000`
- **为什么失败**: 大盘股一天产出数百个 bar，小盘股一天不到 10 个。几何不等价回归
- **结论**: 容量阈值必须动态化（Rolling ADV × 2%），实现相对容量时钟

### Tumbling 不重叠窗口 (V2) → 信息腰斩
- **证伪时间**: V2→V3 过渡
- **做了什么**: 每积累 160 行就清空 buffer，产出一个张量
- **为什么失败**: 相邻张量之间没有重叠，丢失了约 50% 的时间连续性信息。跨窗口的机构累积模式被截断
- **结论**: 必须使用滑动窗口（Ring Buffer, stride=20），不可使用 tumbling 窗口

---

## 工程与性能

### gc.collect() 紧密循环 → 56% 性能回退
- **证伪时间**: 2026-03-17，linux1 ETL 微基准
- **做了什么**: 每处理 300K 行 batch 后调用 `gc.collect()`
- **为什么失败**: 强制全对象图扫描。Python 分代 GC 对短生命周期分块变量已足够高效
- **结论**: 禁止在紧密循环中调用 gc.collect()

### use_threads=True 无条件使用 → 反优化
- **证伪时间**: 2026-03-17，linux1 ETL 微基准
- **做了什么**: `batch.to_pandas(use_threads=True)` 用于简单表格转换
- **为什么失败**: 线程上下文切换开销 > 转换成本本身。无嵌套类型时多线程反而更慢
- **结论**: 必须先微基准测试，不可无条件 use_threads=True

---

## 运维与基础设施

### SSH 继承 oom_score_adj=-1000 → 内核死锁
- **证伪时间**: 2026-03-17 11:00-14:00，linux1
- **做了什么**: SSH daemon 配置了 OOMScoreAdjust=-1000，所有子进程继承
- **为什么失败**: ETL 进程超出 cgroup 内存限额 → OOM killer 触发 → 但所有进程都标记为不可杀 → 内核死循环 "Out of memory and no killable processes"
- **结论**: 用户工作进程不可继承 SSH 的 OOM 保护。重计算必须走 heavy-workload.slice

### 双实例 ETL 未检测 → 内存翻倍
- **证伪时间**: 2026-03-17，linux1
- **做了什么**: AI 重复启动了第二个 ETL 实例，未检查是否已有实例运行
- **为什么失败**: 两个实例合计内存 > cgroup 限额，直接触发 OOM
- **结论**: 单实例文件锁是强制要求（fcntl.LOCK_EX）

---

## 并行架构

### Symbol 级并行（每 worker 读全部文件）→ 单节点 I/O 灾难
- **证伪时间**: 2026-03-19，linux1 全量 ETL
- **做了什么**: 12 workers 各处理 ~443 只 symbol，但每个 worker 都读全部 743 个 parquet 文件（每文件 73M 行）。设计意图是通过 PyArrow `pc.is_in` 过滤只处理 8% 的行
- **为什么失败**: 12 workers 同时读同一文件 → ZFS NVMe I/O 争抢 → 单文件 580s（单 worker 仅 235s）。总 ETA 从预估 6h 暴涨到 120h。I/O 带宽被 12 路重复读取浪费，CPU 利用率反而只有 2.5%（97% idle）
- **数据证据**: 单 worker: 235s/文件, 2.5% CPU; 12 workers: 580s/文件, 2.5% CPU（I/O bound 而非 CPU bound）
- **结论**: Symbol 级并行在单节点上因 I/O 重复读取必定比单 worker 慢。真正的并行必须是**文件级分割**（不同 worker 读不同文件），但这又打断跨文件状态连续性。在当前架构下，单 worker + batch 优化（to_numpy 替代 .as_py()）是最优解

### 非 A 股代码混入 ETL → 垃圾 shard
- **证伪时间**: 2026-03-19，30 只股票烟测
- **做了什么**: c_registry 含 8366 个代码，其中 3054 个是债券、ETF、基金、逆回购等非 A 股标的
- **为什么失败**: 204001.SZ（国债逆回购）价格是利率而非股价，VWAP 计算产生 2.55×10¹⁶ BP 的荒谬 target。这些标的的 LOB 结构与 A 股完全不同
- **结论**: ETL 必须在入口过滤非 A 股代码。有效前缀：000/001/002/003/300/301/600/601/603/605/688/689

### 无断点续传的长时间 ETL → CPython 内存碎片 OOM 风险
- **证伪时间**: 2026-03-20，linux1 全量 ETL
- **做了什么**: 单 worker ETL 处理 743 个文件（预计 ~50h），无断点续传机制
- **为什么危险**: CPython + glibc malloc arena 碎片化导致 RSS 持续膨胀。预期工作集 ~863MB，实际 RSS 32.8GB（38x 超出），线性外推到 743 文件为 71.7GB，超过 61GB 可用 RAM。根因：`bar_ticks_prices/vols` 列表在每根 volume bar 完成后清空重建（~570 亿次 float 对象分配/释放），`bar_buffer = bar_buffer[trim:]` 列表切片（~128 万次），glibc malloc arena 被碎片化的小对象"钉住"无法归还 OS
- **结论**: 任何 ETA > 1h 的批处理脚本必须实现断点续传（已完成文件跳过）。一旦 OOM 崩溃，无断点续传 = 数十小时工作归零

### SSH pipe 并行上传 → 空文件 + 带宽反优化
- **证伪时间**: 2026-03-23，omega-vm → GCS 上传
- **做了什么**: 7 路并行 SSH pipe (`ssh linux1 'cat shard' | gsutil cp - gs://...`)
- **为什么失败**: (1) 7 路共享 linux1 上行带宽 ~3-4 MiB/s，每路降到 0.5 MiB/s，单 shard 从 54s 暴涨到 13min。(2) SSH 断开后 gsutil 仍创建 0 字节目标文件 → 476/1992 shards 损坏。(3) 修复脚本用 `while read` 循环，但 `ssh` 偷走了 stdin → 只修了 1 个就退出
- **结论**: 并行度不可超过带宽阈值（4 路最优）。上传后必须验证文件大小。脚本避免 `while read` + SSH 同时用 stdin（改用 `mapfile` + `for` 循环）

### 未标准化的原始特征直接输入神经网络 → 梯度爆炸
- **证伪时间**: 2026-03-24，Vertex AI v3/v7/v8
- **做了什么**: 原始价格（厘，25K-5M）和成交量（~10M）直接输入 `nn.Linear(6, 64)`
- **为什么失败**: 激活值 ~百万级 → MSE loss 90M → 1000 步后梯度爆炸 NaN。fp16 AMP 时第 0 步就溢出（65504 上限）。CPU 烟测 5 步看不出问题
- **结论**: 永恒工程公理 — 所有数值特征进入模型前必须压缩到 [-30, 30]。`log1p`（非负）或 `symlog`（含负值）是标准手段

### 本地 CPU 烟测通过 → 相信 GPU 训练也能通过
- **证伪时间**: 2026-03-24，v1-v9 连续失败
- **做了什么**: CPU 烟测 batch=4 × 5 steps 全通过（FVU 下降），直接提交 GPU 全量训练
- **为什么失败**: CPU/GPU 精度不同（fp32 vs fp16）、数据覆盖率不同（20 samples vs 256 万）、PyTorch 版本不同（2.6 vs 2.2）、存储后端不同（本地 NVMe vs gcsfuse）
- **结论**: 烟测必须在**目标环境**执行。Vertex AI 训练前必须先提交 `--epochs=1 --steps_per_epoch=100` 快速烟测 job

---

## 云基础设施

### gcsfuse 当真实文件系统用 → stat 假死 + 并发读取损坏
- **证伪时间**: 2026-03-24，Vertex AI v4-v6
- **做了什么**: (1) `os.path.getsize()` 遍历 1992 个 shard 做预过滤；(2) `num_workers=4` 的 DataLoader 并发读取 gcsfuse 挂载的 .tar 文件
- **为什么失败**: (1) gcsfuse 的 stat 需要同步 GCS API 请求，1992 次 → 几分钟假死。(2) 多 worker 并发读同一 tar 文件导致流断裂 `tarfile.ReadError`，且 WebDataset 的 `warn_and_continue` handler 无法捕获 DataLoader worker 进程内的异常
- **结论**: gcsfuse 上禁止批量 stat。WebDataset 管道必须全链路 handler。如需 multi-worker 安全，必须确保 shard 完整性或用 try/except 包裹批读取

---

## AI 治理

### AI 自己写烟测测自己 → 自洽性掩盖正确性
- **证伪时间**: 2026-03-17~18，V3 smoke test
- **做了什么**: Gemini 编写 V3 ETL，然后编写 smoke test 验证自己的输出
- **为什么失败**: 如果 AI 对张量形状有系统性误解，测试和代码会"一致地错误"。自洽 ≠ 正确
- **结论**: 审计/烟测必须独立于被测代码的作者

### 接收架构师指令即执行 → 188GB 数据丢失
- **证伪时间**: 2026-03-17 晚
- **做了什么**: Gemini 收到架构师的 V3 指令后，未经用户确认即删除 188GB V2 数据并开始 V3 改造
- **为什么失败**: 架构师指令是"方向性的"，不是"立即执行的"。V2 数据在 V3 验证完成前应当保留
- **结论**: 接收指令 ≠ 授权执行。破坏性操作必须经人工确认

---

## Vertex AI HPO + Spot VM

### Epoch 级 checkpoint + Spot VM → 训练进度全部丢失
- **证伪时间**: 2026-03-25，Phase 4 HPO v1
- **做了什么**: 仅在 epoch 结束时保存 checkpoint（每 30 分钟），使用 Spot VM
- **为什么失败**: Spot L4 在 us-central1 白天平均 ~10 分钟被抢占一次，远短于一个 epoch。20 个 trial 全部在 Epoch 0 中途被抢占，无有效 checkpoint，SIGTERM 报告 best_fvu=inf，Vizier 判定全部 INFEASIBLE
- **结论**: Spot VM 训练必须使用 step 级 checkpoint（每 500 步 / ~3 分钟）。Epoch 级 checkpoint 在 Spot 环境下等于没有 checkpoint

### float("inf") 作为 HPO metric → Vizier 全盘判死
- **证伪时间**: 2026-03-25，Phase 4 HPO v1
- **做了什么**: SIGTERM handler 报告 best_fvu=float("inf")（因为 validation 未执行，best_fvu 从未更新）
- **为什么失败**: Vizier API 拒绝 inf 作为 objective value（"Invalid objective value: inf"），将 trial 标记为 INFEASIBLE。20/20 trials 全部 inf → HPO job 直接 FAILED
- **结论**: 任何报告给 Vizier 的 metric 必须是有限实数。用 999.0 或 batch 级 FVU 兜底

### 不同 HPO job 复用同一 checkpoint 目录 → 架构不兼容崩溃
- **证伪时间**: 2026-03-25，Phase 4 HPO v2
- **做了什么**: v2 HPO job 的 trial 1-20 使用了与 v1 相同的 output_dir（phase4/trial_${ID}）。v1 的 checkpoint 含不同超参的 state_dict
- **为什么失败**: v2 Trial 12（hidden=128）加载 v1 Trial 12（hidden=256）的 checkpoint → model.load_state_dict() shape mismatch → RuntimeError → "Internal error" → INFEASIBLE
- **结论**: 每次 HPO 提交必须使用唯一的 output base dir（如 phase4_v3）。或在 load_checkpoint 中加 try/except 处理不兼容情况

### Vertex AI 离散参数传递为 float 字符串 → argparse int() 崩溃
- **证伪时间**: 2026-03-25，Gemini 审计发现
- **做了什么**: argparse 使用 type=int，但 Vertex AI Vizier 传递离散值为 "128.0"（float 字符串）
- **为什么失败**: Python int("128.0") 抛出 ValueError。所有含离散参数的 trial 启动即崩溃
- **结论**: HPO 可搜索的整数参数必须用 type=lambda x: int(float(x))

### 云资源分配不算就猜 → 两次 disk-full + 放弃正确方案
- **证伪时间**: 2026-03-27，Vanguard v1/v2/v3
- **做了什么**: (1) 用默认 100GB disk 拷贝 164GB 数据 → 失败。(2) 猜测涨到 500GB → 还是失败。(3) 放弃 NVMe，回退到 gcsfuse 慢方案。(4) gcsfuse 跑了 13h，不敢中断优化
- **为什么失败**: 从未计算实际磁盘需求（gsutil 显示需要 556GB）。两次失败后恐惧驱动决策，选择"安全但慢"而非排查根因。已有 checkpoint/resume 能力却忘记利用
- **结论**: (1) 云资源分配必须先计算再申请，留 2x 安全余量。(2) 连续失败时排查根因，不要回退到次优方案。(3) 慢速 job 如果有 checkpoint，随时可以中断改进再 resume——不要被沉没成本绑架

### bash -c 吞噬 HPO 超参 → 100 个 trial 用同一默认参数
- **证伪时间**: 2026-03-25，Gemini 审计发现
- **做了什么**: containerSpec 使用 bash -c "pip install && python3 train.py --固定参数"，Vertex AI 将 HPO 参数追加到 args 列表末尾
- **为什么失败**: bash -c "cmd" 之后的参数变成 $0, $1 等位置变量，不会传递给 cmd 内部的 python3。所有 trial 实际运行的是完全相同的默认参数
- **结论**: 必须在 bash -c 脚本末尾加 "$@"，并在 args 列表中追加 "_" 作为 $0 占位符
