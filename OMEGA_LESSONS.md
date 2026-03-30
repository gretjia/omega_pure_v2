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
