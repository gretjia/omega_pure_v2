# 架构师洞察索引

本目录存储从架构师裁决中提炼的、可独立查询的结构化洞察。每个洞察是一个原子化的设计决策记录。

**与 `directives/` 的区别**：directives 是原始归档（完整原文，不可压缩）；insights 是从中提炼的结构化决策卡片（可快速检索、交叉引用）。

---

## 洞察列表

| ID | 主题 | 类别 | 日期 | 公理层 | 状态 |
|----|------|------|------|--------|------|
| INS-001 | Omega-TIB 架构正名 | 命名 | 2026-03-18 | — | 已生效 |
| INS-002 | V_D/σ_D 宏观物理量纲 | 物理 | 2026-03-18 | L2 更新 | 已实现 |
| INS-003 | N+1 VWAP 延迟执行目标 | 物理/ETL | 2026-03-18 | L2 更新 | 已实现 |
| INS-004 | Block-wise 因果输入遮蔽 | 训练 | 2026-03-18 | — | 待实现 (train.py) |
| INS-005 | SRL c 摩擦系数特异性标定 | 物理/公理 | 2026-03-18 | L1→L2 降级 | 已实现 |
| INS-006 | 空间轴恢复 [T,S,F] 四维 | 架构 | 2026-03-18 | L2 更新 | 已实现 |
| INS-007 | 相对容量时钟 (动态阈值) | 架构 | 2026-03-18 | L2 更新 | 已实现 |
| INS-008 | FVU 为 HPO 最高准则 | 度量 | 2026-03-18 | — | 待实现 (train.py) |
| INS-009 | 均值坍缩修复: Huber+TargetNorm+MDL Warmup | 训练 | 2026-03-24 | L2 更新 | 待确认 |
| INS-010 | payoff_horizon 锁定, 禁入 HPO | 度量 | 2026-03-24 | L2 更新 | 待确认 |
| INS-011 | 严格日内回测, 禁止 T+1 隔夜 | 架构 | 2026-03-24 | L2 更新 | 待确认 |
| INS-012 | MDL 断头台 — λ_s=0.001 绞杀微弱 Alpha | 训练 | 2026-03-25 | L2 更新 | 已生效 |
| INS-013 | Phase 4 HPO 搜索空间 — 六维拓扑共振搜索 | 训练 | 2026-03-25 | L2 更新 | 被 INS-014 取代 |
| INS-014 | 时间膨胀器回归 — coarse_graining 作为 P0 搜索参数 | 架构 | 2026-03-25 | L2 更新 | 待确认 |

---

## 来源追溯

| 洞察 | 源 directive | 源 gdoc |
|------|-------------|---------|
| INS-001 | v3_full_design_audit | id5 |
| INS-002 | v3_full_design_audit | id6 |
| INS-003 | v3_full_design_audit | id5 |
| INS-004 | v3_full_design_audit | id5 |
| INS-005 | v3_full_design_audit | id4 |
| INS-006 | v3_spatial_restoration | — |
| INS-007 | v3_spatial_restoration | — |
| INS-008 | v3_full_design_audit | id5 |
| INS-009 | mean_collapse_diagnosis | — |
| INS-010 | mean_collapse_diagnosis | — |
| INS-011 | mean_collapse_diagnosis | — |
| INS-012 | phase4_hpo_authorization | — |
| INS-013 | phase4_hpo_authorization | — |
| INS-014 | phase4_ashare_swing_tracker | — |
