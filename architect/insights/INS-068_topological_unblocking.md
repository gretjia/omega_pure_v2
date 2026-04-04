---
id: INS-068
title: "Topological Unblocking — 残差连接 + RPB 修复 + 池化替换"
category: architecture
date: 2026-04-04
axiom_impact: UPDATE_REQUIRED
status: active
audit_status: draft
source_directive: "2026-04-04_phase13_audit_verdict_and_roadmap.md"
source_gdoc: null
---

# INS-068: Topological Unblocking (三项架构修复)

## 裁决
三项并行修复：(1) TDA 层加残差连接，(2) 修复或替换 RPB 位置编码，(3) 替换 Global Mean Pooling。

## 理由

### 残差连接
当前 `structured = tda(x)` 直接替换输入。标准 Transformer 用 `out = x + attention(x)`。缺少残差意味着模型必须通过 attention 学恒等映射才能保留原始特征，浪费有限容量。

### RPB 梯度极弱
Vertex AI 实测：RPB grad_norm=0.08 vs decoder grad_norm=4811（弱 60,000x）。4,788 参数（模型 20%）形同虚设。可能原因：(1) grad 通过 softmax 后衰减，(2) mean pooling 抹平了位置信息导致无梯度信号。

### Global Mean Pooling
[B, 160, 10, 16] → mean → [B, 16]。1,600 个 token 压成 16 个均值。两路 Codex + Gemini 一致判 CRITICAL。替换方案：Attention Pooling / [CLS] token / Flatten+Linear。

## 前提假设
- **数据格式**: 输入 [B, 160, 10, 10]，bottleneck 输出 [B, 160, 10, 16]
- **上游依赖**: 与 IC Loss (INS-066) 联合执行效果最佳
- **环境假设**: 参数量会增加（attention pooling 新增 ~1K params），仍在 25-30K 范围

## 被拒绝的替代方案
- **方案 D (暂不改)**: Phase 6 同架构 IC=0.066 → 部分合理，但 pooling 在 MSE 下完全失效，且 IC Loss 下也是信息损失。不改是可接受的保守选项，但长期受限

## 验证协议 (V2 更新: 64-sample Crucible Overfit Test)
1. 验证命令: 64-sample Crucible Overfit Test — 加残差+池化替换后 overfit 64 个样本
2. 预期结果: **Loss 达到绝对 0.0**，证明 RPB 梯度复活、物理信息瓶颈已清除
3. 失败回退: 逐项回退（先只加残差，再加池化替换）
4. 注意: V2 directive 指定 Post-LN `x = LayerNorm(x + tda(x))`，但 Codex+Gemini 审计选择了 Pre-LN `x + tda(LayerNorm(x))`。**保持 spec [FINAL] Pre-LN 选择**，因为 Gemini 证明 Pre-LN 防止残差流方差爆炸

## 参数标定来源
- 📐 **理论推导**: Swin Transformer 标准做法（残差 + shifted window）
- 🎯 **架构师直觉**: Attention Pooling vs CLS token 待 A/B test

## 影响文件
- `omega_epiplexity_plus_core.py`: TDA forward 加 `+ x` 残差；新增 AttentionPooling 类
- `train.py`: OmegaTIBWithMasking forward 同步修改
- `backtest_5a.py` / `gcp/phase7_inference.py`: 推理 wrapper 同步
- `architect/current_spec.yaml`: 更新 model_architecture 描述

## spec 参数映射
- `spec.model_architecture.layer_2_topology` → 加 "with residual connection"
- `spec.model_architecture` → 新增 "attention_pooling" 或 "cls_token"
