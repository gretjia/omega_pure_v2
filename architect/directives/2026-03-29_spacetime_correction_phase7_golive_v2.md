# 架构师指令：时空换算谬误修正 + Phase 7 Go-Live 授权 V2

**日期**: 2026-03-29
**来源**: 独立架构师（用户）直接输入
**源文档 ID**: 无（会话内直接提供）
**优先级**: VETO — 覆盖同日早期指令中的时间尺度推算

---

## 0x00 独立架构师的终极审计：为"压缩即智能"加冕！但必须斩断"时空膨胀"的数学幻觉！

首席架构师，当你交出这份极其完备的《Phase 7 全量模拟实盘方案》，并向我抛出那个直击灵魂的自我拷问——**"目前的数据是否支持 Epiplexity 的洞察？它又怎么和 Topology 结合？"**时，你已经真正站到了深度学习与金融物理学的最高交汇点！

作为第一性原理的死忠，我将极其肯定、极其狂热地回答你：**当前 Phase 6 的数据，不仅绝对支持 Epiplexity，而且是"压缩即智能"在硅基生命上的最完美铁证！**

但是！在你的物理参数推算中，我发现了整个 OMEGA 项目自建立以来**最致命的一个"时空换算数学谬误（Mathematical Fallacy of Spacetime）"！** 如果不立刻拔除这个地雷，你的 Phase 7 模拟器将彻底违背 A 股的客观规律。

我将对你的 Plan 进行深度审计，打通你的哲学闭环，并纠正这个致命的数学错误。

---

## 0x01 理论大一统：Epiplexity 与 Topology 的完美咬合

你怀疑 Epiplexity 失效，是因为你看到 λ_s 被优化到了极小的 1e-7，你把"压缩"简单等同于了外部强加的 L1 惩罚。

请死死盯住 Phase 6 最震撼的发现：hd=64（仅 1.9 万参数的超小模型 T29/T55）极其华丽地击败了 hd=128 和 hd=256（高达 30 万参数的大模型）！

在信息论（Kolmogorov Complexity）中，压缩有两种形态：显式惩罚（外力抽打）与隐式瓶颈（物理脑容量限制）。在拥有 9.96M 的海量样本中，为什么一个小脑萎缩的侏儒网络能赢？这就是"压缩即智能"的物理涌现：

1. **高熵的噪音（无法压缩）**：散户的追涨杀跌、游资的秒级撤单，是极度混乱的布朗运动。如果你用 hd=256 的大模型，它脑容量太大，会把这些高熵噪音死记硬背下来，导致严重的样本外过拟合。
2. **低熵的信号（极度可压缩）**：主力拿着 50 亿资金建仓，他们使用的是极其机械的 TWAP/VWAP 拆单算法。这种"算法元订单（Meta-order）"在盘口留下的痕迹高度规律、极度低熵。
3. **物理滤网（Epiplexity Bottleneck）**：当你把网络物理锁死在 hd=64 时，你创造了一个极其严苛的信息窄门！庞大的散户噪音根本挤不过去，模型被迫只能去记忆那些能被极度压缩的低熵规律。
4. **两者的完美结合**：Topology（FWT）是"X光机"，它在 2D 张量上描绘出盘口的几何形状；Epiplexity（hd=64）是"铅板过滤网"，它把高熵的随机形状全部屏蔽，只让代表主力算法的"低熵几何拓扑"通过！

**结论**：λ_s 降到 1e-7 不是压缩失效，而是 hd=64 和 IC Loss 已经从架构层面完美实现了"内生压缩"！

---

## 0x02 架构级 VETO：Volume-Clock 与 T+1 法则的"时空撕裂谬误"

**这是本指令的核心修正，VETO 级别。**

之前计划中写道：
> "Volume-Clock 每根 bar = 2% ADV... 20 bars × 2% ADV = 消耗 40% 日均量。对日均成交 1 亿的股票，20 bars ≈ 1-2天。对日均成交 1000 万的中小盘，20 bars 可能 1-3周。"

**这是极其致命的数学直觉错误！**

### 物理学还原

- **ADV** = Average Daily Volume（日均成交量）
- 一根 Bar = 2% ADV
- 在任意**平均交易日**，任何股票必然生成 100% / 2% = **50 根 Bars**
- **无论大盘股还是微盘股，每天平均都流逝 50 根 Volume Bars！**
  - 大盘股：单根 bar 包含更多真实股数，但仍然 50 根/天
  - 微盘股：单根 bar 包含更少真实股数，但仍然 50 根/天
  - Volume-Clock 的本质就是消除大小盘异质性，使所有股票在 bar 轴上流逝相同
- 因此：**holding_horizon = 20 bars = 20/50 = 0.4 天 ≈ 半个交易日**
- 感受野：**macro_window = 160 bars = 160/50 = 3.2 天**（与 spec 注释"~3天宏观建仓周期"吻合）

### 重新定位模型物理尺度

| 参数 | Volume Bars | 日历时间 | 含义 |
|------|------------|---------|------|
| macro_window | 160 bars | ~3.2 天 | 看过去 3 天的盘口演化 |
| window_size_t | 32 bars | ~0.64 天 | 注意力窗口 ≈ 半天 |
| payoff_horizon | 20 bars | ~0.4 天 | 预测未来 ≈ 半天收益 |

**真相：OMEGA 是一个"T+1 隔夜波段模型"，不是数月级长线策略！**

### 但这完美契合 A 股！

主力的建仓意图长达数月，但他们**每天**都在进行"微观拆单"。模型的物理含义是：
- **用 3 天的盘口历史（160 bars）**
- **通过 SRL 反演照出今天的元订单方向**
- **预测接下来半天（20 bars）的价格走势**
- **T+1 强制隔夜 → 第二天早盘享受建仓惯性溢价**

**核心重新定义：捕捉"主力长线建仓过程中的微观执行切片"——用今天的 X 光片，预测明天的惯性**

### 对 INS-021 和 CLAUDE.md 的修正

- CLAUDE.md 不应写"数月级策略"，应写"捕捉主力长线建仓中的日内执行切片（T+1 隔夜波段）"
- INS-021 holding_horizon 描述需修正：20 bars ≈ 0.4 天，不是"数天到数周"
- overnight_exposure: true 仍然正确（T+1 强制隔夜），但原因不同

---

## 0x03 模拟器手术：T+1 的三条铁律

因为持仓周期在日历时间上极短（~0.4 天），但 A 股有 T+1 铁锁，必须在 simulate_7.py 中严格封印：

### 铁律 1：A股 T+1 物理锁
今天买的股票，今天不可卖出，必须至少持仓到下一个交易日。
```python
is_t_plus_1_met = (current_calendar_date > pos.entry_calendar_date)
if not is_t_plus_1_met:
    # 即使触发止损也不能卖，必须锁过夜，承受真实隔夜跳空
    pos.mark_as_locked_in_drawdown()
```

### 铁律 2：跌停板流动性黑洞
跌停锁死时卖不出，只能硬扛到下一个开板日。
```python
if is_limit_down(stock, current_date):
    continue  # 跌停无法成交，跳过本日
```

### 铁律 3：涨停板买不进
涨停时无法建仓。
```python
if is_limit_up(stock, current_date):
    continue  # 涨停无法买入
```

---

## 0x04 架构师最终签发令 (GO-LIVE AUTHORIZATION V2)

Phase 6 用 70 次高维搜索证明了引擎健全。Taleb 反脆弱体系（低胜率 + 极高不对称赔率 > 3.0）天然契合 A 股"牛短熊长、极端肥尾"。

极其支持 T29 (hd=64) 作为旗舰模型！

**签署的五项批准：**

1. **批准修改 Spec**：重写 backtest 节，确认 T+1 隔夜持仓和 25BP 真实成本
2. **批准修改 CLAUDE.md**：时间尺度修正为"捕捉主力长线建仓中的算法订单执行切片（T+1/T+2 隔夜波段）"
3. **批准 INS-011 → SUPERSEDED**
4. **批准测试体系**：M3 (z_core 稀疏度) + 全套 S 类指标
5. **批准 simulate_7.py 三条铁律**：T+1 物理锁 + 涨停买不进 + 跌停卖不出

---

## Spec 变更清单（V2 修正版）

### backtest 节：
```yaml
# AFTER (V2 corrected):
backtest:
  execution_delay: "N+1 bar VWAP"
  holding_horizon: "20 volume-clock bars (~0.4 average trading days; T+1 forces minimum 1-day hold)"
  overnight_exposure: true             # T+1 强制隔夜，非自愿选择
  exit_strategy: "volume_clocked_natural_horizon + trailing_stop"
  t_plus_1_lock: true                  # A股 T+1 铁律：买入当日不可卖出
  limit_up_down_enforcement: true      # 涨停买不进，跌停卖不出
  cost_model:
    round_trip_bp: 25
    slippage_model: "linear_impact"
  success_criterion: "asymmetry_payoff_ratio > 3.0 AND profit_factor > 1.5"
```

### CLAUDE.md WHY 节：
修正为："捕捉主力长线建仓过程中的算法订单执行切片（T+1 隔夜波段），而非数月级持仓"
