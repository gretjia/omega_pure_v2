## 背景

Phase 10 训练完成后，需要部署推理 job 到 Vertex AI 生成 backtest 数据。C-028 已记录 pd-ssd 吞吐陷阱（0.48 MB/s per GB），OMEGA_LESSONS.md 中明确写入"训练数据必须用 Local SSD 或 FUSE v2 file-cache"。

但推理 job 配置由 gen_inference_config.sh 模板生成，该模板在 C-028 之前编写。

## 执行序列

1. 第一次推理 job 配置手写，使用 pd-ssd:
   ```yaml
   bootDiskType: pd-ssd
   bootDiskSizeGb: 200
   ```

2. 556GB shard 数据无法装入 200GB 磁盘:
   ```
   ERROR: Disk space exhausted during data staging
   ```

3. 修改为 bootDiskSizeGb=500，重新提交:
   ```yaml
   bootDiskType: pd-ssd    # 仍然是 pd-ssd — C-028 教训未被应用
   bootDiskSizeGb: 500
   ```

4. 推理 I/O 慢（500GB × 0.48 = 240 MB/s），但推理是单 pass，勉强可接受。问题在于这是第二次犯同样的错误。

5. 后续又一次推理 job 配置再次使用 pd-ssd + 200GB:
   ```
   gen_inference_config.sh 模板硬编码 bootDiskSizeGb=200
   ```

6. 发现 gen_config 模板本身就是错误源头——每次生成的配置都携带 pd-ssd + 200GB 的默认值。

## 环境

- Vertex AI Custom Job, 推理模式
- gen_inference_config.sh: 配置生成脚本（Phase 9 时代编写）
- 556GB WebDataset shards 需要 staging
- C-028 已记录到 OMEGA_LESSONS.md（但仅 doc_only 执法）
