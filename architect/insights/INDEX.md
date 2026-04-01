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
| INS-014 | 时间膨胀器回归 — coarse_graining 作为 P0 搜索参数 | 架构 | 2026-03-25 | L2 更新 | **被 INS-016 取代** |
| INS-015 | 贝叶斯火力侦察 30+70 — 算力凯利公式 | 训练 | 2026-03-26 | L2 更新 | 已生效 |
| INS-016 | cg 微观结构保护 — Volume-Clock 不可二次粗粒化 | 物理 | 2026-03-26 | L2 更新 | 已生效 |
| INS-017 | 先锋定标战役 — T16 全量收敛 + Std(ŷ) 截面监控 | 训练 | 2026-03-27 | NONE | **完成: FAIL** |
| INS-018 | 横截面相对论 — MSE→IC Loss + 绝对收益→截面Z-score | 训练 | 2026-03-28 | L2 更新 | 待确认 |
| INS-019 | 隐式压缩胜利 — hd=64 物理瓶颈 >> λ_s 显式惩罚 | 架构 | 2026-03-29 | NONE | 已生效 |
| INS-020 | 大统一因果链 — SRL→Topology→Entropy→Epiplexity | 物理 | 2026-03-29 | NONE | 已生效 |
| INS-021 | INS-011 废弃 — 日内约束→中长期波段 (Swing Trading) | 架构 | 2026-03-29 | L2 更新 | **时间尺度被 INS-022 修正** |
| INS-022 | 时空换算修正 — 20 bars = 0.4 天，非"数天到数周" | 物理 | 2026-03-29 | L2 更新 | 待确认 |
| INS-023 | T+1 模拟三铁律 — 物理锁 + 涨停买不进 + 跌停卖不出 | 架构 | 2026-03-29 | L2 更新 | 待确认 |
| INS-024 | 绝对零过拟合认证 — OOS/IS IC = 1.00 | 度量 | 2026-03-30 | NONE | 已生效 |
| INS-025 | 对称 Loss 的数学诅咒 — 模型退化为波动率雷达 | 训练 | 2026-03-30 | NONE | Phase 9 待处理 |
| INS-026 | 确信度过滤 — |pred-median|>30 BP 时 IC 翻倍至 0.054 | 架构 | 2026-03-30 | L2 更新 | Phase 8 待实装 |
| INS-027 | 宏观气候雷达 — 熊市 IC≈0 时强制减仓 | 架构 | 2026-03-30 | L2 更新 | Phase 8 待实装 |
| INS-028 | 压缩悖论 — 建仓=低熵可压缩，派发=高熵不可压缩 | 物理 | 2026-03-30 | NONE | Phase 9 封印 |
| INS-029 | Phase 9 两条路径 — 非对称目标截断 vs 双头阿修罗 | 架构 | 2026-03-30 | L2 更新 | Phase 9 封印 |
| INS-030 | Leaky Asymmetric Pearson Loss — downside_dampening=0.05 | 训练 | 2026-03-30 | L2 更新 | Phase 9 待执行 |
| INS-031 | Vanguard V3 Protocol — 锁死底盘换发引擎 | 训练 | 2026-03-30 | NONE | Phase 9 待执行 |
| INS-032 | Pearson 尺度免疫漏洞 — 非对称 dampening 诱导 Reward Hacking | 训练 | 2026-03-30 | NONE | 已生效 |
| INS-033 | Softmax Portfolio Loss — 从统计相关性到交易逻辑的范式跃迁 | 训练 | 2026-03-30 | L2 更新 | 待用户确认 |
| INS-034 | z_sparsity 作为交易扳机 — 高压缩率 = 主力控盘铁证 | 架构 | 2026-03-30 | NONE | 待实现 |
| INS-035 | Phase 9 非对称 Pearson Loss 终极验尸 — 7 jobs 全败 | 训练 | 2026-03-30 | NONE | 已生效 |
| INS-036 | Softmax 尺度失控 — 方差惩罚或 Logits LayerNorm 物理锁 | 训练 | 2026-03-31 | L2 更新 | 待 P0 回测 |
| INS-037 | P0 物理熔炉协议 — 回测先行，代码冻结 | 度量 | 2026-03-31 | NONE | 执行中 |
| INS-038 | 双头阿修罗 V2 — Long Head (Softmax) + Veto Head (BCE) | 架构 | 2026-03-31 | L2 更新 | **推迟到 Phase 12** |
| INS-039 | Epiplexity Gating — z_sparsity 认知门控, 剥夺高熵赌徒 | 架构 | 2026-03-31 | L2 更新 | **FAILED (P0 negative)** |
| INS-040 | 方差之枷 — 截面 Z-score 锁死 Std=1.0 (**取代 INS-036**) | 训练 | 2026-03-31 | L2 更新 | 待 P0 Gating 回测 |
| INS-041 | 压缩即智能实证定律 — 低压缩=负IC (Phase 10 实证) | 物理 | 2026-03-31 | NONE | 已生效 |
| INS-042 | 非对称目标遮蔽 — clamp(target,min=0) 纯建仓检测 | 训练 | 2026-03-31 | L2 更新 | 待 P0 Gating 回测 |
| INS-043 | 建仓 Epiplexity Loss — 交叉熵 + 右尾目标 + MDL | 训练 | 2026-03-31 | L2 更新 | 待 P0 Gating 回测 |
| INS-044 | Spear-First 策略 — 单头建仓优先, Shield 推迟 Phase 12 | 架构 | 2026-03-31 | NONE | 已生效 |
| INS-045 | P0 终极判决 — Casino Exploit 确认, T=0.1 | 训练 | 2026-03-31 | L2 更新 | **T=0.1 被 INS-047 修正为 0.5** |
| INS-046 | 勾股漂移 — Z-score 仿射不变性导致 S_T 爆炸 | 物理 | 2026-04-01 | NONE | 已生效 |
| INS-047 | Detached Straitjacket — detach(std) 斩断仿射黑洞 | 训练 | 2026-04-01 | L2 更新 | 待 Phase 11b |
| INS-048 | λ_s 动态引力重构 — 1e-7→2e-5 匹配 Softmax 量纲 | 训练 | 2026-04-01 | L2 更新 | 待 Phase 11b |
| INS-049 | 跨期 Batch 毒药 — 乱序 WebDataset 封杀 Batch 维度归一化 | 训练 | 2026-04-01 | L2 更新 | active |
| INS-050 | L1 脑死亡陷阱 — z_sparsity 语义翻转修正 | 物理 | 2026-04-01 | NONE | active |
| INS-051 | 点对点建仓之矛 — Pointwise Huber Loss 替代 Softmax 交叉熵 | 训练 | 2026-04-01 | L2 更新 | 待用户确认 |

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
| INS-015 | bayesian_recon_and_cg_microstructure | — |
| INS-016 | bayesian_recon_and_cg_microstructure | — |
| INS-017 | vanguard_convergence_protocol | — |
| INS-018 | cross_sectional_relativity | — |
| INS-019 | compression_is_intelligence_phase7_golive | — |
| INS-020 | compression_is_intelligence_phase7_golive | — |
| INS-021 | compression_is_intelligence_phase7_golive | — |
| INS-022 | spacetime_correction_phase7_golive_v2 | — |
| INS-023 | spacetime_correction_phase7_golive_v2 | — |
| INS-024 | phase7_audit_phase8_deep_fat_tail | — |
| INS-025 | phase7_audit_phase8_deep_fat_tail | — |
| INS-026 | phase7_audit_phase8_deep_fat_tail | — |
| INS-027 | phase7_audit_phase8_deep_fat_tail | — |
| INS-028 | compression_paradox_asymmetric_evolution | — |
| INS-029 | compression_paradox_asymmetric_evolution | — |
| INS-030 | phase9_asymmetric_evolution_leaky_pearson | — |
| INS-031 | phase9_asymmetric_evolution_leaky_pearson | — |
| INS-032 | metric_collapse_softmax_portfolio_loss | — |
| INS-033 | metric_collapse_softmax_portfolio_loss | — |
| INS-034 | metric_collapse_softmax_portfolio_loss | — |
| INS-035 | metric_collapse_softmax_portfolio_loss | — |
| INS-036 | post_phase10_three_campaigns | — |
| INS-037 | post_phase10_three_campaigns | — |
| INS-038 | post_phase10_three_campaigns | — |
| INS-039 | phase11_asura_protocol + phase11_spear_protocol | — |
| INS-040 | phase11_asura_protocol + phase11_spear_protocol | — |
| INS-041 | phase11_spear_protocol | — |
| INS-042 | phase11_spear_protocol | — |
| INS-043 | phase11_spear_protocol | — |
| INS-044 | phase11_spear_protocol | — |
| INS-045 | phase11_spear_final_verdict | — |
| INS-046 | phase11b_reforged_spear | — |
| INS-047 | phase11b_reforged_spear | — |
| INS-048 | phase11b_reforged_spear | — |
| INS-049 | phase11c_pointwise_spear | — |
| INS-050 | phase11c_pointwise_spear | — |
| INS-051 | phase11c_pointwise_spear | — |
