---
id: INS-074
title: "No-Retreat Decision Matrix — Phase 13 结果解读框架 + Phase 14 不可撤销"
category: metrics
date: 2026-04-04
axiom_impact: NONE
status: active
audit_status: final
source_directive: "2026-04-04_phase13_bag_of_windows_and_no_retreat_matrix.md"
source_gdoc: null
---

# INS-074: No-Retreat Decision Matrix — Phase 13 结果解读 + Phase 14 锁定

## 裁决
Phase 13 的 per-date Rank IC 必须按三级阈值解读，严禁因 Rank IC ≈ 0 就宣判方法论死刑。当前架构是"时间词袋模型"（Bag-of-Windows），0.64 天隔离窗口物理上无法捕获多日建仓因果序列。Phase 14（Cross-Window Attention）无论 Phase 13 结果如何都是不可撤销的必选行动（除非深度倒挂）。

## 理由
- **Bag-of-Windows 物理诊断**：5 个 32-bar 窗口互不通信。AttentionPooling 是加权求和 sum(α_i × h_i)，只能检测特征存在性（"窗口 1 和窗口 5 都有异常摩擦"），无法理解因果时序（"窗口 1 在窗口 5 之前"）
- **归因纯洁性**：Phase 13 同时修了 5 个变量（Loss/Target/Pooling/Residual/Regularization），如果再加跨窗口注意力（第 6 个），归因爆炸
- **核心洞察对齐**：用户的核心假说是 T+1 多日建仓流动性痕迹，0.64 天感受野注定是不完整的测量工具

## 解读矩阵（架构师裁决，带具体阈值）

| Phase 13 Per-date Rank IC | 定性 | 行动 |
|---|---|---|
| **> +0.015** | 意外的狂喜 — 日内碎片够预测 T+1 | 引擎点火，Phase 14 乘数放大 |
| **± 0.005** | 符合物理预期的假阴性 — 0.64天不够 | **不准退缩，强制 Phase 14** |
| **< -0.015** | 均值回归陷阱 — 短期冲击→次日反转 | 危险信号：审查 FRT 或翻转交易逻辑 |

## 前提假设
- **物理假设**：多日建仓信号在 0.64 天窗口内仅部分可见（特征存在性可检测，因果轨迹不可检测）
- **上游依赖**：INS-073（Phase 13 scope = intraday），INS-070（Phase 14 = cross-window attention）
- **阈值来源**：±0.015 和 ±0.005 为架构师直觉，待 Phase 13 Post-Flight 实测校准

## 被拒绝的替代方案
- **方案 B**: Phase 13 Rank IC ≈ 0 → 宣判 OMEGA 死刑 → 拒绝原因：用残缺尺子测量完整因果，零结果不代表信号不存在
- **方案 C**: Phase 13 直接加跨窗口注意力 → 拒绝原因：归因灾难（INS-073 控制变量法）

## 验证协议
1. Phase 13 Post-Flight 计算 per-date Rank IC（依赖 ETL v4 date 字段）
2. 按矩阵三级阈值分类结果
3. 如果 Rank IC ∈ [-0.015, +0.015] → 自动触发 Phase 14 规划（不等架构师额外授权）

## 参数标定来源
- 🎯 **架构师直觉**: ±0.015 / ±0.005 阈值 — **待 Phase 13 实测标定**
- 📐 **理论推导**: Bag-of-Windows 无法学跨窗因果 — 来自加权求和的交换律数学性质

## 影响文件
- 无代码变更（纯解读框架）
- `handover/LATEST.md`: Post-Flight 时按此矩阵解读

## spec 参数映射
- `spec.hpo.success_criterion` → 此矩阵为其具体化补充（阈值 + 行动映射）
