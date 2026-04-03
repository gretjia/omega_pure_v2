## 背景

Phase 4/6 HPO (Hyperparameter Optimization) 使用 Vizier 搜索 7 维超参空间。每个 trial 启动一个 Vertex AI training job，bash -c 传入不同超参组合（learning_rate, hidden_dim, num_heads, etc.）。

## 执行序列

1. HPO 脚本启动 100 trials，所有 trial 的 `--output_dir` 指向同一个 GCS 路径:
   ```
   gs://omega-pure-v2/checkpoints/phase4_hpo/
   ```

2. Trial 1 (hidden_dim=64, num_heads=4) 正常训练，保存 checkpoint:
   ```
   gs://omega-pure-v2/checkpoints/phase4_hpo/best_model.pt
   → state_dict keys: encoder.layer.weight [64, 70], attention.heads [4, 64, 64]
   ```

3. Trial 2 (hidden_dim=128, num_heads=8) 启动，train.py 发现 output_dir 中已存在 checkpoint:
   ```
   Loading checkpoint from gs://omega-pure-v2/checkpoints/phase4_hpo/best_model.pt
   ```

4. `model.load_state_dict(checkpoint)` 崩溃:
   ```
   RuntimeError: Error(s) in loading state_dict:
     size mismatch for encoder.layer.weight: copying a param with shape [64, 70] from checkpoint,
     where the shape in current model is [128, 70]
   ```

5. 所有后续 trial 若与 Trial 1 架构不同，均在加载阶段崩溃。Vizier 收到连续 INFEASIBLE，搜索空间被错误收缩。

## 环境

- Vertex AI Custom Job, L4 GPU
- Spot VM, train.py 含 `--resume` 自动恢复逻辑（为 Spot 抢占设计）
- 100 trials parallel=8, 共享 GCS bucket
- bash -c 传入超参，但 output_dir 为模板硬编码值
