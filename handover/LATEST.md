# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-01 — **STATUS: Phase 11c Pointwise Spear 训练中 (n1+T4 Spot), E3/20 稳态收敛**

## Current State
- **Phase 11c 训练中**: Job 5314881274131775488 (n1-standard-8 + T4 Spot, pd-ssd 1300GB staging)
  - Docker: omega-tib:phase11-v3 (canary PASSED)
  - Loss: Pointwise Huber(δ=50) + MDL(λ_s=1e-3) — 彻底废除 Softmax/Z-score (INS-049/051)
  - Output: gs://omega-pure-data/checkpoints/phase11c_pointwise_v1/
  - Cron 监控: 15min (ID 64f62dec), 初期 5min 确认无 bug 后降频
  - 进度: Epoch 3/20, ~1.5h elapsed, 预估总 ~7-8h
- **Epoch 0-2 Val 结果**:
  - E0: Val PfRet=6.94, Std_yhat=290 BP (物理锚定成功!)
  - E1: Val PfRet=7.23★(best), Std_yhat=1234 BP (λ_s 未生效期膨胀)
  - E2: Val PfRet=7.10, Std_yhat=489 BP (λ_s 生效, 压缩 60%)
- **Phase 11b 已废弃**: Softmax = 宏观 Beta 走私 (INS-049), Logit Inflation 6956 BP
- **Phase 11a 已废弃**: NaN 崩溃 (勾股漂移 INS-046)

## Changes This Session (未提交)
- `train.py`: compute_spear_loss → Pointwise Huber(δ=50), checkpoint C-047 本地 staging + os.sync()
- `architect/current_spec.yaml`: loss→Huber, λ_s→1e-3, 删除 temperature/variance_lock, HPO 5 params
- `OMEGA_LESSONS.md`: C-045(跨期 Batch 毒药), C-046(L1 脑死亡), C-047(FUSE checkpoint), C-048(I/O 决策树)
- `deploy-cycle SKILL.md`: Stage 0 I/O 决策树 + Stage 4.5 Gemini Deploy Audit
- `gcp/safe_submit.sh`: C-028 检查从硬阻止改为交互确认 (C-041 训练 staging 兼容)
- `gcp/phase11c_train_config.yaml`: 新配置 (Huber, λ_s=1e-3, --no_amp, --resume)
- `architect/directives/2026-04-01_phase11c_pointwise_spear.md`: 完整归档
- `architect/insights/INS-049,050,051`: 3 条新洞察

## Key Decisions
1. **废除所有跨 Batch 归一化**: Softmax(dim=0)/Z-score/Pearson 在乱序 WebDataset 上制造宏观 Beta 走私 (INS-049)
2. **L1 语义翻转**: z_sparsity≈0 = 脑死亡(非最高压缩), 非零 = 真智能. Gating 方向必须反转 (INS-050)
3. **Pointwise Huber(δ=50)**: 零跨 Batch 依赖, 绝对 BP 尺度锚定, δ=50 截断极端梯度 (INS-051)
4. **Checkpoint C-047**: 先写本地 /tmp → shutil.copy2 到 FUSE → os.sync(), 防 Spot SIGTERM 损坏
5. **deploy-cycle 升级**: I/O 决策树(C-048) + Gemini Deploy Audit + 成本量化模板

## Next Steps (Phase 11c 完成后)
1. 分析训练曲线: Val PfRet 是否超越 7.23? Std_yhat 是否稳定在 <500 BP?
2. 全量推理 (phase7_inference.py + Phase 11c best.pt)
3. P0 Crucible 回测 (25BP cost), 检查 Asymmetry Ratio
4. 如 λ_s 不够强 (Gemini WARN), 考虑 Phase 11d λ_s=1e-2

## Warnings
- **Phase 11c 是 Spot**: 可能被抢占, --resume + 500 步 checkpoint 自动恢复
- **Val Std_yhat 膨胀趋势**: E0=290→E1=1234→E2=489, λ_s 在压制但需持续观察
- **window_size_s=4 vs spec=10**: Gemini WARN, 继承 Phase 10/11 实践, 非 bug
- **epochs=20 vs spec=15**: 新 Loss 需更多 epoch 观察收敛行为

## Remote Node Status
- linux1: 无活跃任务
- Vertex AI: Job 5314881274131775488 RUNNING (Epoch 3/20)

## Architect Insights (本次会话 — 3 条)
- INS-049: 跨期 Batch 毒药 — 封杀 Batch 维度归一化 → architect/insights/INS-049_cross_temporal_batch_poison.md
- INS-050: L1 脑死亡陷阱 — z_sparsity 语义翻转修正 → architect/insights/INS-050_l1_brain_death_semantic_inversion.md
- INS-051: 点对点建仓之矛 — Pointwise Huber 替代 Softmax → architect/insights/INS-051_pointwise_spear_huber_loss.md

## New Lessons (本次会话 — 4 条)
- C-045: 跨期 Batch 毒药 (Softmax+乱序WebDataset=Beta走私)
- C-046: L1 脑死亡陷阱 (L1≈0=脑死亡, 非零=真智能)
- C-047: FUSE checkpoint 竞态 (Spot SIGTERM+FUSE flush=损坏, 先写本地)
- C-048: I/O 策略决策树 (推理→pipe, 训练→staging, FUSE+resampled=灾难)

## External Audits (本次会话)
- Gemini 数学审计: 5 PASS / 2 WARN (λ_s 量纲, 绝对回归范式)
- Gemini Deploy 审计: 4 PASS / 1 FAIL(已修复 --resume) / 1 WARN(window_size_s)
- Codex Code 审计: 4 PASS / 1 INFO (spec 不一致已修复)

## Machine-Readable State
```yaml
phase: 11c
status: "training_in_progress"
job_id: 5314881274131775488
docker: "omega-tib:phase11-v3"
machine: "n1-standard-8 + T4 Spot"
output_dir: "gs://omega-pure-data/checkpoints/phase11c_pointwise_v1"
loss: "Pointwise Huber(delta=50) + MDL(lambda_s=1e-3)"
params: {hd: 64, wt: 32, ws: 4, lambda_s: 1e-3, batch_size: 256, no_amp: true}
monitor: "cron 15min (ID 64f62dec)"
val_best_pfret: 7.232315
val_std_yhat_trend: [290, 1234, 489]
commits_this_session: 0 (pending)
insights_this_session: [INS-049, INS-050, INS-051]
new_lessons: [C-045, C-046, C-047, C-048]
```
