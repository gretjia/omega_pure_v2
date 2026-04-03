## 背景

Phase 11c 将 Loss 从 Softmax Portfolio Loss 切换为 Pointwise Huber (delta=50) + MDL (lambda_s=1e-3)。这是一次范式切换（C-054 原子事件）。新的 train.py 代码已提交到 git (89b4ebf)，Docker 已重建。

## 执行序列

1. Phase 11b 训练完成，checkpoint 保存在:
   ```
   gs://omega-pure-v2/checkpoints/phase11/best_model.pt
   → 包含 Softmax Portfolio Loss 时代的 optimizer state + epoch counter
   ```

2. Phase 11c 使用新 Loss (Pointwise Huber) 提交训练 job:
   ```
   --output_dir gs://omega-pure-v2/checkpoints/phase11/
   --resume
   ```
   output_dir 未更改（仍为 phase11/），与 Phase 11b 相同。

3. train.py 启动，发现 best_model.pt 存在:
   ```
   Resuming from checkpoint: epoch=20, best_metric=0.210
   ```

4. 由于 checkpoint 记录 epoch=20 已达 max_epochs，训练循环判断完成:
   ```
   Training complete. Best metric: 0.210 (from checkpoint)
   ```

5. 新 Loss 代码（Pointwise Huber）从未被执行。Job 报告"成功"——实际是加载旧 checkpoint 的假完成。

6. 用户检查日志看到 "Training complete"，误以为新 Loss 已训练完成。直到手动检查 checkpoint 时间戳才发现 best_model.pt 未更新。

## 环境

- Vertex AI Custom Job, n1-standard-8 + T4 GPU
- Docker image: phase11-v3 (含新 Huber Loss 代码)
- GCS checkpoint 目录: 与 Phase 11b 共享
- train.py --resume 为 Spot VM 设计的自动恢复逻辑
