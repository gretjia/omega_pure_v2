# Phase 15: Pipeline Stabilization + Attribution Baseline + Capacity Verification
**日期**: 2026-04-06
**来源**: 四方独立审计最终结论 (Codex + Gemini + Claude×2)
**状态**: [V2 — Codex 5-FAIL + Gemini 1-FAIL 全部修正]
**前置条件**: Phase 14 Step 0-2 已完成, ETL v5 Sort 进行中 (ETA ~17h)

---

## 审计修正记录

| 原始 FAIL/WARNING | 审计方 | 修正 |
|-------------------|--------|------|
| OneCycleLR total_steps 不整除 | Codex+Gemini | steps_per_epoch 改为 4992 (=312×16) |
| SWA tau=0.999 ≠ AveragedModel 默认 | Codex | 改用 EMA: `get_ema_multi_avg_fn(0.999)` |
| update_bn() 对 LayerNorm 无用 | Codex | 删除 update_bn 调用 |
| 分支阈值有间隙/矛盾 | Codex | 完全重写决策树，覆盖全部区间 |
| Spec/代码未同步 | Codex | 在 Plan 中标注需同步的文件清单 |
| gcp/phase15_step1_config.yaml 缺失 | Codex | 纳入 Step 1 实施清单 |
| Embargo 数学论证错误 | Codex+Gemini | 修正计算 |
| Overlapping windows 输出合并未定义 | Codex | 补充合并策略 |
| 缺多种子统计检验 | Gemini | Step 3/4 用 3 个 seed |
| SWA 后应切 SWALR | Gemini | 加入 SWALR 切换 |
| RPB 梯度监控 | Gemini | 加入日志项 |

---

## 0. Phase 15 总纲

**目标**: 回答 "Phase 13 的 Rank IC=0.029 是管线的上限还是下限？"

**方法**: 严格控制变量的串行实验链。每一步只改变一个变量。

**数据**: v3 shards (1992 shards, gs://omega-pure-data/wds_shards_v3_full/)。不等 ETL v5。

**硬件**: Vertex AI T4 ON_DEMAND

**总预算**: ~40h T4 ≈ $15

**v3 shards 的 date 字段限制**: v3 shards 的 meta.json 可能无 date 字段（ETL v3 设计时未写入）。因此 Phase 15 的评估仍使用 **global Spearman Rank IC**（与 Phase 13 一致），不引入 per-date 评估。per-date 评估留待 ETL v5 shards (含 date) 完成后的 Phase 16。

---

## Step 0: 数据完整性验证 [0h GPU, 纯分析]

### 0.1 Shard 时序排序验证

**执行**:
```bash
# 在 linux1 上采样 5 个 shard 的 meta.json
python3 -c "
import webdataset as wds, json
for url in ['omega_shard_00000.tar', 'omega_shard_00800.tar',
            'omega_shard_01593.tar', 'omega_shard_01594.tar', 'omega_shard_01991.tar']:
    dates = set()
    for sample in wds.WebDataset(f'/omega_pool/wds_shards_v3_full/{url}').decode():
        meta = json.loads(sample.get('meta.json', b'{}'))
        if meta.get('date'): dates.add(meta['date'])
    print(f'{url}: {min(dates) if dates else \"NO DATE\"} ~ {max(dates) if dates else \"NO DATE\"}')
"
```

**分支**:

| 结果 | 行动 |
|------|------|
| 日期单调递增 | ✅ 继续 Step 0.2 |
| 边界 shard 日期重叠 | ⚠️ 加 embargo gap，信号可能被高估 |
| 完全无序 | ❌ **Phase 15 暂停**，需重建时序 shards |
| meta.json 无 date 字段 | ⚠️ 用 sample key 中的 symbol 前缀推断；或直接加 embargo gap 作为保守措施 |

### 0.2 Embargo Gap

丢弃 train 最后 2 shards + val 最前 2 shards。

**数学验证** (Codex 审计修正):
- 每 shard ≤ 5000 样本
- ETL stride=20 bars, window=160 bars
- 需要隔离的最小 bar 距离 = 160 bars (一个完整窗口)
- 2 shards × 5000 samples × 20 bars/sample = 200,000 bars >> 160 bars
- **结论: 2 shards 远超需要，margin 极大**

代码 (`train.py` 新增):
```python
# Phase 15: embargo gap
parser.add_argument("--embargo_shards", type=int, default=0,
                    help="Drop N shards at train/val boundary each side (Phase 15=2)")

# 在分割处:
n_train = int(len(valid_shards) * (1 - args.val_split))
train_shards = valid_shards[:n_train - args.embargo_shards]
val_shards = valid_shards[n_train + args.embargo_shards:]
logger.info(f"Embargo gap: {args.embargo_shards} shards/side, "
            f"train={len(train_shards)}, val={len(val_shards)}")
```

### 0.3 Step 0 实施清单

- [ ] ssh linux1 执行 shard 时序验证脚本
- [ ] 在 `train.py` 和 `gcp/train.py` 中添加 `--embargo_shards` 参数
- [ ] 更新 `architect/current_spec.yaml` 添加 `training.embargo_shards: 2`
- [ ] 交付: `reports/phase15/step0_shard_temporal_verification.json`

---

## Step 1: 训练稳定化 [~10.5h T4]

### 1.1 目标

不改模型架构，仅通过训练技巧提升 Rank IC。控制实验。

### 1.2 变更清单 (vs Phase 13)

| 参数 | Phase 13 | Phase 15 Step 1 | 理由 |
|------|---------|----------------|------|
| gradient_accumulation | 1 | **16** | 有效 batch 256→4096, SNR 4x |
| steps_per_epoch | 5000 | **4992** (=312×16) | 整除 grad_accum (Gemini FAIL 修正) |
| OneCycleLR total_steps | 75,000 | **4,680** (=312×15) | optimizer steps = 312/epoch × 15 epochs |
| EMA | 无 | **epoch 10 开始, decay=0.999** | 替代 checkpoint 选择偏差 |
| LR after EMA start | OneCycleLR 继续 | **SWALR(lr=3e-5)** | Gemini 建议: EMA 期间用低恒定 LR |
| embargo_shards | 0 | **2** | 防泄漏 |
| RPB grad 监控 | 无 | **每 epoch 记录** | Gemini 建议: 确认 Pre-LN 修复有效 |
| **其他全部不变** | hd=64, IC Loss, λ_s=0, mask_prob=0, no_amp, seed=42 | 完全相同 | 控制变量 |

### 1.3 Gradient Accumulation 实现

```python
# train.py 新增参数
parser.add_argument("--grad_accum", type=int, default=1,
                    help="Gradient accumulation steps (Phase 15=16)")

# train_one_epoch() 修改:
ACCUM = args.grad_accum
optimizer.zero_grad(set_to_none=True)

for step_i in range(steps_per_epoch):
    # ... get batch, forward ...
    loss = total_loss / ACCUM  # 缩放
    loss.backward()

    if (step_i + 1) % ACCUM == 0:
        torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        if scheduler is not None:
            scheduler.step()
        global_step += 1  # global_step 只在 optimizer step 时递增

# 注意: steps_per_epoch 必须是 ACCUM 的整数倍
# Phase 15: 4992 / 16 = 312 (整除 ✅)
# 尾部不整除的 microbatch 不存在 (Gemini FAIL 修正)
```

**OneCycleLR 精确计算**:
- optimizer_steps_per_epoch = 4992 / 16 = 312
- total_optimizer_steps = 312 × 15 = **4,680**
- OneCycleLR(total_steps=4680, pct_start=0.05, ...)
- warmup steps = 4680 × 0.05 = 234 optimizer steps = 234 × 16 = 3744 microbatches

### 1.4 EMA 实现 (Codex FAIL 修正)

**Codex 审计指出**: `AveragedModel()` 默认是等权 SWA，不是 EMA。`tau=0.999` 需要用 `get_ema_multi_avg_fn`。

**Gemini 审计指出**: EMA 期间应切换到低恒定 LR (SWALR)。

```python
from torch.optim.swa_utils import AveragedModel, get_ema_multi_avg_fn

# Phase 15: EMA (NOT plain SWA)
EMA_START_EPOCH = 10
EMA_DECAY = 0.999
EMA_LR = 3e-5  # SWALR: 低恒定 LR (Gemini 建议)

ema_model = AveragedModel(model, multi_avg_fn=get_ema_multi_avg_fn(EMA_DECAY))

for epoch in range(args.epochs):
    if epoch == EMA_START_EPOCH:
        # 切换 LR 调度器 (Gemini 建议)
        for pg in optimizer.param_groups:
            pg['lr'] = EMA_LR
        scheduler = None  # 停止 OneCycleLR, 用恒定 LR
        logger.info(f"EMA started: decay={EMA_DECAY}, LR={EMA_LR}")

    # ... 正常训练 ...

    if epoch >= EMA_START_EPOCH:
        ema_model.update_parameters(model)

# 训练结束保存 EMA 模型
# 注意: 无需 update_bn() — 模型只有 LayerNorm, 无 BatchNorm (Codex FAIL 修正)
ema_state = {k.replace("module.", ""): v for k, v in ema_model.state_dict().items()
             if not k.startswith("n_averaged")}
torch.save({"model_state_dict": ema_state, ...}, ema_path)
```

### 1.5 RPB 梯度监控 (Gemini 建议)

```python
# validate() 末尾新增
rpb_param = None
for name, param in model.named_parameters():
    if 'relative_position_bias_table' in name:
        rpb_param = param
        break
if rpb_param is not None and rpb_param.grad is not None:
    rpb_grad_norm = rpb_param.grad.norm().item()
    logger.info(f"RPB grad_norm={rpb_grad_norm:.6f}")
    # Phase 12 审计: RPB grad=0.08 vs decoder=4811 (60000x 弱)
    # Phase 15 预期: Pre-LN 修复后应显著改善
```

### 1.6 Vertex AI Job Config

```yaml
# gcp/phase15_step1_config.yaml (Codex FAIL 修正: 此文件必须创建)
workerPoolSpecs:
  - machineSpec:
      machineType: n1-standard-8
      acceleratorType: NVIDIA_TESLA_T4
      acceleratorCount: 1
    replicaCount: 1
    containerSpec:
      imageUri: gcr.io/gen-lang-client-0250995579/omega-tib:phase15-v1
      args:
        - --shard_dir=gs://omega-pure-data/wds_shards_v3_full
        - --output_dir=/gcs/omega-pure-data/checkpoints/phase15_step1
        - --epochs=15
        - --steps_per_epoch=4992
        - --batch_size=256
        - --lr=3e-4
        - --hidden_dim=64
        - --window_size_t=32
        - --window_size_s=10
        - --lambda_s=0
        - --mask_prob=0.0
        - --no_amp
        - --seed=42
        - --grad_accum=16
        - --ema_start_epoch=10
        - --ema_decay=0.999
        - --ema_lr=3e-5
        - --embargo_shards=2
        - --ckpt_every_n_steps=500
scheduling:
  strategy: ON_DEMAND
```

### 1.7 评估 spec

对照基线: Phase 13 E9 best Rank IC = +0.0292, 均值(E0-E14) ≈ +0.017

### 1.8 结果分支 (Codex FAIL 修正: 全区间覆盖, 无间隙)

设 EMA 模型的 Rank IC 为 `IC_ema`:

| IC_ema 区间 | 判定 | 下一步 |
|------------|------|--------|
| **> 0.040** | 🟢 训练噪声是主要瓶颈 | Step 2 (MLP) + Step 3 (hd), 用 Step 1 配置作新基线 |
| **0.030 ~ 0.040** | 🟡 训练有帮助但非唯一瓶颈 | Step 2 (MLP) 归因, 然后 Step 3 (hd) |
| **0.020 ~ 0.029** | 🟠 无明显改善，架构可能是瓶颈 | Step 2 (MLP), 跳过 Step 3, 直接 Step 4 (跨窗口) |
| **< 0.020** | 🔴 embargo gap 暴露数据泄漏 | **Phase 15 暂停**, 重新评估评估体系 |

**注意**: 0.029 边界属于 🟠 区间 (无改善)，不是 🟡。只有**严格超过** Phase 13 best 才算改善。

---

## Step 2: MLP Baseline [~6h T4]

### 2.1 目标

量化 FWT 拓扑注意力 + 信息瓶颈 + AttentionPooling 的增量贡献。

**注意** (Codex WARNING 修正): MLP 保留 SRL 物理层和 FRT 变换。这是有意设计——SRL/FRT 是特征工程层，不是模型架构。MLP 测量的是 "拓扑归纳偏置的增量"，不是 "整个 OMEGA 管线的增量"。

### 2.2 MLP 架构

```python
class MLPBaseline(nn.Module):
    """Phase 15 Step 2: 同 FRT+SRL 输入, 无拓扑结构, ~5M 参数."""
    def __init__(self, input_dim=9600, hidden_dims=[512, 128]):
        super().__init__()
        self.norm = nn.LayerNorm(input_dim)
        layers = []
        prev = input_dim
        for h in hidden_dims:
            layers.extend([nn.Linear(prev, h), nn.GELU()])
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.mlp = nn.Sequential(*layers)

    def forward(self, x_2d, c_friction):
        # x_2d 已经过 OmegaTIBWithMasking 的 FRT+SRL 处理
        # 取 6 维流形 [B, T, S, 6], flatten
        B = x_2d.shape[0]
        flat = x_2d[:, :, :, :6].reshape(B, -1)  # [B, 160*10*6=9600]
        flat = self.norm(flat)
        pred = self.mlp(flat)
        dummy_z = torch.zeros(B, 1, 1, 1, device=pred.device)  # 接口兼容
        return pred, dummy_z
```

**代码实施**: 在 `train.py` 添加 `--model_type` 参数 (`omega` / `mlp`)，根据选择实例化不同模型。

### 2.3 训练配置

与 Step 1 完全相同 (grad_accum=16, EMA, embargo)。唯一改 `--model_type=mlp`。

### 2.4 结果分支 (Codex FAIL 修正: 全区间覆盖)

设 Step 1 的 IC 为 `IC_omega`，MLP 的 IC 为 `IC_mlp`:

| IC_mlp / IC_omega 比率 | 判定 | 行动 |
|------------------------|------|------|
| **< 30%** | 🟢 OMEGA 拓扑贡献 >70% | 全力优化 FWT → Step 3 + Step 4 |
| **30% ~ 60%** | 🟡 拓扑有价值但非压倒性 | 优化架构 + 特征双线并行 |
| **60% ~ 85%** | 🟠 拓扑贡献有限 | 优先特征工程，架构优化降优先级 |
| **> 85%** | 🔴 拓扑几乎无增量 | **战略转向**: 停架构，转特征/数据 |

---

## Step 3: 容量对比 hd=64 vs 128 [~25h T4]

### 3.1 前提

Step 1 IC ≥ 0.020 且 Step 2 MLP < 60% Omega 时执行。否则跳过。

### 3.2 配置 (Gemini 建议修正: 多种子)

3 个 seed × 2 个 hd = 6 个 Job:
- hd=64, seed={42, 123, 456}
- hd=128, seed={42, 123, 456}

每个 Job 跑 8 epoch (非完整 15，节省预算)。用 EMA 在最后 3 epoch 平均。

hd=128 参数量: ~82K (vs 24.6K, 3.3x)。仍是极小模型。

### 3.3 结果分支

比较 3-seed 均值和标准差:

| 结果 | 判定 | 行动 |
|------|------|------|
| mean(IC_128) > mean(IC_64) + 1 × pooled_std | 🟢 统计显著，容量是瓶颈 | 后续全用 hd=128 |
| 差距 < 1 × pooled_std | 🟡 差异不显著，容量非主要瓶颈 | 保持 hd=64, 进 Step 4 |
| mean(IC_128) < mean(IC_64) | 🟠 更大模型在噪声中更差 | 保持 hd=64, 考虑 dropout |

---

## Step 4: 跨窗口通信 [~16h T4]

### 4.1 前提

Step 1-3 选出最优基线后执行。

### 4.2 Overlapping Windows

stride_t = window_t // 2 = 16。窗口数从 5 → 9。

**输出合并策略** (Codex WARNING 修正):

每个 bar 出现在 2 个窗口中，产生 2 个输出向量。合并方式: **取平均**。

```python
# FiniteWindowTopologicalAttention.forward() 修改
def forward(self, x_nd, overlap=False):
    B, T, S, D = x_nd.shape
    if not overlap:
        # ... 原始不重叠路径 (不改) ...
        return out

    # Overlapping: stride = window_t // 2
    stride_t = self.window_t // 2
    pad_t = (self.window_t - T % stride_t) % stride_t  # 确保能整除 stride
    if pad_t > 0:
        x_nd = F.pad(x_nd, (0, 0, 0, 0, 0, pad_t))
    T_pad = x_nd.shape[1]

    # 收集每个 bar 的输出和计数
    output_sum = torch.zeros(B, T_pad, S, D, device=x_nd.device)
    output_count = torch.zeros(B, T_pad, 1, 1, device=x_nd.device)

    for win_start in range(0, T_pad - self.window_t + 1, stride_t):
        win_end = win_start + self.window_t
        x_win = x_nd[:, win_start:win_end, :, :]  # [B, wt, S, D]

        # 空间分割 + 注意力 (复用现有逻辑)
        x_win_flat = x_win.view(B, 1, self.window_t, 1, S, D)
        x_win_flat = x_win_flat.permute(0, 1, 3, 2, 4, 5).contiguous()
        x_win_flat = x_win_flat.view(-1, self.window_t * S, D)
        # ... QKV + RPB + softmax + proj (同现有代码) ...
        out_win = self._attention_block(x_win_flat)  # 抽出为方法
        out_win = out_win.view(B, self.window_t, S, D)

        output_sum[:, win_start:win_end, :, :] += out_win
        output_count[:, win_start:win_end, :, :] += 1

    # 平均合并
    output = output_sum / output_count.clamp(min=1)
    output = output[:, :T, :S, :].contiguous()  # 去 padding
    return output
```

**RPB 兼容性** (Codex WARNING 确认): RPB 表由 (window_t, window_s) 定义，与窗口数量和重叠无关。每个窗口内部仍然是 32×10 的相对位置编码。✅ 兼容。

### 4.3 多种子 (Gemini 建议)

seed={42, 123, 456}，比较 3-seed 均值。

### 4.4 结果分支

| 结果 | 判定 | 行动 |
|------|------|------|
| mean(IC_overlap) > mean(IC_baseline) + 1 × pooled_std | 🟢 跨窗口释放新信号 | Phase 16: Swin shifted window 2 层 |
| 差距不显著 | 🟡 重叠不够，需更激进方案 | Phase 16: Swin 2 层 |
| IC_overlap 更差 | 🔴 计算翻倍无改善 | 问题不在感受野，转 Loss 优化 |

---

## 全局决策树 (Codex FAIL 修正: 全区间, 无矛盾)

```
Step 0: Shard 时序验证
  ├─ ❌ 无序 → STOP, 重建数据
  ├─ ⚠️ 无 date 字段 → 加 embargo gap 作保守措施, 继续
  └─ ✅ 有序 → Step 1

Step 1: 训练稳定化 (grad_accum=16 + EMA + embargo)
  ├─ 🔴 IC < 0.020 → STOP, 数据泄漏
  ├─ 🟠 IC 0.020~0.029 → Step 2 (MLP), 跳 Step 3, 直接 Step 4
  ├─ 🟡 IC 0.030~0.040 → Step 2 (MLP), 再 Step 3 (hd)
  └─ 🟢 IC > 0.040 → Step 2 (MLP), 再 Step 3 (hd)

Step 2: MLP Baseline (任何 Step 1 非 🔴 结果都执行)
  ├─ 🔴 MLP > 85% Omega → 战略转向特征
  ├─ 🟠 MLP 60~85% Omega → 双线, 架构降优先级
  ├─ 🟡 MLP 30~60% Omega → 双线并行
  └─ 🟢 MLP < 30% Omega → 全力架构优化

Step 3: hd=64 vs 128 (仅 Step 1 🟡/🟢 且 Step 2 非 🔴🟠 时执行)
  ├─ 🟢 128 显著优于 64 → 后续用 hd=128
  └─ 🟡 无显著差异 → 保持 hd=64

Step 4: Overlapping Windows (Step 1-3 最优基线确定后执行)
  ├─ 🟢 显著改善 → Phase 16: Swin 2 层
  ├─ 🟡 不够 → Phase 16: Swin 2 层 (更激进)
  └─ 🔴 更差 → 转 Loss 优化
```

---

## 实施清单 (代码/文件同步)

### 必须在 Step 1 提交前完成 (Codex FAIL 修正):

- [ ] `train.py` + `gcp/train.py` 添加: `--grad_accum`, `--ema_start_epoch`, `--ema_decay`, `--ema_lr`, `--embargo_shards`, `--model_type`
- [ ] `train.py` 修改训练循环: accumulation + EMA + SWALR 切换 + RPB 监控
- [ ] `gcp/phase15_step1_config.yaml` 创建 (上面 §1.6)
- [ ] `architect/current_spec.yaml` 更新 Phase 15 新参数
- [ ] `gcp/train.py` 与 `train.py` 同步 (safe_build_and_canary.sh Step 1b 会检查)
- [ ] Docker `phase15-v1` 构建 + canary
- [ ] Codex 代码审计 (编码完成后)

---

## Spec 变更 (architect/current_spec.yaml 新增)

```yaml
# ============================================================
# Phase 15 Training Stabilization (2026-04-06, Codex+Gemini audited V2)
# ============================================================
phase15:
  gradient_accumulation: 16       # 有效 batch = 256 × 16 = 4096
  steps_per_epoch: 4992           # = 312 × 16 (整除, Gemini FAIL 修正)
  total_optimizer_steps: 4680     # = 312 × 15 epochs
  ema:
    enabled: true
    start_epoch: 10               # 最后 5 epoch EMA
    decay: 0.999                  # 指数移动平均衰减率
    lr_after_start: 3e-5          # SWALR: EMA 启动后切恒定低 LR (Gemini)
    # 注意: 使用 get_ema_multi_avg_fn(0.999), 非默认 AveragedModel (Codex FAIL)
    # 注意: 无需 update_bn() — 模型只有 LayerNorm (Codex FAIL)
  embargo_shards: 2               # train/val 边界隔离
  evaluation: "global Spearman Rank IC"  # v3 shards 无 date 字段, 不用 per-date
  monitoring:
    rpb_grad_norm: true           # Gemini 建议: 每 epoch 记录 RPB 梯度范数
```

---

## 时间线

```
Day 0 (今天):
  [0-2h]  Step 0: shard 验证 + embargo 代码
  [2-4h]  编码 grad_accum + EMA + model_type
  [4-5h]  Docker build + canary
  [5-6h]  Codex 代码审计

Day 1:
  [0h]    提交 Step 1 Job (T4 ON_DEMAND, ~10.5h)
  [10.5h] Step 1 结果 → GO/NO-GO

Day 2:
  [0h]    提交 Step 2 MLP (T4, ~6h)
  [6h]    MLP 结果 → 归因判定
  [7h]    如需: 提交 Step 3 × 6 Jobs (3 seed × 2 hd, 各 8 epoch)

Day 3-4:
  [0h]    Step 3 结果 → 容量判定
  [1h]    提交 Step 4 × 3 Jobs (3 seed, overlapping)
  [17h]   Step 4 结果 → Phase 15 完成

同时: ETL v5 Sort → ETL v5 Pipeline → 为 Phase 16 准备数据
```

---

*[V2 — Codex 5-FAIL + Gemini 1-FAIL 全部修正, 2026-04-06]*
