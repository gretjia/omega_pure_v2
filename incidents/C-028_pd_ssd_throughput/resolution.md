## 修复

1. Phase 10 配置切换到 FUSE v2 + file-cache 方案 (bbad361):
   - GCS FUSE v2 自动缓存到 Local SSD
   - Epoch 1 网络读取，Epoch 2+ 本地 NVMe 速度 (4.8 GB/s)
   - 无需手动 staging 脚本

2. 建立 I/O 策略决策树 (C-048):
   - 推理(单 pass) → pipe 模式 (100GB disk)
   - 训练(多 epoch) → pd-ssd 大容量 staging (1300GB)
   - FUSE file-cache + resampled=True → cache thrashing 灾难（禁止）

3. OMEGA_LESSONS.md 记录 pd-ssd 公式: 0.48 MB/s per GB

## 验证

- Phase 10 训练确认 FUSE v2 file-cache 生效:
  - Epoch 1: 网络速度 (~600 MB/s)
  - Epoch 2+: NVMe 速度 (~4.8 GB/s)
  - Validation 时间大幅缩短

## 执法

executable — `.claude/hooks/lesson-enforcer.sh` PreToolUse hook (d3f5352):
- 拦截任何 YAML 文件中的 pd-ssd 配置写入
- 交互式确认: 训练 job 不允许使用 pd-ssd（除非明确 staging 方案）
- 在 Phase 11b (d3f5352) 中随 lesson-enforcer.sh 一起部署
