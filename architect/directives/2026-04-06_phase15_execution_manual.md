# Phase 15 执行手册
**版本**: V1 (2026-04-06)
**执行者**: Claude + 用户
**前置**: Phase 15 Plan V2 已通过外审 (Codex + Gemini)，代码已实现并通过审计

---

## 一、执行总览

```
Step 0  ──→  Step 1  ──→  Step 2  ──→  Step 3  ──→  Step 4
数据验证     训练稳定化    MLP归因      容量对比     跨窗口
(0h GPU)    (10.5h T4)   (6h T4)     (25h T4)    (16h T4)
  │            │            │           │            │
  │ GO/STOP    │ 4色判定     │ 4色判定    │ 3色判定     │ 3色判定
  ▼            ▼            ▼           ▼            ▼
 Step 1      Step 2     Step 3/4    Step 4      Phase 16
```

**总预算**: ~40h T4 ≈ $15 (ON_DEMAND)
**数据**: v3 shards (不等 ETL v5)
**对照基线**: Phase 13 E9 best Rank IC = +0.0292, 均值 ≈ +0.017

---

## 二、Step 0: 数据完整性验证

### 执行命令

```bash
# 1. 已完成: v3 shards 无 date 字段 (2026-04-06 实测确认)
#    meta.json 只有 {symbol, timestamp(递增序号)}
#    无法直接验证时序排序

# 2. embargo gap 已在代码中实现 (--embargo_shards=2)
#    train 末尾丢 2 shards + val 开头丢 2 shards = 4 shards 隔离带
```

### 关注指标

无。Step 0 是代码准备，不产出数值指标。

### GO/STOP 判定

| 条件 | 判定 |
|------|------|
| 代码编译通过 + embargo 逻辑在 train.py | ✅ GO → Step 1 |
| train.py 编译失败或 embargo 逻辑有误 | ❌ 修复后重来 |

**当前状态: ✅ GO** (代码已通过 8/8 内审 + Gemini 8/8 PASS)

---

## 三、Step 1: 训练稳定化

### 目标
**单一问题**: "batch=256 的梯度噪声是不是压制了 IC？"

### 执行前准备

```bash
# 1. Docker 构建 (在 omega-vm 上)
bash gcp/safe_build_and_canary.sh phase15 v1

# 2. Canary 通过后，提交正式训练
bash gcp/safe_submit.sh phase15 v1
# 或手动:
gcloud ai custom-jobs create \
  --region=us-central1 \
  --config=gcp/phase15_step1_config.yaml \
  --display-name="phase15-step1-stabilization"
```

### 训练期间关注指标 (从 Vertex AI 日志实时读取)

```bash
# 监控命令
gcloud ai custom-jobs stream-logs <JOB_ID> --region=us-central1 2>&1 | grep "Epoch.*DONE"
```

**每 Epoch 应输出**:

| 指标 | 含义 | 健康范围 | 危险信号 |
|------|------|---------|---------|
| `IC_loss` | 训练 IC Loss (running avg) | [-0.05, -0.01] | > 0 (模型没学到东西) |
| `RankIC` | 验证集 Spearman Rank IC | > 0 | < 0 (反信号) |
| `D9D0` | 验证集十分位 spread (BP) | > 0 | < 0 持续 3 epoch |
| `Std_yhat` | 预测标准差 (BP) | [5, 100] | < 1 (脑死亡) 或 > 500 (方差爆炸) |
| `RPB_grad` | RPB 梯度范数 | > 0.01 | < 0.001 (RPB 梯度死亡, Pre-LN 未生效) |
| `S_T` | z_core L1 范数 (监控) | > 0.1 | ≈ 0 (脑死亡, C-046) |

### 训练期间实时检查点 (不需等训练结束)

| 时间点 | 检查 | 行动 |
|--------|------|------|
| **E0 完成** (~42min) | RankIC > 0? Std_yhat 在 [5, 100]? | 如果 RankIC < 0 或 Std_yhat < 1 → **立即 kill job**, 检查代码 |
| **E2 完成** (~2h) | RankIC 趋势向上? | 如果 E0-E2 三个 RankIC 全 < 0 → **kill, 检查** |
| **E9 完成** (~6.5h) | 对比 Phase 13 E9: RankIC 0.029 | 记录，继续跑 |
| **E10** | EMA 启动，LR 切到 3e-5 | 日志应显示 "EMA started" |
| **E14 完成** (~10.5h) | 训练结束 | 等 EMA 评估输出 |

### 训练完成后的关键数据

训练日志末尾会输出:
```
EMA Val: RankIC=X.XXXXXX D9D0=X.XXBP Std=X.XXBP
Training complete. Best Rank IC: X.XXXXXX
```

**需要记录 3 个数字**:

| 数字 | 来源 | 用途 |
|------|------|------|
| `IC_ema` | EMA 模型的验证集 Rank IC | **主判定指标** |
| `IC_best` | 最佳单 epoch Rank IC | 与 Phase 13 的 0.029 对比 |
| `IC_mean` | E0-E14 Rank IC 均值 | 与 Phase 13 均值 0.017 对比 |

### Step 1 决策树

```
                        IC_ema = ?
                           │
              ┌────────────┼────────────┬──────────────┐
              │            │            │              │
         > 0.040      0.030~0.040  0.020~0.029     < 0.020
              │            │            │              │
          🟢 绿灯      🟡 黄灯      🟠 橙灯        🔴 红灯
              │            │            │              │
              │            │            │         ┌────┴────┐
              │            │            │         │ STOP!   │
              │            │            │         │ 数据泄漏│
              │            │            │         │ 或代码  │
              │            │            │         │ bug     │
              │            │            │         └─────────┘
              │            │            │
          训练噪声      训练有帮助    无明显改善
          是主瓶颈      非唯一瓶颈    架构是瓶颈
              │            │            │
              ▼            ▼            ▼
          Step 2       Step 2       Step 2
          + Step 3     + Step 3     跳 Step 3
          + Step 4     + Step 4     直接 Step 4
```

**判定细则**:
- 🟢 `IC_ema > 0.040`: Phase 13 的 0.029 被训练噪声严重压制。管线远未到极限。
- 🟡 `0.030 ≤ IC_ema ≤ 0.040`: 有改善但不够剧烈。训练和架构都可能是瓶颈。
- 🟠 `0.020 ≤ IC_ema < 0.030`: EMA 没有超过 Phase 13 best。训练稳定化不是主要瓶颈。
- 🔴 `IC_ema < 0.020`: Embargo gap 暴露了 Phase 13 的 0.029 有数据泄漏成分。**停下来，重新审视整个评估体系。**

**边界说明**: 0.029 属于 🟠 (无改善)。只有**严格超过 0.030** 才算 🟡。

---

## 四、Step 2: MLP Baseline (归因)

### 目标
**单一问题**: "Omega-TIB 的 FWT 拓扑 + 信息瓶颈 + AttentionPooling 贡献了多少增量信号？"

### 执行条件
Step 1 非 🔴 (任何 ≥ 0.020 的结果都执行 Step 2)。

### 执行命令

```bash
# 修改 config: --model_type=mlp, --output_dir 改为 phase15_step2_mlp
# 其他全部保持与 Step 1 相同 (grad_accum=16, EMA, embargo)
gcloud ai custom-jobs create \
  --region=us-central1 \
  --config=gcp/phase15_step2_mlp_config.yaml \
  --display-name="phase15-step2-mlp-baseline"
```

### 关注指标

与 Step 1 相同的指标，但核心关注点是 **MLP 的 IC_ema 与 Step 1 Omega IC_ema 的比值**。

### Step 2 决策树

设 Step 1 的 `IC_ema` 为 `IC_omega`，Step 2 的 `IC_ema` 为 `IC_mlp`:

```
                   IC_mlp / IC_omega = ?
                           │
           ┌───────────────┼───────────────┬───────────────┐
           │               │               │               │
        < 30%          30% ~ 60%       60% ~ 85%        > 85%
           │               │               │               │
       🟢 拓扑           🟡 拓扑         🟠 拓扑          🔴 拓扑
       贡献 >70%         有价值           贡献有限         几乎无增量
           │               │               │               │
       全力优化         双线并行:        优先特征工程     ┌────┴────┐
       FWT 架构         架构+特征        架构降优先级     │ 战略转向 │
           │               │               │             │ 停架构   │
           ▼               ▼               ▼             │ 转特征   │
       Step 3           Step 3           Step 4          └─────────┘
       + Step 4         + Step 4         (跳 Step 3)
```

**解读示例**:
- 如果 `IC_omega = 0.035`, `IC_mlp = 0.008` → 比率 23% → 🟢: OMEGA 拓扑贡献了 77% 信号
- 如果 `IC_omega = 0.035`, `IC_mlp = 0.030` → 比率 86% → 🔴: 拓扑几乎无增量
- 如果 `IC_omega = 0.025`, `IC_mlp = 0.012` → 比率 48% → 🟡: 拓扑有价值但非压倒性

---

## 五、Step 3: 容量对比 hd=64 vs 128

### 目标
**单一问题**: "hd=64 的瓶颈维度 (z_core=16) 是否过窄？"

### 执行条件
- Step 1 为 🟡 或 🟢 **且**
- Step 2 为 🟢 或 🟡 (MLP < 60% Omega)

如果 Step 1 为 🟠 或 Step 2 为 🟠🔴 → **跳过 Step 3**。

### 执行命令

6 个 Job 并行 (3 seed × 2 hd):

```bash
for HD in 64 128; do
  for SEED in 42 123 456; do
    # 修改 config: --hidden_dim=$HD --seed=$SEED --epochs=8
    # --output_dir=phase15_step3_hd${HD}_s${SEED}
    gcloud ai custom-jobs create ...
  done
done
```

每个 Job 跑 8 epoch (非完整 15，节省预算)。EMA 从 E5 开始 (最后 3 epoch 平均)。

### 关注指标

| 指标 | 来源 | 用途 |
|------|------|------|
| `IC_ema_64_{seed}` | 3 个 hd=64 Job 的 EMA IC | 计算 mean ± std |
| `IC_ema_128_{seed}` | 3 个 hd=128 Job 的 EMA IC | 计算 mean ± std |
| `pooled_std` | 6 个 Job 的合并标准差 | 显著性判断 |

### Step 3 决策树

```
        mean(IC_128) - mean(IC_64) = Δ
        pooled_std = σ
                    │
        ┌───────────┼───────────┐
        │           │           │
    Δ > 1σ      |Δ| < 1σ    Δ < -1σ
        │           │           │
    🟢 显著       🟡 不显著    🟠 更差
    容量是瓶颈    容量非瓶颈    噪声中过拟合
        │           │           │
    后续用        保持 hd=64   保持 hd=64
    hd=128        进 Step 4    加 dropout=0.05
        │           │           │
        └─────┬─────┘           │
              ▼                 ▼
          Step 4             Step 4
     (用 Step 3 最优 hd)   (hd=64 + dropout)
```

---

## 六、Step 4: 跨窗口通信 (Overlapping Windows)

### 目标
**单一问题**: "5 个隔离窗口之间零通信，是不是 IC 的硬天花板？"

### 执行条件
Step 1-3 确定最优基线后执行。

### 执行命令

3 个 Job (3 seed，用 Step 1-3 确定的最优 hd):

```bash
for SEED in 42 123 456; do
  # 修改: --overlap_windows=True --seed=$SEED
  # --output_dir=phase15_step4_overlap_s${SEED}
  gcloud ai custom-jobs create ...
done
```

**注意**: Step 4 需要先在 `omega_epiplexity_plus_core.py` 中实现 overlapping windows 逻辑。这是额外的代码变更，需要独立的 dev-cycle。

### 关注指标

| 指标 | 来源 | 用途 |
|------|------|------|
| `IC_ema_overlap_{seed}` | 3 个 overlap Job | mean ± std |
| `IC_ema_baseline_{seed}` | Step 1 或 Step 3 最优基线 | 对照 |

### Step 4 决策树

```
        mean(IC_overlap) - mean(IC_baseline) = Δ
                    │
        ┌───────────┼───────────┐
        │           │           │
    Δ > 1σ      |Δ| < 1σ    Δ < 0
        │           │           │
    🟢 跨窗口     🟡 重叠       🔴 更差
    释放新信号    不够激进       感受野非瓶颈
        │           │           │
        ▼           ▼           ▼
    Phase 16:    Phase 16:    Phase 16:
    Swin 2层     Swin 2层     转 Loss 优化
    (全面实现)   (更激进)     (Tail-Weighted IC)
```

---

## 七、全局决策树 (一页总览)

```
Step 0: 数据验证 ───────────────────────── ✅ 已完成 (无 date, 加 embargo)
  │
Step 1: 训练稳定化 (grad_accum=16 + EMA)
  │
  ├── 🔴 IC < 0.020 ──────────────────── STOP. 检查泄漏/bug
  │
  ├── 🟠 IC 0.020~0.029 ─┐
  │                       │
  ├── 🟡 IC 0.030~0.040 ─┤
  │                       ├──→ Step 2: MLP Baseline
  └── 🟢 IC > 0.040 ─────┘
                          │
              ┌───────────┼───────────┬───────────┐
              │           │           │           │
          🟢 MLP<30%  🟡 30~60%   🟠 60~85%   🔴 >85%
              │           │           │           │
              │           │           │       战略转向
              │           │           │       (停架构)
              │           │           │
              └─────┬─────┘           │
                    │                 │
          Step 1 是 🟡/🟢?            │
          且 MLP 非 🟠🔴?             │
                ┌───┴───┐             │
               Yes     No            │
                │       │             │
           Step 3:      │             │
           hd 对比      │             │
                │       │             │
           最优 hd ─────┘             │
                │                     │
           Step 4:                    │
           Overlapping Windows        │
                │                     │
         ┌──────┼──────┐              │
         │      │      │              │
     🟢 Swin  🟡 Swin  🔴 Loss       │
     2层(全面) 2层(激进) 优化          │
         │      │      │              │
         └──────┴──────┴──────────────┘
                    │
                Phase 16
```

---

## 八、关键数据记录模板

每个 Step 完成后，填写以下模板并保存到 `reports/phase15/`:

### Step 1 记录模板
```
# Phase 15 Step 1 Results
Date: YYYY-MM-DD
Job ID: <Vertex AI Job ID>
Duration: X.Xh
Cost: $X.XX

## Epoch-by-Epoch
| Epoch | IC_loss | RankIC | D9D0(BP) | Std_yhat | RPB_grad | S_T |
|-------|---------|--------|----------|----------|----------|-----|
| 0     |         |        |          |          |          |     |
...
| 14    |         |        |          |          |          |     |

## Key Metrics
IC_best (single epoch): 
IC_mean (E0-E14):
IC_ema (EMA model):
D9D0_ema:
Std_ema:

## vs Phase 13 Baseline
IC_best delta: IC_best - 0.0292 = 
IC_mean delta: IC_mean - 0.017 = 

## 判定
Color: 🟢/🟡/🟠/🔴
Next: Step 2 / Step 2+3 / STOP
```

### Step 2 记录模板
```
# Phase 15 Step 2 MLP Baseline Results
Date: YYYY-MM-DD
Job ID: <Vertex AI Job ID>

## Key Metrics
IC_ema_mlp:
IC_ema_omega (from Step 1):
Ratio: IC_mlp / IC_omega = X%

## 判定
Color: 🟢/🟡/🟠/🔴
OMEGA topology contribution: >70% / 30-70% / <30%
Next: Step 3+4 / Step 4 / 战略转向
```

---

## 九、紧急情况处理

| 情况 | 症状 | 处理 |
|------|------|------|
| 训练 NaN | `IC_loss=nan` 或 `Std_yhat=nan` | Kill job. 检查 grad_accum 是否破坏了 AMP scaler |
| 方差坍缩 | `Std_yhat < 1 BP` 持续 3 epoch | Kill job. 可能 EMA LR 切换太早 |
| Spot 抢占 | Job FAILED + SIGTERM 日志 | 重提交 (ON_DEMAND 不应发生) |
| 内存不足 | OOM 日志 | 减 batch_size 到 128，grad_accum 改为 32 (保持有效 batch=4096) |
| 训练太慢 | > 60min/epoch (预期 ~42min) | 检查 num_workers 和 pipe 模式是否正常 |

---

## 十、与 ETL v5 的协调

```
时间线:
Day 0 (今天):
  ├── Step 0: ✅ 完成 (数据验证 + 代码实现)
  ├── Docker build + canary (~2h)
  └── ETL v5 Sort: 433/743 (~16h 剩余)

Day 1:
  ├── Step 1 提交 (~10.5h)
  └── ETL v5 Sort 完成 → ETL v5 Pipeline 启动

Day 2:
  ├── Step 1 结果 → 判定
  ├── Step 2 MLP 提交 (~6h)
  └── ETL v5 Pipeline 运行中

Day 3:
  ├── Step 2 结果 → 归因判定
  ├── Step 3 提交 (如需, 6 Jobs 并行)
  └── ETL v5 Pipeline → merge → QC

Day 4-5:
  ├── Step 3 结果 → 容量判定
  ├── Step 4 提交 (如需)
  └── ETL v5 shards upload GCS → v5 就绪

Day 5+:
  └── Phase 15 完成 → Phase 16 用 v5 shards
```

**关键**: Phase 15 用 v3 shards，ETL v5 完全独立并行，互不阻塞。

---

*Phase 15 Execution Manual V1 — 2026-04-06*
