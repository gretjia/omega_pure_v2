# OMEGA LESSONS — 压缩后的唯一经验源

> 压缩即智能：元公理生成具体规则，操作手册指向可执行脚本，案例库每条 ≤ 2 行。
> 原始证据存档于 `VIA_NEGATIVA.md`（已冻结）和 `audit/gemini_bitter_lessons.md`。

---

## 元公理（Ω1-Ω6）

从 Phase 1-7 全部灾难中蒸馏的否定性智慧。违反任何一条 = 灾难必现。

| # | 元公理 | 一句话 |
|---|--------|--------|
| Ω1 | **只信实测，不信推断** | 报告/状态/ETA 必须由命令输出生成，不可由 agent 推断或猜测 |
| Ω2 | **先量化，后行动** | 资源承诺前必须有 `du -sh` / `df -h` / 带宽实测 |
| Ω3 | **测试环境 = 生产环境** | 本地 smoke 永不授权生产部署；canary 必须在目标环境用精确镜像 |
| Ω4 | **可执行 > 可记忆** | 已知最优方法必须固化为 wrapper 脚本，不可仅存在于文档或记忆 |
| Ω5 | **生产者 ≠ 验证者** | 写代码的 agent 不可独自验证该代码；外部审计不可删除 |
| Ω6 | **数据在哪，计算在哪** | 大数据不搬运；计算靠近存储 |

**公理管理规则**：数量严格 ≤ 8。新教训先归入已有公理。公理膨胀 = 压缩失败。

---

## 操作手册（按场景索引 → 指向可执行脚本）

### 上传 shard 到 GCS
**用**: `bash gcp/safe_upload.sh <shard_list_file>`
- 路径: linux1 → HK(反向隧道 localhost:2226) → GCS（Ω6）
- 方法: mapfile + for + ssh -n（Ω4, 编码在脚本中）
- 验证: 每个 shard 上传后自动检查 size > 0（Ω1, 编码在脚本中）
- **禁止**: `upload_shards.sh`（已废弃重命名），SSH pipe `ssh cat | gsutil cp -`

### 构建 Docker + 部署推理
**用**: `bash gcp/safe_build_and_canary.sh <phase> <version>`，然后 `bash gcp/safe_submit.sh <phase> <version>`
- Step 1: 本地 py_compile + regression test（`tests/test_known_bugs.py`）
- Step 2: Docker build + push
- Step 3: 1-shard canary 在 Vertex AI L4 上验证（Ω3）
- Step 4: Canary PASS → 写入 `gcp/manifest.jsonl` → 允许全量提交
- **禁止**: 直接 `gcloud ai custom-jobs create`（pre-deploy-gate hook 会阻止）

### 生成 Vertex AI 推理 Job Config
**用**: `bash gcp/gen_inference_config.sh <checkpoint> <output> [--hd N] [--wt N] [--ws N] [--spot]`
- 自动内嵌: Local NVMe SSD(C-028) + GPU auto-detect(C-039) + checkpoint_interval>0(C-032)
- **禁止**: 手写 gcp/*.yaml（lesson-enforcer.sh hook 会拦截 pd-ssd 写入）
- 三层防御: (1) gen_config 模板 → (2) lesson-enforcer.sh PreToolUse hook → (3) safe_submit.sh diskType 硬检查

### 新代码开发
**用**: `/dev-cycle <任务描述>`
- Stage 0（新增）: Pre-mortem — 列 3 个方案 + 失败模式 + 选最优
- Stage 1-7: Plan → Audit → Code → Audit → Axiom → External Audit → Summary
- **禁止**: 跳过 dev-cycle 直接写代码部署

### Cron 监控报告
- 只用 Job ID + Docker tag（从 `gcp/manifest.jsonl` 读取）
- 不自己起名字，不混用版本号
- 必须包含: 进度%、健康度、ETA（由日志实测计算，非猜测）（Ω1）

### 远程节点操作
- 部署前必跑 `/pre-flight <node>`
- SSH 工作负载走 `systemd-run --slice=heavy-workload.slice`
- 日志必须 `PYTHONUNBUFFERED=1`（否则 nohup 缓冲导致"无输出"）

---

## 案例库（每条 ≤ 2 行，编号索引）

### 数学与架构
- **C-001**: Wall-Clock 时间轴 → 拓扑撕裂。必须 Volume-Clock
- **C-002**: 拍扁空间轴 [160,7] → 维度坍缩。必须保持 [B,T,S,F] 四维
- **C-003**: 固定绝对容量阈值 → 大小盘不可比。必须 Rolling ADV × 2%
- **C-004**: Tumbling 不重叠窗口 → 信息腰斩。必须 Ring Buffer stride=20

### 工程与性能
- **C-005**: gc.collect() 紧密循环 → 56% 性能回退。禁止
- **C-006**: use_threads=True 无条件使用 → 反优化。必须先基准测试
- **C-007**: 未标准化原始特征 → 梯度爆炸 NaN。所有特征 log1p/symlog 压到 [-30,30]
- **C-008**: squeeze() 对单 sample → 维度坍塌。永远用 view(-1)
- **C-009**: WebDataset 迭代器 ValueError 在 for 内部抛出。try/except 包整个 for 循环

### 基础设施
- **C-010**: SSH OOM 继承 → 内核死锁。重计算走 heavy-workload.slice
- **C-011**: 双实例 ETL → 内存翻倍 OOM。单实例锁 fcntl.LOCK_EX
- **C-012**: SSH pipe 7 路并行上传 → 476 空文件。用 safe_upload.sh（≤4路 + 验证）
- **C-013**: 修复操作不验证就报告成功 → 115/200 仍为空。"修了 ≠ 修好了"（Ω1）

### 云部署
- **C-014**: GCS FUSE 当本地磁盘 → Python 优化无效。先 staging 到 pd-ssd
- **C-015**: CPU smoke 通过 → 相信 GPU 也通过 → 9 版连续失败。用 canary（Ω3）
- **C-016**: 云资源不算就猜 → disk-full × 2。先 `gsutil du -sh`（Ω2）
- **C-017**: bash -c 吞 HPO 超参 → 100 trial 同默认参数。末尾加 `"$@"` + `_`
- **C-018**: Epoch 级 checkpoint + Spot VM → 进度全丢。必须 step 级（每 500 步）
- **C-019**: float("inf") 报给 Vizier → 全盘 INFEASIBLE。兜底 999.0
- **C-020**: 不同 HPO 复用同一 checkpoint 目录 → 架构不兼容崩溃。唯一 output dir

### 训练
- **C-024**: MSE Anchor dampening → Std_yhat 爆炸 + 过拟合 (Train IC=0.18, Val IC=0)。Anchor 必须对称（Ω1: 实测 val IC）
- **C-025**: downside_dampening=0.05 → 丢弃 50% 数据 → 19.7K 模型过拟合。最小 0.3（Ω2: 先量化数据量）
- **C-026**: pipe 对推理最优（单 pass 556GB），对训练是瓶颈（20 epoch = 11.1TB + 验证 15min > 训练 13min）。训练必须 staging（Ω6）
- **C-027**: HPO 搜出的超参只对当时的 Loss 有效。换 Loss 后 anchor_weight=0.001→Std_yhat 爆炸。非对称 Loss 需 anchor≥0.01（Ω2: 先量化）

### GCS / 云 I/O
- **C-028**: pd-ssd 吞吐与容量挂钩（0.48 MB/s per GB）→ 800GB 仅 384 MB/s。训练数据必须用 Local SSD（4.8 GB/s）或 FUSE v2 file-cache（Ω2: 先量化 IOPS）
- **C-029**: GCS Nearline 看似省钱（$5.5 vs $11/月），但 20 epoch × 556GB = 11.1TB 检索费 $111。训练数据必须 Standard（Ω2: 先量化总成本）

### 配置管理
- **C-030**: 热修复配置错误时**只改出错字段，禁止重写整个文件**。Phase 10: `pd-balanced` 报错→重写 YAML→静默丢掉 Local SSD→FUSE 裸跑 11h/$9（预期 4h/$3）。修复后必须 diff 原始推荐 vs 修改后（Ω1: 只信实测，不信"我改好了"）
- **C-031**: Vertex AI `bootDiskType` 只接受 `pd-ssd`/`pd-standard`/`hyperdisk-balanced`，不接受 `pd-balanced`。Canary `bootDiskSizeGb` 最小 100GB（不是 50GB）（Ω2: 先查 API 约束再写配置）
- **C-032**: `checkpoint_interval=0` 导致 `% 0` 除零崩溃。任何用作除数/模数的参数必须在使用前检查 > 0（Ω1: 测试不能只跑默认值）
- **C-033**: ETA 计算引用了外部审计的假设值（NVMe 吞吐）但实际部署在 pd-ssd → 预估 4h 实际 12h。ETA 必须用 Epoch 0 实测 pace 校准，不可引用非本次运行的推算（Ω1: 只信实测）
- **C-034**: batch_size 翻倍（128→256）导致训练 I/O 翻倍，但 ETA 未重新计算。改变任何影响 I/O 吞吐的参数后必须重新量化 ETA（Ω2: 先量化后行动）

### CPU 推理性能
- **C-035**: PyTorch CPU `set_num_threads(16)` 导致严重线程争用：16线程=23 samples/s, 1线程=131 samples/s (5.7x差距)。小模型 CPU 推理必须先 benchmark 线程数（Ω2: 先量化后行动）
- **C-036**: 8进程并行推理在内存带宽受限机器上比单进程更慢（87→70 shards/h）。多进程不等于加速，必须实测（Ω1: 只信实测）
- **C-037**: Phase 10 checkpoint window_size=(32,4) 但推理脚本默认 window_size_s=10 → state_dict shape mismatch。checkpoint 和推理参数必须从同一 config 读取（Ω4: 可执行>可记忆）
- **C-038**: `phase7_inference.py` final flush 缺少 `z_sparsity` 列 → PyArrow concat_tables 会直接崩溃（schema不一致报错）。多处写同一 schema 时，所有写入点必须同步维护（Ω5: code review）
- **C-039**: `device = torch.device("cpu")` 硬编码导致 Vertex AI L4 GPU 空转、CPU 跑 23h/$25。设备选择必须 auto-detect `torch.cuda.is_available()`，不可硬编码（Ω6: 计算匹配硬件）
- **C-040**: 推理 job 多次用 pd-ssd（C-028 已禁）+ gen_config 模板硬编码 bootDiskSizeGb=200（装不下 556GB shard）。**修正: lesson-enforcer.sh hook 已部署拦截 pd-ssd 写入; gen_config.sh 模板已固化 1300GB**（Ω4: 可执行>可记忆）
- **C-041**: Vertex AI 容器**所有机型**均无法 mount Local NVMe SSD（permission denied，非仅 g2）。Vertex AI API 只支持 bootDisk (pd-ssd/pd-standard)，不支持 localSsdSpec。训练 staging 唯一方案: pd-ssd 大容量 boot disk（Ω2: 先查 API 规格再写配置）

### 训练稳定性
- **C-042**: Z-score 标准化是仿射不变的 → 梯度与权重正交 → 勾股漂移: W² 单调膨胀 → S_T 爆炸 → NaN。修复: std 必须 `.detach()` + `clamp(min=1.0)`（Ω1: Phase 11a 5 epoch 全部 NaN 实测确认）
- **C-043**: λ_s 必须与 Loss 量纲匹配。IC Loss≈0.05 时 λ_s=1e-7 可行，Softmax Loss≈10 时 λ_s 需 ≥2e-5 (200x)。换 Loss 后必须重新标定 λ_s（Ω2: 先量化量纲差）
- **C-044**: `--resume` + 相同 `output_dir` → 加载旧 checkpoint 跳过训练。换 Loss/超参后必须用新 output_dir（如 v1→v2），否则复用废弃 checkpoint 假完成（Ω1: 只信实测，C-020 同类教训）
- **C-045**: 乱序 WebDataset(188 shards 随机流式) + Softmax(dim=0)/Batch Z-score → 跨期 Batch 毒药：模型识别宏观牛熊 Beta 比微观 Alpha 简单 1000x → logit 膨胀 6956 BP。绝对禁止 Batch 维度归一化（Ω1: Phase 10 十分位拆解实证确认）
- **C-046**: z_sparsity(L1) ≈ 0 是"脑死亡"非"最高压缩"。模型关闭 z_core 全部通道逃避 λ_s → 靠 Bias 盲赌 Beta。L1 非零才代表真智能涌现。Gating 必须保留高 L1 剔除低 L1（Ω1: Z-D0 IC 为负, Z-D9 IC 为正）
- **C-047**: Spot SIGTERM 期间 torch.save 直写 /gcs/ FUSE → FUSE 缓存来不及 flush → checkpoint 损坏(0 byte)。修复: 先写本地 /tmp staging → shutil.copy2 到 FUSE → os.sync() 强制刷盘（Ω4: Gemini 审计发现）
- **C-048**: 训练 I/O 策略决策树: (1) 推理(单 pass) → pipe 模式(100GB disk, Phase 7 实测 466 shards/h); (2) 训练(多 epoch) → pd-ssd staging(1300GB, C-026); (3) FUSE file-cache + resampled=True → cache thrashing 灾难（Ω2: 先量化 I/O 模式再选方案）
- **C-049**: Train-Serve Skew 恶魔（训练目标变更但推理代码未同步更新）。Phase 11c 改输出绝对 BP，推理仍残留 `* TARGET_STD` 反向缩放，导致 20 BP 预测暴涨至 4319 BP，摧毁回测引擎。架构变更（如 Loss 量纲）必须**同步审查全栈文件**，避免前线突变而后勤崩溃（Ω5: 验证链对齐）。
- **C-050**: 局部修复残留"死代码/幽灵 Bug"。废弃架构级变量（TARGET_STD）或算子（.squeeze()）时，必须 `grep -r` 全栈扫描，不可只改报错行。Gemini 修复遗漏 4 处 .squeeze() + 引入 IndentationError 致 train.py 无法编译（Ω5: 验证者自身也需审计）。
- **C-051**: 量纲剧变与方差坍缩。更换 Loss（如 Softmax→Pointwise Huber）或移除归一化后，梯度尺度剧变，必须重标定 λ_s 和 Huber δ。Phase 11c δ=50 削峰 + λ_s=1e-3 结构税 → z_core 脑死亡（0.44%），模型输出均值常数 ~30 BP。仪表盘 Std_yhat 被旧代码 *216x 放大为幻觉（Ω1: 只信实测）。
- **C-052**: **长训练前必须独立烟测**。Phase 11c 跑完 20 epoch (~9h GPU) 才发现模型脑死亡（pred_std=5.6 BP）。长训练（>2h）启动后 E0-E1 完成时必须：(1) 用修复后推理脚本跑 checkpoint（不是训练日志），(2) 断言 pred_std 在物理区间。仪表盘可能被旧 Docker 代码污染，仅靠日志判断健康是自欺欺人（Ω1: 只信实测，Ω3: 测试环境=生产环境）。
- **C-053**: **Docker 构建时间点 vs 代码修复时间点必须对齐**。Phase 11c Docker `phase11-v3` 在修复 `d744c4d` 之前构建，训练用旧代码（含 `*TARGET_STD`），仪表盘 15 epoch 全是 216x 幻觉。代码修复后必须重建 Docker + canary，"git 上修了"不等于"Docker 里也修了"（Ω3: 测试环境=生产环境）。
- **C-054**: **范式切换是全栈原子事件，不是单点修改**。Softmax→Pointwise Huber 触发 6 个级联故障（λ_s 量纲、推理缩放、仪表盘幻觉、Docker 错位、HPO 过时、Epiplexity 前提破坏），逐个发现逐个救火，耗 9h GPU + 4h 人力。范式切换必须执行**原子 checklist**：(1) grep 全栈受影响变量, (2) 重标定正则化超参, (3) 重建 Docker + canary, (4) E1 后独立烟测, (5) 更新 spec + HPO, (6) 同步推理/回测脚本。不走 checklist = 埋定时炸弹（Ω4: 可执行>可记忆）。
- **C-056**: **监控不行动 = 没有监控**。Phase 11d 夜间 Config B 被 Spot 抢占→FAILED，cron 脚本只报告不重提交，用户醒来才发现。自动化监控必须包含自动修复能力（至少：Spot FAILED→重提交），否则"无人值守"是假的（Ω4: 可执行>可记忆）。
- **C-055**: **阈值也要实测标定，不能拍脑袋**。Phase 11d 方差哨兵的 10/30 BP 红线来源：架构师直觉（基于 216x 幻觉时代）+ 5 shard 粗估的 1.6x 乘数。这只是早期预警粗估，不可作为最终判据。正确做法：训练完成后用全量 val 烟测，实测 pred_std 与 D9-D0 spread 的映射关系，用数据定阈值（Ω1: 只信实测，Ω2: 先量化后行动）。
- **C-057**: **代码默认值必须与 spec 同步，OOM 补丁不可静默残留**。`train.py` 和 `gcp/train.py` 的 `--window_size_s` 默认值为 4（早期防 OOM 临时改的），而 spec `fixed_params.window_size_s=10`（完整 LOB 10 档深度）。Phase 11 全部训练只看了 4 档浅水区，Topology Attention 丧失 60% 深水区机构挂单信息，z_core 无特征可编码。临时 OOM 补丁必须在 issue 解决后立即回退，否则就是静默降级（Ω1: 只信实测 — 代码 default 才是实测值，不是 spec 文档）。

- **C-058**: **双副本必然漂移——靠记忆同步违反 Ω4**。Phase 12 烟测 ImportError: `gcp/omega_epiplexity_plus_core.py` 缺新函数。根因：gcp/ 维护根目录文件副本，Dockerfile 从 gcp/ 构建，dev-cycle 只同步了 train.py 忘了核心模块。C-053 教训没防住因为它只说"重建 Docker"，没覆盖"构建源文件本身是旧的"。**结构性修复：`safe_build_and_canary.sh` Step 1b 自动解析 Dockerfile COPY 指令，diff 每个源文件与根目录，不一致则 ABORT。** 从此漂移被机器拦截，不靠人记忆（Ω4: 可执行>可记忆）。

- **C-061**: **每次烟测必须用唯一 output_dir，否则旧 checkpoint 触发 resume 跳过训练**。Phase 12 烟测 v3b 复用 `phase12_smoke_v1` 目录，train.py 自动从旧 checkpoint resume 到 E2 直接完成，新 Loss 代码根本没执行。这是 C-044 的变种（换 Loss/超参后必须用新 output_dir），泛化为：任何需要验证新代码的运行，output_dir 必须唯一。格式建议 `phase12_smoke_v{N}`（Ω1: 只信实测 — "训练完成"不等于"新代码被执行"）。
- **C-060**: **部署命令必须从目标环境反推，不可从本地路径假设**。烟测 YAML 写 `/app/tools/phase7_inference.py`，但 Dockerfile COPY 到 `/app/`。又写 `--shard_dir` 但漏了 `--date_map`（必需参数）。两次提交两次白跑。写远程命令前必须：(1) 读 Dockerfile 确认文件路径 (2) 读目标脚本 `argparse` 确认必需参数 (3) 不假设本地目录结构=容器目录结构（Ω1: 只信实测，Ω3: 测试环境=生产环境）。
- **C-062**: **torch.compile 的 `_orig_mod.` 前缀会静默毁掉推理**。torch.compile 给 state_dict key 加 `_orig_mod.` 前缀，`load_state_dict(strict=False)` 不匹配时静默跳过所有 key → 推理用随机权重。修复：save 端 strip 前缀 + load 端防御性 strip + 打印诊断日志。`strict=False` 是危险的沉默杀手（Ω1: 只信实测 — "加载成功"不等于"权重被加载"）。
- **C-063**: **GCS pipe (`pipe:gcloud storage cat`) 不可用于推理**。gcloud CLI 子进程缺少中途字节范围重试，网络微中断 → EOF → shard 丢失。训练可容忍（shuffle+handler 重试），推理不行（每个 shard 必须完整）。Vertex AI 正确方案：GCS FUSE `/gcs/` 路径直读（自动重试+预读缓冲+零安装）。`pipe:` 仅限训练容错场景（Ω6: 数据在哪计算在哪 + Ω2: 先量化 I/O 可靠性）。
- **C-064**: **推理 job staging 必须只下载需要的 split，提前计算磁盘需求**。Phase 12 post-flight staging 全量 1992 shards (1.8TB) 到 500GB pd-ssd → 磁盘满 FAILED。val-only = 399 shards (~400GB)。下载前必须：`shard 数 × 平均 shard 大小 < disk * 0.8`（Ω2: 先量化后行动）。

- **C-067**: **"同意原则"后立刻违反 = 没有原则**。Claude 口头同意"先验证管线再跑"，下一个动作就提交推理 job。AI 的短期记忆不可信，必须用规则（R-017）强制约束行为。"同意"必须转化为可执行规则，否则只是噪声（Ω4: 可执行 > 可记忆）。
- **C-065**: **训练指标好看 ≠ 模型有效 — 范式切换前必须先验证推理管线**。Phase 6→12 每次训练 val 指标好看，post-flight 全部失败。Phase 6 完美单调递减 deciles [3.33→-2.59] 是 bug 特征，不是模型弱。**新训练被阻塞，直到历史 checkpoint 用修复后代码重跑 post-flight 并翻正**（Ω1: 只信实测）。
- **C-066**: **不要用换 Loss 来解决管线 bug**。Phase 6 IC Loss���Phase 9 Pearson→Phase 10 Softmax→Phase 11 Huber→Phase 12 MSE，7 次换 Loss，7 次 post-flight 失败。Gemini 诊断："你在用换 Loss 函数来解决管线工程 bug"。正确做法：先修管线（Train-Serve Skew / 评估指标 / 架构瓶颈），验证管线健康，**然后**才评估 Loss（Ω1 + Ω4: 可执行的管线验证 > 可讨论的 Loss 理论��。

- **C-059**: **量纲必须从数据源头追溯，不可假设；修复时必须逐变量分析，不可一刀切**。ETL 输出 target 已是 BP，架构师指令假设 raw decimal 导致 target double-convert（C-059a）。修复时一刀切去掉 pred 和 target 的 ×10000，但 model output 是 raw logit（~0.07）vs target ~20 BP → 梯度冻死（5e-9/step），模型无法学习（C-059b）。正确组合：`pred×10000`（投影到 BP）+ target 不动（已是 BP）+ `/scale_factor` 抵消链式法则。教训：量纲修复必须对每个变量独立追溯源头，不可 batch 修（Ω1: 只信实测 — 读 ETL 源码 + 读 model output 量级）。

### AI 治理
- **C-021**: AI 自己写烟测测自己 → 自洽性掩盖正确性。审计独立于作者（Ω5）
- **C-022**: 接收架构师指令即执行 → 188GB 数据丢失。指令 ≠ 授权
- **C-023**: 不读历史经验就写代码 → 重蹈覆辙。新代码走 /dev-cycle
- **C-068**: **归档指令必须逐字对比原文，不可仅凭标题/日期判重复**。V2 directive（POST-MORTEM）含全新 §1 波动率幻觉诊断 + Mandate B.3 窗口隔离 + Crucible 测试标准，但 Claude 只看到日期相同就报"已摄取"，差点丢失 INS-070。判重复 = 读 diff，不是读标题（Ω1: 只信实测——读文件内容，不信文件名推断）

---

## 新经验登记规则

1. 确定违反了哪条 Ω 公理
2. 如果是新的具体失败模式 → 在案例库追加（编号递增，≤ 2 行）
3. 如果涉及操作方法 → 更新操作手册，优先编码进 wrapper 脚本（Ω4）
4. 如果现有 Ω 公理无法覆盖 → **先尝试泛化已有公理**，实在不行再新增（≤ 8 条）
5. **不要同时写入多个文件** — OMEGA_LESSONS.md 是唯一入口
