## WHY Chain

1. HPO config 模板的 `--output_dir` 是固定值（未参数化 trial ID）
2. train.py 的 `--resume` 逻辑在 output_dir 下发现 checkpoint 就自动加载
3. 不同 trial 的 hidden_dim/num_heads 不同 → state_dict shape 不兼容
4. load_state_dict 报 size mismatch → trial 崩溃
5. Vizier 大量 INFEASIBLE → HPO 搜索退化

**根因**: Spot VM resume 机制与 HPO 多 trial 机制冲突——resume 假设 "同目录 = 同架构"，HPO 违反此假设。

## 模式泛化

**Checkpoint 目录 = 隐式架构绑定**。任何改变模型架构的操作（HPO trial、Loss 切换、超参修改）都必须使用唯一的 output_dir，否则 resume 逻辑会加载不兼容的 state_dict。

这是"隐式状态泄漏"模式：一个子系统（Spot resume）的状态假设被另一个子系统（HPO）违反，错误不在任一子系统内部，而在交互边界。
