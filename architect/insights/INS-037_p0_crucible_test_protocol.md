---
id: INS-037
title: P0 物理熔炉协议 — 回测先行，代码冻结
category: metrics
date: 2026-03-31
axiom_impact: NONE
status: active
source_directive: post_phase10_three_campaigns
source_gdoc: null
---

# INS-037: P0 物理熔炉协议 — 回测先行，代码冻结

## 裁决

Phase 10 产出必须先通过 Phase 8 防弹模拟器的实盘回测验证，在看到 S7 (Asymmetry Payoff Ratio) 数据之前，**严禁修改任何训练代码**。回测结果决定后续路线：P1（修补）或 P2（重铸）。

## 理由

验证集 PfRet = 0.210 只是数学相对分数，不等于实盘 alpha。历史教训（Phase 9 的 7 jobs 全败）证明理论指标和实盘表现之间存在巨大鸿沟。必须用真实 A 股物理法则审判。

## 回测参数（不可降级）

| 参数 | 值 | 理由 |
|------|-----|------|
| board_loss_cap | true | 主板10%/科创20% 跌停物理兜底 |
| cost_bp | 25 | 双边摩擦冲击（税5+佣6+滑7+冲7） |
| max_positions | 50 | 集中度上限 |
| trailing_stop_pct | -10% | 尾部风控 |

## 推理要求

- checkpoint: `gs://omega-pure-data/checkpoints/phase10_softmax_v5/best.pt`
- 必须通过 forward hook 提取 `z_sparsity` 写入 `predictions.parquet`（复用 INS-034 要求）

## 战略决策树

```
P0 回测结果
├── Asymmetry Ratio > 2.0 → 胜利分支
│   └── P1: 方差修复 (INS-036) → Phase 11 HPO
│       └── 检查项: OOS/IS=1.38 是否因牛市 Beta？(看 23-24 熊市逐年分解)
│
└── Asymmetry Ratio ≈ 1.2 → 失败分支
    └── P2: 双头阿修罗 (INS-029 升级 → INS-038)
        └── 共享底层 + 双 z_core(hd=32) + Long/Veto Head
```

## 影响文件

- `phase7_simulate.py` 或 `phase8_simulate.py`: 运行回测（不修改，只运行）
- 推理脚本: 添加 z_sparsity forward hook（如未实现）
