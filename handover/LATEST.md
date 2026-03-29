# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-29 — **STATUS: Harness V2 落地 + Phase 7 inference v13 运行中**

## Current State
- **Vertex AI Job `5960500483188588544`** (phase7-inference-v13-robust2): RUNNING on g2-standard-8 + L4 GPU, 800GB pd-ssd
- **Harness V2 已落地**: 3 safe wrapper 脚本 + 2 新 hook + OMEGA_LESSONS.md + CLAUDE.md 精简 + 回归测试套件
- **旗舰模型**: T29 (hd=64, 19.7K params) — 压缩即智能

## Phase 6 HPO 最终结果

Best: **T36 IC=+0.0667** | Flagship: **T29 IC=+0.0661 (hd=64, 单调性 8/9)**

| Trial | IC | Spread | Mono | Top 10% | Net Profit |
|-------|-----|--------|------|---------|-----------|
| T36 (hd=128) | +0.067 | 12.55 BP | 7/9 | 14.56 BP | +4.56 BP |
| T29 (hd=64) | +0.066 | 11.45 BP | 8/9 | 14.37 BP | +4.37 BP |

## Changes This Session
- **Harness V2 完整落地**（用户发起 Phase 7 灾难尸检 → Codex 审计 plan → 执行 → Codex 审计代码 → 修 2 bug）
  - Layer 1: `gcp/safe_upload.sh`, `gcp/safe_build_and_canary.sh`, `gcp/safe_submit.sh`, `tests/test_known_bugs.py`
  - Layer 2: `.claude/hooks/pre-deploy-gate.sh` (阻止无 canary 部署), `.claude/hooks/post-upload-verify.sh` (自动验证上传)
  - Layer 3: `OMEGA_LESSONS.md` (唯一经验源, 6 元公理 Ω1-Ω6 + 23 案例), CLAUDE.md 53→33 条, VIA_NEGATIVA 冻结归档
- **upload_shards.sh 废弃**: 重命名为 `.DEPRECATED_UNSAFE`（SSH pipe 空文件 bug 的温床）
- **dev-cycle SKILL 升级**: 9→10 阶段，新增 Stage 0 Pre-mortem（列 3 方案 + 失败模式）
- **Codex 审计发现 2 bug**: manifest 缺 type 字段 + hook 整数比较错误 → 已修复

## Key Decisions
1. **Harness V2 设计哲学**: "物理约束 > 软性惩罚" — wrapper 脚本比文档规则更有效（类比 hd=64 瓶颈 > λ_s 正则化）
2. **外部审计保留**: 上次压缩错误地弱化了外部审计，这次 Ω5 明确为公理级要求
3. **经验统一到 OMEGA_LESSONS.md**: VIA_NEGATIVA 冻结，LATEST.md 去经验化，4 文件→1 入口

## Next Steps
1. **等待 v13 job 完成** — 监控: `gcloud ai custom-jobs describe 5960500483188588544 --region=us-central1 --format="value(state)"`
2. 推理完成后 → `phase7_simulate.py` → `phase7_report.py` → 成功标准: 不对称比>3.0 AND pf>1.5
3. **HK shard 修复**: 193 个空 shard 修复进程可能仍在 HK 后台运行（nohup）
4. **下次部署必须用 Harness V2 流程**: `safe_build_and_canary.sh` → `safe_submit.sh`

**监控命令**:
```
gcloud logging read "resource.type=ml_job AND resource.labels.job_id=5960500483188588544" --limit=5 --format="value(textPayload)" --order=desc
```

## Warnings
- **GCS 193 个空 shard**: linux1 本地完好，v13 用 robust skip 处理。HK 修复可能仍在进行
- **Harness V2 未 commit**: 所有变更在工作区，待用户确认后 commit
- **涨跌停检测是 best-effort**: 基于 spread-lock 启发式，无昨收数据
- **日期映射是近似值**: 基于 parquet 行数比例，±1-2 天误差

## Audit Summary
| 审计 | 工具 | 结果 |
|------|------|------|
| Harness V2 Plan 审计 | Codex (gpt-5.4) | 3 CRITICAL + 5 MISSING → 全部吸收 |
| Harness V2 Code 审计 | Codex (gpt-5.4) | 2 bug (manifest type + hook integer) → 已修复 |
| Phase 7 代码 | Codex + Gemini + omega_axioms | 前 session 已通过 |

## Remote Node Status
- linux1-lx: SSH 超时（Tailscale 可能掉线）
- Vertex AI: Job `5960500483188588544` RUNNING
- HK (43.161.252.57): 可能有 shard 修复 nohup 进程运行中

## Machine-Readable State
```yaml
phase: 7
status: "vertex_ai_inference_v13_running"
vertex_job: "5960500483188588544"
harness: "v2"
harness_files:
  safe_scripts: [gcp/safe_upload.sh, gcp/safe_build_and_canary.sh, gcp/safe_submit.sh]
  hooks: [.claude/hooks/pre-deploy-gate.sh, .claude/hooks/post-upload-verify.sh]
  lessons: OMEGA_LESSONS.md
  tests: tests/test_known_bugs.py
  manifest: gcp/manifest.jsonl
  deprecated: [gcp/upload_shards.sh.DEPRECATED_UNSAFE]
flagship_model: {trial: 29, ic: 0.0661, params: {hd: 64, wt: 32, lr: 3.2e-4, lambda_s: 1e-7, wu: 2, aw: 1e-3, bs: 128}}
flagship_checkpoint: "gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt"
meta_axioms: [Ω1_只信实测, Ω2_先量化后行动, Ω3_测试环境等于生产环境, Ω4_可执行大于可记忆, Ω5_生产者不等于验证者, Ω6_数据在哪计算在哪]
```

## Architect Insights (本次会话)
- **Harness V2 设计原理**: hd=64 瓶颈 > λ_s 正则化 → wrapper 脚本 > 文档规则 → 物理约束 > 软性惩罚。知行分离是灾难根因，不是知识不足。
