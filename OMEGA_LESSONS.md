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

### AI 治理
- **C-021**: AI 自己写烟测测自己 → 自洽性掩盖正确性。审计独立于作者（Ω5）
- **C-022**: 接收架构师指令即执行 → 188GB 数据丢失。指令 ≠ 授权
- **C-023**: 不读历史经验就写代码 → 重蹈覆辙。新代码走 /dev-cycle

---

## 新经验登记规则

1. 确定违反了哪条 Ω 公理
2. 如果是新的具体失败模式 → 在案例库追加（编号递增，≤ 2 行）
3. 如果涉及操作方法 → 更新操作手册，优先编码进 wrapper 脚本（Ω4）
4. 如果现有 Ω 公理无法覆盖 → **先尝试泛化已有公理**，实在不行再新增（≤ 8 条）
5. **不要同时写入多个文件** — OMEGA_LESSONS.md 是唯一入口
