# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-03 — **STATUS: Living Harness V3 部署完成 + Phase 12 代码就绪, 烟测训练 PASS, 推理断言量纲待修。**

## Current State
- **Living Harness V3 已部署** (详见 [`LIVING_HARNESS.md`](../LIVING_HARNESS.md)):
  - 16 条数据驱动执法规则 (rules/active/*.yaml), rule-engine.sh 动态加载
  - 10 个完整 incident trace (incidents/), 5 组重复模式全覆盖
  - 管线神经系统: chain_of_custody + INS 6-section 质量门禁 + spec draft/final
  - Spec-Code 对齐检查器 (tools/spec_code_alignment.py)
  - 烟测 26/26 passed (tests/test_harness_v3.py)
  - 2 个新 skill: /lesson-to-rule + /harness-reflect
  - 3 个新 hook: rule-engine.sh + pipeline-quality-gate.sh + post-lesson-trigger.sh
- **Phase 12 代码已实现并经 Codex 全链审计**:
  - 新 Loss: `compute_spear_loss_unbounded` — Scaled MSE + Static Centering + Leaky Blinding
  - 新指标: best.pt 保存由 D9-D0 Spread 驱动 (替代 PfRet, INS-058)
  - torch.compile 已启用 (mode=reduce-overhead)
  - window_size_s=10 已修复 (C-057)
- **Docker**: omega-tib:phase12-v4, canary PASSED
- **GCP 烟测 v5 状态**: 训练功能验证 PASS，推理断言量纲 FAIL
  - 训练: Loss 0.91→0.80 (正常下降 ✓), Std_yhat=8.78→12.40 BP (活着 ✓)
  - D9-D0=-7.7 BP (warmup 期负值正常，2 epoch 太短无法判断)
  - 推理输出 raw logit (pred ~-0.055)，断言脚本期望 BP 量级 → FAIL
  - **修复**: 断言中 pred_std 需 ×10000 转 BP，与 validate() 一致
- **正式训练 YAML 就绪**: `gcp/phase12_train_ondemand.yaml`, n1-standard-8 + T4 On-Demand, ~$13/17h

## Changes This Session (~38 commits)

### Living Harness V3 (本次 session 核心)
- `incidents/` Trace Vault: 10 个事件目录 (42 files), 5 组重复模式全迁移
- `rules/active/*.yaml`: 16 条规则 (R-001~R-016), 覆盖 block + warn 级别
- `.claude/hooks/rule-engine.sh`: 数据驱动规则引擎 (替代硬编码 lesson-enforcer)
- `.claude/hooks/pipeline-quality-gate.sh`: INS 完整性 + Spec DRAFT + 失败回溯
- `.claude/hooks/post-lesson-trigger.sh`: 教训记录后自动提示 /lesson-to-rule
- `.claude/skills/lesson-to-rule/`: 教训→规则自动转化 (含 incidents 自动迁移)
- `.claude/skills/harness-reflect/`: 自省循环 (规则效果 + 管线健康 + 健康分)
- `architect/chain_of_custody.yaml`: 指令全生命追踪
- `tools/spec_code_alignment.py`: Spec-Code 参数漂移检测
- `tests/test_harness_v3.py`: 26 项烟测 (block/warn/exempt/compound/perf)
- `LIVING_HARNESS.md`: 完整架构文档
- `/architect-ingest` 升级: INS 6-section 模板 + spec draft/final + chain_of_custody
- `/dev-cycle` 升级: Stage 8.5 spec-code 对齐门禁
- `safe_build_and_canary.sh` 升级: Step 1d spec-code alignment check

### Phase 12 代码 (上一个 session)
- `b03e66f` feat: Phase 12 Unbounded Spear — 新 Loss + D9-D0 Spread + ws=10
- `69ddafd` feat: torch.compile + deploy-cycle Stage 5.5 烟测 (8 条防线)
- `de569ef` fix: gcp/ 文件漂移 (C-058)
- `ef376a7` fix: Dockerfile COPY drift gate 结构性修复 (C-058)
- `ef46878` fix: BP double-conversion (C-059)
- `65e34d7` fix: Codex 审计 — model default (4,4)→(32,10)
- `206af7f` fix: 恢复 pred×10000 投影 (C-059b 梯度冻死修复)
- 架构师指令归档: 2 份 directive, INS-057~064, spec 全面更新

## Key Decisions
1. **Path A (INS-063)**: 仅居中 target, pred 不居中 — 防 Beta 走私
2. **lambda_s = 1e-4** (架构师 Override, 非 1e-3)
3. **static_mean_bp = 40.0** 作为 Config 注入参数 (INS-064)
4. **GCP On-Demand** (非 Spot): 用户明确要求，~$13 买确定性
5. **pred × 10000 投影**: model raw logit 必须投影到 BP 空间，target 不动 (已是 BP from ETL)

## Lessons Learned (C-057~C-061)
- C-057: 代码默认值 vs spec 漂移 (ws=4 残留)
- C-058: 双副本必然漂移 → drift gate 结构性修复
- C-059: 量纲修复必须逐变量追溯，不可一刀切 (target 已 BP, pred 需 ×10000)
- C-060: 部署命令从目标环境反推，不假设路径
- C-061: 每次烟测用唯一 output_dir，防 resume 跳过

## Next Steps
1. **[P0] 修复烟测断言量纲**: `pred_std * 10000` 或改用 rank-based 断言
2. **[P0] 重提交烟测 v6**: 断言修复后一次通过即可
3. **[P0] 提交正式训练**: `gcp/phase12_train_ondemand.yaml` (20 epochs, 5000 steps)
4. **[P1] E0 后 post-deploy 烟测**: 等 E0 完成后跑推理验证
5. **[P2] Phase 12 HPO**: 启用 Vizier MedianStoppingRule + Transfer Learning

## Warnings
- **spec 注释需更新**: `loss_function:` 伪代码仍写 `pred * 10000; tgt * 10000`，实际是 `pred * 10000` only
- **linux1 不可达**: SSH Connection refused, 需检查节点状态
- **phase11e_config.yaml 是旧的**: 不含新 CLI 参数，不可用于 Phase 12
- **推理脚本 pred_bp 列是 raw logit**: 不是真正的 BP。排序不受影响，但绝对值需 ×10000

## Remote Node Status
- linux1: SSH Connection refused (本次会话无法连接)
- windows1: 未检查
- GCP: 6 次烟测 job 提交 (v1~v5+v4b), Docker v4 canary PASSED

## Architect Insights (本次会话 — 8 条)
- INS-057: SRL 捷径学习确认 — z_core 被架构旁路饿死
- INS-058: PfRet 评价失效 — 方差坍缩下等价等权 Beta
- INS-059: IC Loss 历史翻案 — Phase 6 IC=0.066 为真信号
- INS-060: Phase 12 无界之矛(审计版) — Scaled MSE + Static Centering
- INS-061: 空间深度恢复强制令 — ws=4 脏补丁
- INS-062: MSE 量纲碾压与噪声过拟合防线
- INS-063: Excess BP 输出语义 — 仅居中 Target，封杀路径 B
- INS-064: Static Mean 全局先验注入 — 严禁 Batch 内动态计算

## Machine-Readable State
```yaml
phase: "12_unbounded_spear"
status: "living_harness_v3_deployed + smoke_test_training_pass_assertion_fail"
harness:
  version: "v3_living"
  rules_active: 16
  incidents_migrated: 10
  hooks: 9
  skills: 9
  smoke_test: "26/26 passed"
  key_doc: "LIVING_HARNESS.md"
docker: "omega-tib:phase12-v4"
smoke_test_v5:
  training: PASS
  loss_e0: 0.91
  loss_e1: 0.80
  std_yhat_e0: 8.78
  std_yhat_e1: 12.40
  d9d0_e0: -7.70
  d9d0_e1: -9.31
  inference: PASS
  assertion: FAIL (pred_std unit mismatch — raw logit vs BP)
  fix_needed: "pred_std * 10000 in assertion script"
full_train_yaml: "gcp/phase12_train_ondemand.yaml"
full_train_cost: "$13 (On-Demand T4, ~17h)"
full_train_output_dir: "phase12_unbounded_v1"
commits_this_session: 8
insights_this_session: [INS-057, INS-058, INS-059, INS-060, INS-061, INS-062, INS-063, INS-064]
new_lessons: [C-057, C-058, C-059, C-060, C-061]
vizier_todo: "MedianStoppingRule + Transfer Learning (memory: project_vizier_advanced_features.md)"
```
