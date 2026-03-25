# Phase 4 HPO Pre-Flight Checklist

从 Phase 3 的 15 次迭代 (v1-v15) 中提炼的强制预检清单。
每一条都对应一次真实的失败。不跳过任何一条。

---

## Phase 3 苦涩教训 → Phase 4 防护措施

| # | Phase 3 失败 | 根因 | Phase 4 防护 | 状态 |
|---|-------------|------|-------------|------|
| 1 | v1: PyTorch 镜像 404 | `pytorch-gpu.2-4` 不存在 | 使用 `2-2.py310` (v15 验证过) | ✅ 已固化到脚本 |
| 2 | v2: GradScaler API 错误 | PyTorch 2.2 无 `torch.amp.GradScaler` | 使用 `torch.cuda.amp.GradScaler` | ✅ train.py 已修复 |
| 3 | v3: AMP fp16 溢出 | 原始价格 ~5M > fp16 max 65504 | Financial Relativity Transform 压到 [-30,30] | ✅ train.py 已内置 |
| 4 | v4: 空 shard 崩溃 | SSH pipe 上传产生 0-byte 文件 | `warn_and_continue` 全链路 handler | ✅ train.py 已内置 |
| 5 | v5: 多 worker 崩溃 | gcsfuse + multi-worker → tarfile.ReadError | `num_workers=0` | ✅ 脚本中固定 |
| 6 | v7: 梯度爆炸 NaN | 未归一化的原始特征 | Financial Relativity Transform + LayerNorm | ✅ train.py 已内置 |
| 7 | v8-v10: FVU=1.0 不降 | 特征未正确归一化 / Target 未归一化 | Z-score + Huber loss | ✅ train.py 已内置 |
| 8 | v9: WebDataset API 不兼容 | `split_by_worker` 不存在于 1.0.2 | 已移除 | ✅ |
| 9 | CPU 烟测 ≠ GPU 训练 | 精度/版本/存储后端全不同 | **强制 Vertex AI 烟测** (phase4_smoke_test.sh) | ⚠️ 必须先跑 |
| 10 | gcsfuse 不是真文件系统 | batch stat 假死 + 并发读损坏 | 不做 getsize, num_workers=0 | ✅ |

## 启动前检查清单

- [ ] **Step 0: 烟测 (MANDATORY)**
  ```bash
  bash gcp/phase4_smoke_test.sh
  # 等待 SUCCEEDED, 检查日志无 NaN, loss 下降, SPOT 调度成功
  ```

- [ ] **Step 1: 确认 Preemptible L4 GPU 配额**
  ```
  Vertex AI Training Preemptible L4: 200 (approved 2026-03-24)
  需要: 20 (parallel_trial_count)  ✅
  ```

- [ ] **Step 2: 确认 GCS 数据完整性**
  ```bash
  gsutil ls gs://omega-pure-data/wds_shards_v3_full/ | wc -l
  # 应为 1992 shards
  ```

- [ ] **Step 3: 确认脚本已上传**
  ```bash
  gsutil ls gs://omega-pure-data/scripts/v4/
  # 应有: train.py, omega_epiplexity_plus_core.py, omega_webdataset_loader.py
  ```

- [ ] **Step 4: 确认 budget 授权**
  - SPOT 定价: 100 trials × ~2h × $0.20/hr ≈ $40 + retries ≈ **$60-130**
  - Wall-clock: ~10h

- [ ] **Step 5: 启动 HPO**
  ```bash
  bash gcp/submit_phase4_hpo.sh
  ```

## OOM 风险评估

高风险组合: coarse_graining=1 + hidden_dim=256 + window_size_t=32
- 全分辨率 160 步 × 10 空间 × 256 hidden, 注意力窗口 32×10=320 tokens
- L4 (24GB) 在 batch=128 时应足够

极端组合 OOM 时:
- train.py 捕获 `torch.cuda.OutOfMemoryError`
- 报告 FVU=999.0 (Vizier 学习避开该区域)
- `sys.exit(0)` 防止 Spot VM 无限重启烧钱

## Spot VM 抢占保护

- SIGTERM handler: 30 秒内保存 emergency checkpoint 到 GCS
- `restartJobOnWorkerRestart: true`: Vertex AI 自动重启被抢占的 trial
- Auto-resume: train.py 启动时自动检测并加载 checkpoint（无需 --resume）
- 最坏情况: 丢失当前 epoch 进度（~30 min），从上一个 epoch checkpoint 恢复
