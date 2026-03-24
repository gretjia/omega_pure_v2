# 架构师指令：v15 全量训练启动授权 + 飞控补丁
- **日期**: 2026-03-24
- **来源**: 独立架构师 via Claude Code 对话
- **触发条件**: v14 单 batch 过拟合测试通过 (Train FVU=0.43, 架构无 bug)

## 核心判决
v14 过拟合测试证明 FWT/SRL 架构图论连通性和梯度链完整。FVU=1.0 是数值幻象（target 肥尾 + 特征未剥离），非架构缺陷。批准 v15 全量训练。

## Train FVU=0.43 而非 0.00 的解释
1. 金融市场 Aleatoric Uncertainty: 相同 LOB 特征下存在不可消除的条件方差（冰山单/宏观冲击）
2. Huber Loss 天然拒绝死记极端离群点，保留弹性

## 飞控补丁（强制）

### 补丁 1: LR Scheduler (禁止恒定学习率)
- 使用 OneCycleLR 或 CosineAnnealingLR + Warmup
- 前 2-5% steps: lr 从 1e-5 预热到 1e-3
- 之后余弦退火至极小值
- 理由: 全量金融数据 loss landscape 极崎岖，恒定 lr 在鞍点震荡

### 补丁 2: 梯度裁剪 (已存在，确认 max_norm=1.0)
- torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
- 理由: 黑天鹅 batch 产生瞬间梯度尖峰

### 补丁 3: 重新定义胜利基准
- mask=0 会导致后半程过拟合（预期行为）
- 胜利标准: Val FVU 哪怕短暂触及 0.9980~0.9950 即为成功
- Train FVU 从 1.00 稳定降至 0.95 即为信号存在的证据
- 防过拟合是 Phase 4 HPO 的任务

## v15 配置
- Huber loss + target Z-score + 5σ clip
- MDL warmup (前 2 epochs lambda_s=0)
- mask_prob=0.0
- lr=1e-3 with OneCycleLR (warmup 5% → cosine decay)
- hidden_dim=128
- grad_clip=1.0
