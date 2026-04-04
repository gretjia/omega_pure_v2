## 修复

Phase 11b "Reforged Spear" (d3f5352) 实施四项修复:

1. **Detached Straitjacket**: `std = clamp(std, min=1.0).detach()`
   - `.detach()`: 阻断 std 的反向传播，恢复梯度对 W 的控制力
   - `clamp(min=1.0)`: 防止 std 过小导致除法梯度爆炸

2. **Temperature**: 0.1 → 0.5 (梯度放大从 10x 降到 2x，减缓漂移速度)

3. **lambda_s**: 1e-7 → 2e-5 (匹配 Softmax Loss 量纲，C-043 教训)

4. **数值安全**: FP32 safe room + F.log_softmax + z_core clamp [-20, 20]

## 验证

- Phase 11b 训练 20 epochs 无 NaN
- S_T 保持稳定（不再单调膨胀）
- Std_yhat 在物理合理区间
- Pythagorean drift 机制被 .detach() 彻底阻断（数学证明: ∂L/∂W 不再与 W 正交）

## 执法

none — doc_only。修复直接嵌入 train.py 代码中:
```python
std = predictions.std(dim=0).clamp(min=1.0).detach()
z_pred = (predictions - predictions.mean(dim=0).detach()) / std
```
代码即执法 — `.detach()` 和 `clamp` 是结构性防御，不依赖外部 hook。
