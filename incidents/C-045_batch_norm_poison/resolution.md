## 修复

Phase 11c (89b4ebf) 彻底重构 Loss:

1. **废除所有 Batch 维度归一化**:
   - 删除 Softmax(dim=0)
   - 删除 Batch Z-score
   - 删除 temperature scaling

2. **Pointwise Huber Loss 替代**:
   ```python
   # 每个样本独立计算 loss，无跨 batch 交互
   loss = F.huber_loss(predictions, targets, delta=huber_delta, reduction='mean')
   ```

3. **Spear Protocol (INS-046/047/048)**:
   - Pointwise loss: 样本间零信息泄漏
   - Per-sample MDL: S_T 独立于 batch composition
   - 评估仍用 Spearman rank (跨 batch)，但只在 validation 阶段

4. **OMEGA_LESSONS.md 绝对禁令**: "绝对禁止 Batch 维度归一化"

## 验证

- Phase 11c 训练: Std_yhat=489 BP (vs C-045 的 6956 BP)
- 十分位拆解: D0/D9 不再按市场环境分层
- Asymmetry ratio 回归合理区间
- Phase 11d 进一步确认 Pointwise 方案的稳定性

## 执法

none — doc_only + 代码结构性防御:
- OMEGA_LESSONS.md 绝对禁令
- train.py 中 compute_spear_loss 函数不含任何 dim=0 操作
- architect/current_spec.yaml loss 定义为 Pointwise Huber（变更需人工确认）
- INS-049 cross-temporal batch poison 归档为架构师洞察

建议未来执法升级: omega_axioms.py 中增加 "no dim=0 normalization" 静态检查。
