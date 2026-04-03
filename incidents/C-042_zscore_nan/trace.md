## 背景

Phase 10 Softmax Portfolio Loss 的 P0 Crucible Test 揭示 Logit Inflation（22.9x Casino Exploit）。Phase 11a "Variance Straitjacket" 方案尝试用 Z-score 标准化 + Temperature=0.1 + lambda_s=1e-7 约束模型输出方差，防止 logit 膨胀。

Z-score 标准化: `z = (x - mean(x)) / std(x)`，将 batch 输出强制为均值 0、方差 1。

## 执行序列

1. Phase 11a 训练启动，配置:
   ```
   Loss: Softmax Portfolio + Z-score normalization
   Temperature: 0.1 (gradient amplification 10x)
   lambda_s: 1e-7
   FP32 mode (no AMP)
   ```

2. Epoch 1-4: 训练看似正常，loss 下降:
   ```
   E1: loss=8.42, S_T=0.003
   E2: loss=7.91, S_T=0.005
   E3: loss=7.55, S_T=0.012
   E4: loss=7.28, S_T=0.089   ← S_T 开始加速膨胀
   ```

3. Epoch 5: 全部 NaN:
   ```
   E5: loss=NaN, S_T=NaN, grad_norm=NaN
   All subsequent epochs: NaN
   ```

4. 数学诊断 — Pythagorean Drift 机制:
   ```
   Z-score: z = (Wx - mean(Wx)) / std(Wx)
   
   ∂z/∂W 与 W 正交（Z-score 是仿射不变的，缩放 W 不改变 z）
   → 梯度 ∂L/∂W 始终正交于 W
   → W 的更新方向始终垂直于 W 本身
   → ||W||² 单调递增（勾股定理: ||W + ΔW||² = ||W||² + ||ΔW||²）
   → S_T ∝ ||W||² 指数膨胀
   → 5 个 epoch 后 S_T 溢出 → NaN
   ```

5. 关键洞察: Z-score 标准化消除了 W 的"刹车"能力——无论 W 多大，输出永远是均值 0 方差 1，所以 loss landscape 对 ||W|| 完全平坦，W 只能无限膨胀。

## 环境

- Vertex AI Custom Job, L4 GPU
- Phase 11a Variance Straitjacket 配置
- FP32 模式（排除 AMP 数值问题）
- 训练数据: 188 shards WebDataset, 556GB
