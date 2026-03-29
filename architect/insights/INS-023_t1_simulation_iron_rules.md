---
id: INS-023
title: T+1 模拟三铁律 — 物理锁 + 涨停买不进 + 跌停卖不出
category: architecture
date: 2026-03-29
axiom_impact: UPDATE_REQUIRED
status: pending_user_confirm
source_directive: 2026-03-29_spacetime_correction_phase7_golive_v2.md
source_gdoc: null
---

# INS-023: T+1 模拟三铁律

## 裁决
Phase 7 模拟器 (simulate_7.py) 必须严格执行 A 股三条物理铁律，否则回测曲线是作弊的。

## 铁律

### 铁律 1：T+1 物理时间锁
买入当日**绝对不可卖出**，必须至少持仓到下一个交易日。
即使触发止损，如果 T+1 未满足，也必须锁过夜，承受真实隔夜跳空风险。
```python
is_t_plus_1_met = (current_calendar_date > pos.entry_calendar_date)
if not is_t_plus_1_met:
    pos.mark_as_locked_in_drawdown()  # 不能卖，硬扛
```

### 铁律 2：跌停板流动性黑洞
跌停锁死时卖不出，只能硬扛到下一个开板日。
```python
if is_limit_down(stock, current_date):
    continue  # 跌停无法成交
```

### 铁律 3：涨停板买不进
涨停时无法建仓。
```python
if is_limit_up(stock, current_date):
    continue  # 涨停无法买入
```

## 理由
- payoff_horizon = 20 bars ≈ 0.4 天，但 T+1 强制最少持仓 1 天
- T+1 锁使得实际持仓时间 = max(0.4天, 1天) = **至少 1 天**
- 跌停时所有卖单排队，散户几乎不可能成交
- 涨停时所有买单排队，散户几乎不可能买入
- 不执行这三条铁律 = 回测超额收益中包含不可实现的幻觉交易

## 影响文件
- `tools/phase7_simulate.py`: 核心模拟循环必须实现三条铁律
- `architect/current_spec.yaml`: 新增 backtest.t_plus_1_lock 和 backtest.limit_up_down_enforcement
