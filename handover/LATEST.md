# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-26 — **STATUS: Phase 4 HPO v3 运行中 (Spot L4, 100 trials, 等待资源分配)**

## Current State
- **Phase 3 完成**: v15 全量训练 10 epochs, Best FVU=0.9997 (信号存在但微弱)
- **Phase 4 HPO v3 运行中**: Job `5240027896902320128`, 20 trials REQUESTED (等 Spot L4)
  - v1 FAILED: SIGTERM 报告 inf → Vizier 拒绝
  - v2 FAILED: v1 旧 checkpoint 架构不兼容 + 同一 inf 问题
  - v3 修复: step 级 checkpoint + batch FVU 追踪 + 兼容性检查 + 新 output dir
- **架构师指令已摄取**: 2 条 (MDL 断头台 + A 股长周期重构)
- **Gemini 外部审计已完成**: 3 CRITICAL + 1 HIGH 全部修复

## Changes This Session
- `638e6b7` docs: Phase 3 v15 全训练报告 (handover/PHASE3_V15_TRAINING_REPORT.md)
- `a753c24` feat: Phase 4 HPO — A-Share Swing Tracker + Spot VM + Gemini 审计修复
  - 14 文件, 801 行新增
  - train.py: SIGTERM handler, OOM handler, MDL-aware early stop, auto-resume
  - gcp/phase4_hpo_config.yaml: 完整 Vertex AI HPO 配置 (SPOT 调度)
  - 2 条架构师指令归档 + 3 个 insights (INS-012/013/014)
  - current_spec.yaml 更新: Phase 4 搜索空间
- `6eeaa0a` fix: SIGTERM handler inf→999.0 (v1 失败后紧急修复)
- `26ea9b5` feat: Spot VM resilience v3 — step 级 checkpoint + mid-epoch resume
  - --ckpt_every_n_steps=500 (~3 min intervals)
  - load_checkpoint 兼容性检查 (try/except)
  - batch FVU 追踪 for SIGTERM reporting
  - 新 output dir: phase4_v3 (避免 v1/v2 残留冲突)
- handover/GCP_PRICING_REFERENCE.md: 实际 Vertex AI 定价 + CUD 分析

## Key Decisions
- **Phase 4 搜索空间重构**: coarse_graining_factor 回归 [1,4,16,64] (A 股长周期建仓)
- **hidden_dim 缩减**: [128,256] (移除 384, OOM 安全)
- **window_size_s 固定=10**: 全盘口深度
- **Spot VM 而非 Standard**: 省 ~58%, 但需要完整的断点续做机制
- **Flex CUD 分析**: $0.07/h 承诺不覆盖 GPU, 对 HPO 无影响

## Next Steps
1. **等待 HPO v3 trials 获得 Spot L4 资源并完成** (周末应更容易)
2. 如果 Spot 仍持续失败 → 切换 STANDARD 模式 ($222 预算)
3. HPO 完成后 → 分析最佳超参组合 → Phase 5 (防过拟合 + 全量训练)
4. 考虑长期: Vertex AI resource-based CUD for L4 GPU (可省 55%)

## Warnings
- **HPO v1/v2 旧 checkpoint 仍在 GCS**: gs://omega-pure-data/checkpoints/phase4/ (无害但浪费空间)
- **Spot L4 us-central1 白天极不稳定**: 周一~周五 trial 会被频繁抢占, 周末/深夜最佳
- **v3 output dir 是 phase4_v3**: 与 v1/v2 的 phase4 隔离, 不会冲突
- **Flex CUD 不覆盖 GPU**: 不要期望 CUD 能降低训练成本
- **Gemini 审计的 "$@" 修复至关重要**: HPO 参数传递依赖 bash -c + "$@" + "_" 占位符

## Bitter Lessons — Phase 4 HPO (v1→v3, 3 次提交失败)

### Lesson 1: Spot VM + Epoch 级 checkpoint = 零进度保留
Spot L4 在 us-central1 白天 ~10 分钟被抢占一次。每个 epoch 需 30 分钟。20 个 trial 在 Epoch 0 中途被全部抢占，无有效 checkpoint。**必须用 step 级 checkpoint (每 500 步 / ~3 min)**。

### Lesson 2: float("inf") 报告给 Vizier = 全盘判死
best_fvu 初始值 float("inf")，validation 未执行就被抢占 → SIGTERM 报告 inf → Vizier API 拒绝 ("Invalid objective value: inf") → 全部 INFEASIBLE。**任何报告给 Vizier 的 metric 必须是有限实数**。

### Lesson 3: 不同 HPO job 复用 checkpoint 目录 = 架构崩溃
v2 的 trial_12 (hidden=128) 加载了 v1 trial_12 (hidden=256) 的 state_dict → shape mismatch → crash。**每次 HPO 提交必须用唯一 output base dir**。

### Lesson 4: Gemini 审计在提交前是必须的
Gemini 发现了 3 个 CRITICAL bug (bash -c 参数吞噬、int("128.0") ValueError、SIGTERM exit code)。这些在人工 review 中几乎不可能发现。**复杂部署前必须经过独立外部审计**。

### Lesson 5: Vertex AI 的 bash -c 与 HPO 参数传递不兼容
bash -c "cmd" 之后的追加参数变成位置变量 $0/$1，不会传给 cmd 内部的 python。**必须用 "$@" + "_" 占位符**。

### Pre-HPO Gate (Phase 4 教训清单)
未来提交 HPO 前必须检查：
- [ ] checkpoint 频率适配 Spot 抢占周期 (step 级, 非 epoch 级)
- [ ] SIGTERM handler 报告有限实数 metric (不是 inf/nan)
- [ ] output dir 唯一 (含版本号或 job ID)
- [ ] argparse int 参数兼容 float 字符串 ("128.0")
- [ ] bash -c 使用 "$@" + "_" 转发 HPO 参数
- [ ] load_checkpoint 有 try/except 处理不兼容 state_dict
- [ ] 在目标环境 (Spot VM) 烟测通过后再提交 HPO

## Remote Node Status
本次会话未涉及远程节点 (linux1/windows1)

## Architect Insights (本次会话)
- INS-012 MDL 断头台: λ_s=0.001 对微弱 Alpha 构成致命正则化过当 → 搜索 [1e-6, 1e-4]
- INS-013 Phase 4 HPO 搜索空间 v1: 六维搜索 (被 INS-014 取代)
- INS-014 时间膨胀器回归: coarse_graining_factor [1,4,16,64] 作为 P0 参数, 捕捉 A 股机构长周期建仓
