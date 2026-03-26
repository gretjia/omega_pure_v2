# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-26 — **STATUS: Phase 4 RECON HPO 运行中 (30 trials STANDARD, Job 5228425850206027776)**

## Current State
- **Phase 3 完成**: v15 全量 10 epochs, Best FVU=0.9997
- **Phase 4 验证 trial PASSED**: 8/8 epochs 完成, Best FVU=1.0003, 无 crash
- **Phase 4 RECON HPO 运行中**: Job `5228425850206027776`, 30 trials, 8 parallel, STANDARD L4
  - 搜索空间: cg=[1,2,4,8], hidden=[128,256], λ_s=[1e-6,1e-4], warmup=[3,4,5], window_t=[8,16,32], lr=[1e-4,1e-3]
  - 预算: ~$67
  - Docker v5 镜像 (预装依赖 + Codex 修复)
  - 预计 ~8h 完成 (5 waves × ~1.5h/trial)

## Changes This Session (15 commits)
- `638e6b7` docs: Phase 3 v15 训练报告
- `a753c24` feat: Phase 4 HPO — A-Share Swing Tracker + Spot VM + Gemini 审计修复 (14 files, 801 lines)
- `6eeaa0a` fix: SIGTERM inf→999.0
- `26ea9b5` feat: Spot VM resilience v3 — step 级 checkpoint + mid-epoch resume
- `959a633` docs: handover + 5 new VIA_NEGATIVA
- `f481807` feat: 自定义 Docker 镜像 + 降低并行数
- `a7a766d` fix: bash entrypoint for CLOUD_ML_TRIAL_ID
- `34e3ca8` fix: Codex 审计 — warmup_epochs _int + best_fvu resume
- `1d825e8` fix: --max_val_steps=200 (validation gcsfuse 瓶颈)
- `1b589ba` feat: Phase 4 recon HPO — 30 trials, cg=[1,2,4,8] (INS-015/016)

## Key Decisions
1. **Spot → STANDARD**: Spot L4 us-central1 周末仍极不稳定 (v1-v4b 全部因抢占失败)。STANDARD 贵但可靠
2. **100 trials → 30+70 分阶段**: 算力凯利公式风控 (INS-015)。30 trials 火力侦察 ($67)，无信号则止损
3. **cg=[1,4,16,64] → [1,2,4,8]**: 保护 Volume-Clock 微观结构 (INS-016)。cg≥16 摧毁 LOB 信号且与 payoff_horizon=20 bars 采样倒挂
4. **自定义 Docker 镜像**: 消除 ~4min pip install 重复开销。v5 镜像含 Codex 修复
5. **--max_val_steps=200**: 解决 validation gcsfuse 单线程读 399 shards 阻塞 110min 问题

## Next Steps
1. **等待 RECON HPO 完成** (~8h, Job 5228425850206027776)
2. 分析 30 trials 结果：
   - 任何 trial FVU < 1.0 → 追加到 100 trials (Vizier 有状态，无缝扩展)
   - 全部 FVU > 1.0 → 反思特征/目标/架构，不盲目追加
3. 如需更长时间视野 → 扩大 macro_window (320/500)，不增大 cg

## Warnings
- **HPO v1/v2/v3/v4b 已全部取消**，残留 checkpoint 在 phase4_v3/ 和 phase4_v4/（可清理）
- **Docker 镜像 v5 嵌入了 train.py**: 代码变更需重建镜像 (Cloud Build ~10min)
- **Cloud Logging 延迟 15-20 min**: 实际进度比日志快，用 GCS checkpoint 时间戳判断
- **Vizier 追加 trials**: 如需从 30 追加到 100，可能需要用 Python SDK（gcloud CLI 不支持修改 max_trial_count）

## Bitter Lessons — 本次会话新增

### Spot VM 对 HPO 是错误选择
us-central1 Spot L4 周末仍极不稳定。20 并行 trial 的惊群效应导致分配即抢占。12+ 小时工程时间只为省 $128。**HPO 需要可靠完成，用 STANDARD。Spot 适合单个长 job (Phase 5)**。

### Validation gcsfuse 阻塞
num_workers=0 + 399 val shards + gcsfuse 单线程 = validation 110+ min/epoch。Phase 3 v15 用了 max_val_steps 但这次验证 trial 忘记设。**必须设 --max_val_steps=200**。

### Docker 镜像内 python3 直接 entrypoint 不展开环境变量
${CLOUD_ML_TRIAL_ID} 需要 bash 展开。python3 直接调用时变量变成字面字符串。**必须用 bash -c + "$@" + "_"**。

## Remote Node Status
本次会话未涉及远程节点 (linux1/windows1)

## Architect Insights (本次会话)
- INS-012 MDL 断头台: λ_s=0.001 致命正则化过当 → 搜索 [1e-6, 1e-4]
- INS-013 Phase 4 HPO 搜索空间 v1 (被 INS-014→016 取代)
- INS-014 时间膨胀器回归 (被 INS-016 取代)
- INS-015 贝叶斯火力侦察 30+70: 算力凯利公式，Vizier 有状态追加
- INS-016 cg 微观结构保护: Volume-Clock 不可二次粗粒化，cg=[1,2,4,8]
