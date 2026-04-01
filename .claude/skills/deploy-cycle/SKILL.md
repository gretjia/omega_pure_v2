---
name: deploy-cycle
description: 部署周期 — Pre-flight/Axiom/NodeHealth/Deploy/Verify/Document 六阶段自动编排
user-invocable: true
---

# Deploy Cycle（部署周期）

自动编排从预检到部署完成的完整部署周期。

## 输入

用户提供目标节点，例如：
- `/deploy-cycle linux1`
- `/deploy-cycle windows1`

如果没有提供目标，询问用户部署到哪个节点。

节点别名映射：
- `linux1` → `linux1-lx`
- `windows1` → `windows1-w1`

## 部署类型

**在开始之前，确认部署类型：**

| 类型 | 目标 | 工具链 | 流程 |
|------|------|--------|------|
| **GCP 训练** | Vertex AI Custom Job | safe_build_and_canary.sh → safe_submit.sh | 走 Stage 0 I/O 决策 → Docker build → Canary → Submit |
| **GCP 推理** | Vertex AI Custom Job | gen_inference_config.sh → safe_submit.sh | Pipe 模式, 100GB disk |
| **本地节点** | linux1 / windows1 | SCP + systemd-run | 走 Stage 1-6 |

## 八阶段流程（含 Stage 0 I/O 决策）

### Stage 0: I/O + 成本决策（GCP 部署必须执行）

**I/O 策略决策树（C-048, Gemini 审计固化）：**

```
数据读取模式？
├── 单次遍历 (推理) → Pipe 模式
│   - `pipe:gcloud storage cat gs://...`
│   - 磁盘: 100GB pd-ssd (仅 OS+code)
│   - 成本最低, Phase 7 实测 466 shards/h
│   - 同 region GCS→Vertex AI 网络 $0
│
├── 多次遍历 (训练, N epochs) → pd-ssd Staging
│   - 一次性 `gcloud storage cp` 到 /tmp/shards
│   - 磁盘: data × 2.5 安全余量 (556GB → 1300GB pd-ssd)
│   - C-026: N epoch × data_size TB 重复读, pipe 会 CPU 瓶颈
│   - C-041: Vertex AI 无法 mount Local NVMe SSD
│   - 吞吐: 0.48 MB/s/GB × 容量 (1300GB = 624 MB/s)
│
└── 多次遍历 + resampled=True → 绝对禁止 FUSE file-cache
    - resampled=True = 随机采样 → Cache Thrashing
    - tarfile.ReadError + multi-worker 冲突
```

**Spot vs On-demand 决策树：**

```
有 checkpoint 续传机制？
├── 是 (训练: step-level ckpt + SIGTERM handler) → Spot VM
│   - 价格: ~70% 折扣 ($0.19/h vs $0.73/h for n1+T4)
│   - C-018: 必须 500 步 step-level checkpoint
│   - C-047: checkpoint 必须先写本地再 copy 到 GCS FUSE
│
└── 否 (推理: 无断点续传) → On-demand
    - 被抢占 = 从头开始
    - 短推理 (<1h) 可冒险用 Spot
```

**机型选择参考：**

| 场景 | 推荐机型 | 理由 |
|------|----------|------|
| 训练 (<100K 参数) | n1-standard-8 + T4 (Spot) | 性价比最高 |
| 推理 (大 batch) | g2-standard-8 + L4 | 更大显存 |
| HPO (多 trial) | a2-highgpu-1g + A100 (Spot) | 并行效率 |

**Checkpoint 安全规则（C-047, Gemini 审计固化）：**
- `save_checkpoint` 必须先写本地 `/tmp` → 再 copy 到 GCS FUSE path
- SIGTERM handler 必须调用 `os.sync()` 强制 FUSE 刷盘
- 换 Loss/超参后必须用新 output_dir（C-044）

**成本量化（Ω2 强制）：**
必须列出预估成本表：
```
| 项目 | 数量 | 单价 | 总计 |
|------|------|------|------|
| GPU (Spot) | Xh | $Y/h | $Z |
| pd-ssd | XGB × Yh | $0.17/GB/月 | $Z |
| GCS 出口 | 同 region | $0 | $0 |
| 总计 | | | $Z |
```

### Stage 1: PRE-FLIGHT

调用 `/pre-flight` skill，对目标节点执行 9 项预检：
1. SSH 连通性
2. 磁盘空间 > 20%
3. 内存 < 80%
4. 无重复进程
5. Python 依赖
6. 数据路径存在
7. systemd slice 状态
8. OOM 保护
9. 确认正确节点

输出：
```
=== STAGE 1: PRE-FLIGHT ===
Target: <node>
Verdict: GO / NO-GO
```

**如果 NO-GO → 停止并报告，等待用户修复后重试**

### Stage 2: AXIOM AUDIT

调用 `/axiom-audit` skill，运行完整公理检查：
```bash
python3 omega_axioms.py --verbose
```

输出：
```
=== STAGE 2: AXIOM AUDIT ===
Verdict: PASS / FAIL
```

**如果 FAIL → 停止，不允许部署有公理违规的代码**

### Stage 3: NODE HEALTH

调用 `/node-health-check` skill，检查集群健康：

输出：
```
=== STAGE 3: NODE HEALTH ===
<集群健康报告>
```

### Stage 4: DEPLOY

**此阶段需要用户明确确认后才执行。**

1. 确认要部署的文件列表
2. 用户确认后，SCP 文件到目标节点：
   ```bash
   scp <files> <target>:<deploy_path>/
   ```
3. 如果需要启动进程，使用 systemd-run：
   ```bash
   ssh <target> systemd-run --slice=heavy-workload.slice --scope python3 <script>
   ```

输出：
```
=== STAGE 4: DEPLOY ===
Files deployed:
  - <file1> → <target>:<path>
Status: DEPLOYED
```

### Stage 4.5: GEMINI DEPLOY AUDIT（GCP 部署必须执行）

**对最终 Job Config YAML 调用 Gemini API 进行独立审计（Ω5: 生产者≠验证者）。**

审计维度：
1. 磁盘配置 vs 数据量是否匹配
2. I/O 策略是否与 Stage 0 决策一致
3. 超参是否与 current_spec.yaml 对齐
4. Spot + checkpoint 配置是否安全
5. 成本估算是否合理
6. 是否遗漏 GCP 最佳实践

```bash
source .env && curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent?key=${GEMINI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @/tmp/gemini_deploy_audit.json
```

输出：
```
=== STAGE 4.5: GEMINI DEPLOY AUDIT ===
Verdict: PASS / WARN / FAIL
<审计详情>
```

**如果 FAIL → 修复 config 后重新审计**

### Stage 5: VERIFY

部署后验证：
1. 确认进程在目标节点运行：
   ```bash
   ssh <target> ps aux | grep python
   ```
2. 检查初始日志输出（前 20 行）
3. 确认无立即错误

输出：
```
=== STAGE 5: VERIFY ===
Process: RUNNING (PID: <pid>)
Initial output: <summary>
Verdict: HEALTHY / ERROR
```

### Stage 6: DOCUMENT

1. 更新 `handover/LATEST.md` 记录本次部署：
   - 时间戳
   - 目标节点
   - 部署的文件
   - 当前状态
2. 提示用户是否要 commit 这些变更

输出：
```
=== DEPLOY CYCLE COMPLETE ===

Target: <node>
Stages: PRE-FLIGHT ✓ → AXIOM ✓ → HEALTH ✓ → DEPLOY ✓ → VERIFY ✓ → DOCUMENT ✓

Deployed files:
  - <file1>

Process status: RUNNING

handover/LATEST.md updated.
Ready to commit? (yes/no)
```

## 安全约束

- Pre-flight 必须全部 PASS 才能继续
- 公理违规时绝不部署
- 部署操作（SCP + systemd-run）需要用户明确确认
- 使用 `systemd-run --slice=heavy-workload.slice` 启动重计算
- 不可同时运行多个 ETL 实例（单实例锁）
- 远程推送（git push, scp 到生产节点）需要用户确认
