# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-04 — **STATUS: Phase 12 post-flight COMPLETE — 信号不可交易，等待架构师审计。**

## Current State
- **Phase 12 训练 COMPLETE**: 20 epochs, best D9-D0=4.48BP (E0), checkpoints 在 GCS
- **Phase 12 Post-flight COMPLETE**: E0 + E19 双模型推理完成，信号不足
- **8 轮外部审计 COMPLETE**: 代码正确，发现并修复 torch.compile 静默加载 bug
- **Living Harness V3**: 16 规则 + 10 incidents + 10 hooks + 9 skills

## Phase 12 Post-Flight 结果

### E0 (best.pt, MDL 未激活) vs E19 (latest.pt, MDL 激活后)

| 指标 | E0 | E19 | Phase 11c baseline | 判定 |
|------|-----|------|-------------------|------|
| pred_std | 26.61 BP | 18.57 BP | 5.64 BP | 方差恢复 ✓ |
| D9-D0 spread | 4.51 BP | 1.29 BP | 8.90 BP | 不足 ✗ |
| Pearson IC | 0.0046 | 0.0001 | 0.0210 | 退步 ✗ |
| Spearman Rank IC | -0.0206 | -0.0297 | — | **负值** ✗ |
| Monotonicity | 7/9 | 4/9 | — | E0 略好 |
| z_sparsity | 5.4% | 18.5% | — | MDL 生效 |
| Cost coverage | 4.5/25 BP | 1.3/25 BP | — | 不可交易 |

### 关键诊断
1. **方差坍缩已解决**: Unbounded Spear 成功恢复 pred_std (5.64→26.61 BP)
2. **判别力消失**: D9-D0 从 Phase 11c 的 8.90 退步到 4.51 BP
3. **Rank IC 为负**: 模型排序能力比随机差
4. **MDL 压缩杀信号**: D9-D0 从 E0 的 4.51 单调降到 E19 的 1.29，lambda_s=1e-4 仍太强
5. **结论**: 不是代码 bug（8 轮审计确认），是模型/Loss 架构层面问题

## Changes This Session

### 代码修复（8 轮外部审计驱动）
1. **[CRITICAL] torch.compile `_orig_mod.` 静默加载修复**
   - `train.py`: save 端 strip `_orig_mod.` 前缀
   - `backtest_5a.py`: load 端防御性 strip + 诊断日志
   - 此 bug 可能导致历次"训练成功推理失败"
2. **[CRITICAL] backtest_5a.py 默认值对齐**: hidden_dim=64, window_t=32, costs_bp=25
3. **[CRITICAL] pred_bp 量纲修复**: `prediction * 10000.0` (raw logit → BP)
4. **[HIGH] SRL overflow clamp**: `±1e12` before symlog (train.py + backtest_5a.py)
5. **[LOW] 死代码清理**: 删除 `compute_spear_loss_moment_matched`, 修复默认值, core SRL autocast
6. **[SYNC] gcp/ 目录同步**: 所有 .py 文件与根目录一致

### 新教训 (C-062~C-064)
- C-062: torch.compile `_orig_mod.` 静默杀推理
- C-063: GCS pipe 不可用于推理，用 FUSE `/gcs/`
- C-064: 推理 staging 只下载需要的 split

## Key Decisions
- **E0 作为 post-flight 模型**: MDL warmup=2 前的未压缩模型，val D9-D0 最优
- **Rank IC 为负**: 模型排序能力比随机差，不是 lambda_s 问题
- **Outlier clamp 维持架构师设计**: clamp 在居中后，右尾 540 BP 截断
- **GCS FUSE 替代 pipe**: Gemini 确认 FUSE 是 Vertex AI 推荐方案

## Next Steps（等架构师裁决）
1. **[P0] 架构师审计**: 汇报 D9-D0=4.51 BP 和 Rank IC=-0.02 的诊断
2. **[P1] HPO 探索**: Vizier 70-trial, lambda_s 搜索含 0, 验证是否有可交易超参组合
3. **[P2] 损失函数重新审视**: Rank IC 为负可能需要回到 IC-based Loss 或混合 Loss

## Warnings
- **linux1 SSH 不稳定**: OOM 后反复 Connection refused，推理已改用 Vertex AI
- **gcp/phase7_inference.py 未被 Dockerfile COPY**: 需要更新 Dockerfile 或 YAML 内联

## 8-Round External Audit Summary

| 轮次 | 工具 | 结果 |
|------|------|------|
| R1: Core model+loss | Codex | 9 PASS, 1 FAIL (SRL overflow → 已修) |
| R2: Spec-code alignment | Codex | 4 CRITICAL drift (默认值 → 已修) |
| R3: Train-serve skew | Codex | FRT 一致, 2 外部问题 (→ 已修) |
| R4: Math correctness | Gemini | 6 PASS, 2 WARNING (clamp 非对称 → 维持) |
| R5: Directive compliance | Codex | 活跃路径全合规, 4 死代码 (→ 已清理) |
| R6: Fix verification | Codex | 10 PASS, 2 FAIL (_orig_mod_ + gcp/ → 已修) |
| R7: Fix math verification | Gemini | 3/3 PASS |
| R8: Final torch.compile | Codex | 5/5 PASS |

## Remote Node Status
- **linux1**: SSH 不稳定 (OOM 后恢复缓慢), 推理改用 Vertex AI
- **Vertex AI**: T4 GPU, 推理正常 (GCS FUSE 模式)

## Architect Insights (本次会话)
- **torch.compile _orig_mod. 是潜在历史元凶**: 可能解释历次 Phase 的"训练好推理差"
- **方差恢复但判别力消失**: Unbounded Spear 解决了方差坍缩，但模型未学到排序信号
- **MDL 确认有害**: D9-D0 从 E0→E19 单调下降，压缩杀信号
- **GCS FUSE 是正确方案**: Gemini 确认 pipe:gcloud 是反模式

## Machine-Readable State
```yaml
phase: "12_unbounded_spear"
status: "postflight_complete_signal_insufficient"
harness:
  version: "v3_living"
  rules_active: 16
  incidents_total: 64
  hooks: 10
  skills: 9
docker: "omega-tib:phase12-postflight-v1"
formal_training:
  job_id: "340079341608108032"
  status: SUCCEEDED
  best_d9d0: {epoch: 0, d9d0: 4.48, saved_as: "best.pt"}
  checkpoint_dir: "gs://omega-pure-data/checkpoints/phase12_unbounded_v1/"
postflight:
  status: COMPLETE
  e0_d9d0: 4.51
  e19_d9d0: 1.29
  e0_rank_ic: -0.0206
  e0_pearson_ic: 0.0046
  e0_pred_std: 26.61
  e0_z_sparsity: 0.054
  samples: 1904747
  symbols: 5200
  verdict: "NOT TRADEABLE — spread 4.51 < cost 25 BP"
  parquet_e0: "gs://omega-pure-data/postflight/phase12_val_predictions.parquet"
  parquet_e19: "gs://omega-pure-data/postflight/phase12_latest_val_predictions.parquet"
audit:
  rounds: 8
  tools: ["Codex", "Gemini"]
  critical_fix: "torch.compile _orig_mod. silent load failure"
  all_active_paths: "COMPLIANT"
code_fixes:
  - "torch.compile _orig_mod_ strip (save+load)"
  - "backtest defaults aligned (hd=64, wt=32, costs=25)"
  - "pred_bp * 10000 scaling"
  - "SRL overflow clamp ±1e12"
  - "dead code cleanup"
  - "gcp/ sync"
new_lessons: ["C-062", "C-063", "C-064"]
next_decision: "architect_audit"
```
