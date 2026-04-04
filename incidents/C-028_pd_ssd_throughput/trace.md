## 背景

Phase 9 训练使用 GCS pipe 模式（pipe:gcloud storage cat）流式读取 556GB WebDataset shards。Gemini I/O 审计发现验证阶段耗时 15 min 远超训练 13 min，诊断为 I/O 瓶颈。Phase 9 v3 (f820d11) 切换到 Fat Node + Local SSD + On-demand 方案解决。

后续 Phase 10 配置回退到 pd-ssd（因 C-041 发现 Vertex AI 容器无法 mount Local NVMe SSD），但未量化 pd-ssd 实际吞吐。

## 执行序列

1. Phase 9 v1 使用 GCS pipe 模式，I/O 严重瓶颈:
   ```
   Epoch validation: 15 min (vs training 13 min)
   Effective throughput: ~600 MB/s (network bound)
   ```

2. Phase 9 v3 切换到 g2-standard-24 + 750GB Local SSD:
   ```
   Stage 556GB to NVMe: ~3 min
   Local I/O: 3-6 GB/s
   Validation: 15min → 1-2min
   ```

3. Phase 10 部署时，发现 Vertex AI 容器 (C-041) 不支持 localSsdSpec:
   ```
   ERROR: Local SSD mount permission denied in Vertex AI container
   ```

4. 回退到 pd-ssd，配置 bootDiskSizeGb=800:
   ```
   GCP pd-ssd throughput formula: 0.48 MB/s per GB provisioned
   800GB × 0.48 = 384 MB/s sequential read
   ```

5. 556GB dataset, 20 epochs = 11.1TB total I/O:
   ```
   11.1TB / 384 MB/s = ~8h pure I/O time (理论值)
   实际: epoch 1 validation 需要全量读取，严重拖慢训练
   ```

6. Gemini 审计推荐 FUSE v2 file-cache（bbad361）: 第一 epoch 缓存到 Local SSD，后续 epoch NVMe 速度 (4.8 GB/s)。

## 环境

- Vertex AI Custom Job
- n1-standard-8 + L4 GPU
- pd-ssd boot disk 800GB（装 OS + 556GB staged data）
- GCP pd-ssd IOPS/throughput 文档: https://cloud.google.com/compute/docs/disks/performance
- 关键公式: Sequential read throughput = min(1200 MB/s, 0.48 × disk_size_GB)
