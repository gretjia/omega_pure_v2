# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-03-29 — **STATUS: Phase 7 inference v16 build 中，A100 Spot 待提交**

## Current State
- **Phase 7 inference**: v16 Docker 构建中，A100 Spot job 待提交
- **Shard 修复**: linux1 LAN 直连修复中 (43/193, 59/h, ~04:50 UTC 完成)
- **旗舰模型**: T29 (hd=64, 19.7K params) — 压缩即智能
- **时空修正 (INS-022)**: 20 bars = 0.4 天。OMEGA 是 T+1 隔夜波段模型

## Changes This Session
- **phase7_inference.py v16**: 6 次迭代重写
  - v1: CPU hardcoded → v2: GPU auto-detect → v3: AMP + vectorize
  - v11: ThreadPool prefetch → v13: empty shard tolerance
  - v15: pipe:gcloud storage cat 流式读取（Gemini GCS best practice）
  - v16: Gemini 最终审计修复（ls 输出过滤、checkpoint 原子性、timeout 增大）
- **三方审计通过**: Gemini 数学/金融 + Codex 代码质量 + Gemini GCS 架构
- **CLAUDE.md 更新**: 规则 32-33 强制经验回读，规则 48-49 GCS/ETA 教训
- **VIA_NEGATIVA 新增 5 条**: CPU 盲目部署、GPU 伪可用、GCS FUSE、squeeze 陷阱、不读经验
- **Shard 修复发现**: 3月28日修复报告 "200/200 完成" 实际 115 个仍为空

## Key Decisions
1. **L4 → A100 Spot**: L4 training quota 不存在/耗尽，A100 有 20 quota
2. **GCS FUSE → pipe streaming**: 消除 staging，100GB disk 代替 800GB
3. **Spot + checkpoint**: checkpoint_interval=50，SIGTERM flag 模式，自动 resume
4. **linux1 GPU 不可用**: Radeon 8060S (RDNA 3.5 gfx1150) HIP kernel 未编译
5. **Shard 修复路径**: linux1 → LAN 192.168.3.93:7897 → GCS（绕过反向隧道瓶颈）

## 推理优化经验（Bitter Lesson）

### 时间线：为什么从头没发现最优方案
1. linux1 CPU 盲目部署 → 预估 2h 实际 55h（不算数据量）
2. linux1 GPU → HIP kernel crash（`cuda.is_available()=True` ≠ 真能用）
3. Vertex AI L4 GCS FUSE → 467 shards/h（Python 优化无效，FUSE 是瓶颈）
4. Local SSD staging → 614 shards/h 但 staging 不稳定（pd-ssd burst credit 耗尽）
5. Pipe streaming → 466 shards/h（与 FUSE 持平，但无 staging、无大磁盘）
6. L4 quota 耗尽 → 改 A100 Spot

### 根因表
| 失误 | 教训 |
|------|------|
| 不算数据量就预估 ETA | 先 `du -sh` / `gsutil du` |
| `cuda.is_available()=True` 就开 GPU | ROCm iGPU 先跑 smoke test |
| GCS FUSE 当本地磁盘 | FUSE 有 POSIX 转换开销和 stat 延迟 |
| Python 优化了但没解决 I/O | 瓶颈在网络/FUSE，不在 Python |
| 云资源分配不算就猜 | 300→500→800GB，三次 disk-full |
| 修复操作不验证就报告成功 | "修了" ≠ "修好了" |
| 不读历史经验就写代码 | CLAUDE.md 已强制要求回读 |

### 未来推理任务 SOP
1. `du -sh` / `gsutil du` 算数据量 → 估算真实 ETA
2. 数据在 GCS → 直接用 Vertex AI GPU
3. 用 pipe:gcloud storage cat 流式读取，不 staging
4. 小模型 + 大数据 = 数据管道是瓶颈，不是 GPU
5. Spot + checkpoint_interval=50 + SIGTERM flag
6. Gemini 3.1 Pro 审计 → 修 bug → 再部署

## 深圳局域网 → GCS 上传方法
- **代理节点**: Mac Studio LAN IP `192.168.3.93:7897`（商业 VPN）
- **方法**: `export https_proxy=http://192.168.3.93:7897` + Python google-cloud-storage SDK
- **已验证**: linux1 (`192.168.3.113`) → proxy → GCS，速率 ~5 MB/s
- **注意**: 不走反向隧道（<1 MB/s），不走 Tailscale（多余跳数），走 LAN IP

## Next Steps
1. ~~v16 Docker build~~ 🔄 构建中
2. 提交 A100 Spot job（v16 镜像 + pipe streaming + 自动 resume）
3. Shard 修复完成后验证 0 空文件
4. inference 完成 → 下载 predictions.parquet → simulate → report
5. 后续考虑 HSA_OVERRIDE_GFX_VERSION 让 linux1 GPU 可用

## Warnings
- **L4 training quota 不存在**: 用 A100（quota=20）代替
- **GCS 193 个空 shard**: 修复中（43/193 完成），v16 脚本会安全跳过
- **linux1 GPU 不可用**: Radeon 8060S HIP kernel 未编译
- **GCS FUSE os.replace 不原子**: v16 改用 /tmp 写入 + shutil.copy2
- **Gemini CLI 429 限流**: 改用 curl API + gemini-3.1-pro-preview

## Remote Node Status
- linux1-lx: ONLINE, shard 修复进行中 (PID 1145894, 59/h, LAN proxy)
- Vertex AI: v16 build 中，A100 Spot job 待提交

## Audit Summary (本次会话)
| 审计 | 工具 | 结果 |
|------|------|------|
| 数学/金融 | Gemini 3.1 Pro | FAIL→修复: try/except 过宽 + z_sparsity 偏差 |
| 代码质量 | Codex | FAIL→修复: SIGTERM 竞态 + checkpoint 非原子 + 内存 |
| GCS 架构 | Gemini 3.1 Pro | 重构: pipe streaming 替代 FUSE/staging |
| 部署前 | Gemini 3.1 Pro | 修复: ls 输出过滤 + timeout + FUSE 原子性 |

## Phase 6 HPO 最终结果

Best: **T36 IC=+0.0667** | Flagship: **T29 IC=+0.0661 (hd=64, 单调性 8/9)**

| Trial | IC | Spread | Mono | Top 10% | Net Profit |
|-------|-----|--------|------|---------|-----------|
| T36 (hd=128) | +0.067 | 12.55 BP | 7/9 | 14.56 BP | +4.56 BP |
| T29 (hd=64) | +0.066 | 11.45 BP | 8/9 | 14.37 BP | +4.37 BP |

## Machine-Readable State
```yaml
phase: 7
status: "v16_build_pending_a100_spot"
flagship_model: {trial: 29, ic: 0.0661, params: {hd: 64, wt: 32, lr: 3.2e-4, lambda_s: 1e-7, wu: 2, aw: 1e-3, bs: 128}}
flagship_checkpoint: "gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt"
inference_docker: "phase7-v16"
inference_gpu: "A100 Spot"
inference_method: "pipe:gcloud storage cat (streaming, no staging)"
shard_repair: {total: 193, done: 43, remaining: 150, method: "linux1 LAN proxy 192.168.3.93:7897"}
lan_proxy: {host: "192.168.3.93", port: 7897, type: "commercial VPN on Mac Studio"}

time_scale: {bars_per_day: 50, payoff_bars: 20, payoff_days: 0.4, strategy: "T+1 overnight momentum"}
backtest: {cost_bp: 25, t1_lock: true, limit_enforcement: true, trailing_stop: -10%, success: "asymmetry>3.0 AND pf>1.5"}

scripts: [phase7_date_mapper.py, phase7_inference.py, phase7_simulate.py, phase7_report.py]
audits: {codex: "4F fixed", gemini_math: "2F fixed", gemini_gcs: "restructured", gemini_deploy: "3F fixed", axioms: "ALL PASS"}
commits: ["7f8e795", "6186f9c", "afbc726", "583a741"]
insights: [INS-019, INS-020, INS-021, INS-022, INS-023]
```

## Architect Insights (本次会话)
本次会话无新架构洞察（聚焦在工程部署优化）
