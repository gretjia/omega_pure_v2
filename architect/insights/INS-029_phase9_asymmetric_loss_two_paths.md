---
id: INS-029
title: Phase 9 两条路径 — 非对称目标截断 vs 双头阿修罗
category: architecture
date: 2026-03-30
axiom_impact: UPDATE_REQUIRED
status: pending_phase9
source_directive: 2026-03-30_compression_paradox_asymmetric_evolution.md
source_gdoc: null
---

# INS-029: Phase 9 两条路径 — 非对称目标截断 vs 双头阿修罗

## 裁决
Phase 9 "非对称重构" 有两条候选路径，Phase 8 完成后择优执行：

**路径 A: Asymmetric Target Masking (低成本)**
- 保留 T29 架构不变
- `target_long_only = torch.clamp(target_cs_z, min=0.0)` 单侧 ReLU 截断
- 让高熵派发噪音对梯度零贡献
- 预期效果：64 维全部变异为"建仓探测器"

**路径 B: Two-Headed Asura (高成本)**
- 底层 SRL + FWT 共享权重
- 分叉两个 Epiplexity 窄门：多头 hd=32 (买入信号) + 空头 hd=32 (风控否决)
- 空头雷达报警时一票否决多头买入
- 参数量不变 (19.7K)

架构师建议先试路径 A（最低成本），效果不佳再切路径 B。

## 理由
- 路径 A 只需修改 1 行 loss 代码，训练成本与 Phase 6 HPO 相同
- 路径 B 需要架构变更 + 重新 HPO，成本高但理论上更优
- 必须在 Phase 8 建立修正后的 simulate baseline 之后才能公正评估

## 影响文件
- `train.py`: loss function 修改 (路径 A) 或架构分叉 (路径 B)
- `omega_epiplexity_plus_core.py`: 路径 B 需双头 EpiplexityBottleneck
- `architect/current_spec.yaml`: Phase 9 时更新 training.loss 和 model_architecture
