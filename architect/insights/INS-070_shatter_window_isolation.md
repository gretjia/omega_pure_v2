---
id: INS-070
title: "Shatter Window Isolation — 跨窗注意力打破 0.64 天感受野限制"
category: architecture
date: 2026-04-04
axiom_impact: UPDATE_REQUIRED
status: active
audit_status: draft
source_directive: "2026-04-04_phase13_audit_verdict_and_roadmap_v2.md"
source_gdoc: null
---

# INS-070: Shatter Window Isolation (跨窗注意力)

## 裁决
当前 5 个隔离的 32-bar 窗口将模型感受野限制在 0.64 天内。必须实现跨窗注意力或滑动窗口重叠，允许模型看到跨越多个窗口的建仓模式。

## 理由
外部审计 V2 新增 Mandate B.3：主力机构建仓周期通常跨越多天。5 个独立的 32-bar 窗口（每窗口 ~0.64 天 = 32 bars × 2%ADV / 50 bars/day）之间无信息流通，模型无法检测跨窗口的渐进建仓信号。这是信息瓶颈的一部分——与 GMP (INS-068) 和缺失残差 (INS-068) 共同限制了拓扑信息流。

数学：`window_size=160, window_size_t=32` → 160/32 = 5 windows × 10 spatial = 50 tokens/window。窗口间完全隔离 = 无法学习跨窗口时间模式。

## 前提假设
- **数据格式**: 输入 [B, 160, 10, F]，TDA 将其分为 5 个 [B, 32, 10, F] 窗口
- **上游依赖**: 与 INS-068 (残差+池化) 联合实施效果最佳；与 IC Loss (INS-066) 独立
- **环境假设**: 跨窗口注意力会增加 O(n²) 复杂度。160×10=1600 tokens 的 full attention 可能 OOM on 24.4K 模型。需要 Swin-style shifted window 而非 full cross-attention
- **HPO 影响**: `window_size_t` 当前在 HPO 搜索空间 [8, 16, 32]。如果实现跨窗注意力，可能需要重新评估此参数

## 被拒绝的替代方案
- **方案 B**: Full global attention (所有 1600 tokens) → 拒绝: O(1600²) = 2.56M attention scores，24.4K 模型无法承受
- **方案 C**: 仅增大 window_size_t (如 64 或 160) → 拒绝: 减少窗口数但增大每窗复杂度，不解决边界截断问题
- **方案 D**: 不改（先验证 IC Loss + 残差 + 池化的效果） → 可接受的保守选项，但审计明确要求

## 验证协议
1. 验证命令: 实施后跑 64-sample Crucible Overfit Test (INS-068 定义)
2. 预期结果: 如果窗口隔离是瓶颈之一，overfit 速度应加快
3. 失败回退: 如果 OOM 或训练变慢，先只做 shifted window (相邻窗口重叠 50%)

## 参数标定来源
- 📐 **理论推导**: Swin Transformer shifted window attention (Liu et al. 2021)
- 🎯 **架构师直觉**: "跨窗注意力或滑动窗口" — **待实测标定** 具体方案

## 影响文件
- `omega_epiplexity_plus_core.py`: `FiniteWindowTopologicalAttention` 的窗口分割逻辑
- `train.py`: 可能需要新超参 `--cross_window` 或修改 `--window_size_t` 语义
- `architect/current_spec.yaml`: 更新 `model_architecture.layer_2_topology` 描述

## spec 参数映射
- `spec.model_architecture.layer_2_topology` → 加 "cross-window attention" 或 "shifted window"
- `spec.hpo.search_space.window_size_t` → 可能需要重新评估搜索范围
