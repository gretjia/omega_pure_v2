## WHY Chain

1. Phase 11c 切换 Loss (Softmax → Huber) 但未更改 output_dir
2. train.py --resume 逻辑在 output_dir 发现旧 checkpoint
3. 旧 checkpoint 的 epoch counter 已达 max_epochs
4. 训练循环判断"已完成"，跳过所有训练
5. 新 Loss 代码零执行，job 报告假成功

## 为什么现有教训没拦住

C-020 已记录"不同 HPO 复用同一 checkpoint 目录 → 架构不兼容崩溃"。但 C-020 的症状是 **崩溃**（state_dict shape mismatch），容易被发现。

C-044 的陷阱更隐蔽: Loss 切换不改变模型架构（state_dict 完全兼容），所以 load_state_dict 成功。区别仅在 optimizer state 和 epoch counter——这些是**语义不兼容**而非**结构不兼容**。

C-020 教训被理解为"架构不同才需要新目录"，而 C-044 证明: **任何训练语义变更**（Loss、超参、目标函数）都需要新目录，即使模型架构完全相同。

## 模式泛化

**Checkpoint 是完整训练状态的快照，不仅是模型权重**。它包含:
- model state_dict (结构兼容性)
- optimizer state (动量、学习率 schedule)
- epoch counter (进度语义)
- best_metric (评估基准)

改变 Loss/超参等于开始新实验，但 checkpoint 不知道实验语义已变。resume 逻辑假设"同目录 = 同实验"，这个假设在任何实验变更时都会被违反。

泛化规则: **output_dir 是实验的唯一标识符**。任何改变实验语义的操作（Loss、超参、数据、评估方式）都必须使用新的 output_dir。格式建议: `phase{N}_{loss}_{version}`。
