## 修复

1. 使用新 output_dir 重新提交训练:
   ```
   --output_dir gs://omega-pure-v2/checkpoints/phase11c_huber_v1/
   ```

2. OMEGA_LESSONS.md 记录泛化规则: 换 Loss/超参后必须用新 output_dir（如 v1 -> v2）

## 验证

- 新 output_dir 无旧 checkpoint，训练从 epoch 0 正常开始
- 确认 Huber Loss 代码被执行（日志显示 huber_delta=50 生效）
- 后续 C-061 复发证明需要更强执法

## 执法

none — doc_only。写入 OMEGA_LESSONS.md。

C-061（Phase 12 烟测）再次复发同类问题，证明 doc_only 执法对此模式无效。需要在 train.py 中加入 checkpoint 元数据校验（记录 loss_type + 关键超参 hash，resume 时比对），或在 safe_submit.sh 中强制检查 output_dir 唯一性。
