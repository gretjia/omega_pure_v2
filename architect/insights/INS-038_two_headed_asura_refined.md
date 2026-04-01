---
id: INS-038
title: 双头阿修罗 V2 — Long Head (Softmax) + Veto Head (BCE) 精炼架构
category: architecture
date: 2026-03-31
axiom_impact: UPDATE_REQUIRED
status: pending_p0_backtest
source_directive: post_phase10_three_campaigns
source_gdoc: null
---

# INS-038: 双头阿修罗 V2 — Long Head (Softmax) + Veto Head (BCE) 精炼架构

## 裁决

在 P0 回测确认 Asymmetry Ratio 依然死锁 ~1.2 后启动。INS-029 的 Path B 概念升级为具体可实现的双头架构：共享物理层 + 双 z_core + 专职损失函数 + 一票否决机制。

## 与 INS-029 的关系

INS-029 提出了两条路径的概念框架（Path A: 非对称目标截断 vs Path B: 双头阿修罗）。Phase 9 的 7 jobs 全败已宣判 Path A 死刑（非对称 Pearson Reward Hacking，INS-032/035）。本洞察是 Path B 的精炼工程规范。

## 架构规范

### 共享层（不变）
- Layer 1: AxiomaticSRLInverter（SRL 物理反演，c_friction per-stock）
- Layer 2: FiniteWindowTopologicalAttention（2D FWT 拓扑注意力）

### 分裂点：信息瓶颈处

原架构:
```
[共享层] → EpiplexityBottleneck(dim→dim/2→dim/4) → z_core(hd=64) → IntentDecoder → scalar
```

新架构:
```
[共享层] → ┬─ EpiplexityBottleneck_Long(dim→dim/2→dim/4) → z_long(hd=32) → LongHead → scalar (alpha signal)
           └─ EpiplexityBottleneck_Veto(dim→dim/2→dim/4) → z_veto(hd=32) → VetoHead → sigmoid (crash probability)
```

### Long Head（The Bull Detector）
- **任务**: 专职学习胜率极低但赔率极高的主升浪建仓信号
- **损失**: Softmax Portfolio Loss（Phase 10 验证有效）
- **z_long**: hd=32, L1 MDL 正则化
- **输出**: 截面 alpha 预测值

### Veto Head（The Crash Detector）
- **任务**: 专职学习规避主力出货和崩盘黑洞
- **损失**: Binary Cross-Entropy（target: 1 if T+1 return < -500 BP, else 0）
- **z_veto**: hd=32, L1 MDL 正则化
- **输出**: 崩盘概率 p_crash ∈ [0, 1]
- **阈值**: -500 BP（~5% 跌幅，主板半个跌停板）

### 实盘执行机制

```python
alpha_signal = long_head(shared_features)   # 截面 alpha
crash_prob = veto_head(shared_features)      # 崩盘概率

# 一票否决权
if crash_prob > VETO_THRESHOLD:
    position = 0  # 强制拒绝开仓，不管 alpha 多强
else:
    position = portfolio_allocate(alpha_signal)
```

## 物理直觉

在 A 股高度不对称的市场机制下，单一 z_core 无法同时编码：
- "贪婪模式"：低熵、可压缩的主力建仓拉升特征
- "恐惧模式"：高熵、不可压缩的主力出货派发特征

这是 INS-028（压缩悖论）的建筑学解决方案：用两个独立的信息瓶颈分别处理两种截然相反的物理模式，避免任务坍塌。

## 影响文件

- `omega_epiplexity_plus_core.py`: 重大重构 — 双 EpiplexityBottleneck + 双 Head
- `train.py`: 双损失函数加权训练
- `architect/current_spec.yaml`: 模型架构全面更新
- 推理脚本: 双输出处理逻辑
- 模拟器: 加入 veto 过滤逻辑
