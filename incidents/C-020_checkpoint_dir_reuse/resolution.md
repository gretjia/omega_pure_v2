## 修复

HPO 配置模板中 `--output_dir` 改为包含 trial ID:
```
--output_dir gs://omega-pure-v2/checkpoints/phase{N}_hpo/trial_${TRIAL_ID}/
```

每个 trial 使用独立目录，resume 逻辑只在同 trial 被 Spot 抢占时生效。

## 验证

- 重新启动 HPO，确认不同 trial 写入独立目录
- 故意用不同 hidden_dim 的 trial 验证不再交叉加载
- Vizier 正常收到有效 objective 值

## 执法

none — doc_only。C-020 被记录到 OMEGA_LESSONS.md 作为经验教训。
后续 C-044 和 C-061 证明 doc_only 执法不足以防止同类错误复发。
