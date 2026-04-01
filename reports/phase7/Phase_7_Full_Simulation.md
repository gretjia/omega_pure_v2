Phase 7: 全量模拟实盘 — 最终方案
核心洞察 (Bible)
压缩即智能：利用高维拓扑（Topology）+ 平方根法则（SRL）+ 认知复杂性（Epiplexity）+ 时间有界熵（Time-bounded Entropy）捕捉A股主力行为。
目标行为：主力在个股上进行长达数月甚至一年的建仓、拉升和高抛低吸。绝非高频。
________________


Part 1: Spec 修改（3处）
1a. 废弃 INS-011，重写 backtest 节
文件: architect/current_spec.yaml (lines 149-153)
YAML
# BEFORE (INS-011, 基于错误假设"秒级LOB微观Alpha"):
backtest:
  execution_delay: "N+1 bar VWAP"
  t_plus_1_exposure: false
  exit_strategy: volume_clocked_intraday
  success_criterion: "asymmetry_payoff_ratio > 3.0 AND expectancy > slippage + fee"


# AFTER (对齐核心洞察"数月级主力行为检测"):
backtest:
  execution_delay: "N+1 bar VWAP"    # 信号触发后下一根Bar的VWAP成交（不变）
  holding_horizon: "20 volume-clock bars (calendar: 数天到数周，取决于个股流动性)"
  overnight_exposure: true             # 主力行为跨越数天到数月，隔夜持仓是必然的
  exit_strategy: "volume_clocked_natural_horizon + trailing_stop"
  # 退出逻辑：持仓到 target horizon (20 bars) 自然到期，
  # 或信号反转时提前退出，或 trailing stop 触发止损
  cost_model:
    round_trip_bp: 25                  # 印花税5 + 佣金6 + 滑点7 + 冲击7
    slippage_model: "linear_impact"    # 冲击成本 ∝ 成交量/ADV
  success_criterion: "asymmetry_payoff_ratio > 3.0 AND profit_factor > 1.5"
  # INS-011 (严格日内) 已废弃 — 与核心论点物理冲突
  # 原因：SRL检测的是数月级主力元订单，强制日内平仓等于在建仓期斩断肥尾


1b. 更新 INS-011 状态
文件: architect/insights/INS-011_intraday_only_backtest.md
* status: pending_user_confirm → SUPERSEDED
* 添加废弃原因：核心论点是检测数月级主力行为，非秒级微观Alpha
1c. 更新 CLAUDE.md WHY 节（补充核心洞察）
文件: CLAUDE.md (WHY 节, line ~30)
在"压缩即智能"段落后添加：
### 主力行为检测（核心论点）
* 目标：捕捉A股机构主力在个股上长达数月的建仓、拉升、高抛低吸行为
* 逻辑：SRL反演提取隐藏的元订单（metaorder）流 — 大资金通过分拆订单隐藏的真实意图
* 尺度：Volume-Clock 每根bar = 2% ADV，20根bar的持仓周期对应数天到数周
* 策略时间尺度：中长期波段（周到月），绝非高频
* Taleb哲学：低胜率可接受，关键是抓住主力拉升时的肥尾收益
________________


Part 2: Phase 7 测试指标体系（最终版）
第一类：数学核心验证（Omega 独有）
#
	指标
	测什么
	通过标准
	执行方式
	M1
	SRL 信号增量
	Q_metaorder 是否有用
	有SRL的IC > 无SRL的IC
	消融：需训练无SRL变体
	M2
	2D 拓扑 vs 1D
	LOB空间轴保留是否优于拍扁
	2D Spread > 1D Spread
	消融：需训练1D变体
	M3
	MDL 压缩效率
	瓶颈层是否真的丢弃噪音
	z_core 稀疏度 > 50%
	Phase 7 可做：inference hook 提取 z_core
	M4
	Volume-Clock vs Time-Clock
	容量时间是否优于等间隔
	VC IC > TC IC
	消融：需重做ETL + 训练
	M5
	IC Loss vs Huber
	横截面排序损失优于绝对回归
	已证：+12.55 vs -1.67 BP
	Phase 6 已完成
	M6
	c_friction 个股标定
	per-stock c 是否优于全局常数
	标定 c_i 的 IC > 统一 c 的 IC
	消融：需训练统一c变体
	M7
	预测视野衰减
	时间有界熵能支撑多远？
	IC 在 N+21 仍显著 (>0.02)
	Phase 7 可做：用不同lag计算IC
	执行优先级：M3、M5、M7 在 Phase 7 主线即可完成。M1/M2/M4/M6 是消融实验，需独立算力，排入 Phase 8。
第二类：量化金融标准指标（可横向对比）
按 Taleb 反脆弱 + 中长期波段策略校准：
#
	指标
	定义
	业界基准
	我们的目标
	说明
	S1
	年化收益率
	CAGR 扣 25BP 成本
	量化多头 15-25%
	>15% (OOS)
	

	S2
	Sharpe Ratio
	年化 (均值/标准差)
	趋势跟踪 0.8-1.2
	>1.0 (OOS)
	中长期肥尾策略不追求超高 Sharpe
	S3
	Sortino Ratio
	年化 (均值/下行标准差)
	>1.5 优秀
	>1.5 (OOS)
	只惩罚下行，不惩罚上行爆发（Taleb 友好）
	S4
	最大回撤 MDD
	净值峰谷最大跌幅
	<15% 优秀
	<25%
	中长期策略容忍更大回撤
	S5
	最大回撤持续期
	水下最长天数
	<60天
	<90 交易日
	主力建仓有枯水期，需要耐心
	S6
	Calmar Ratio
	年化收益 / MDD
	>1.0 及格
	>0.8
	

	S7
	不对称收益比
	平均单笔盈利 / 平均单笔亏损
	Taleb >3.0
	>3.0 ★核心★
	整个系统的终极标准
	S8
	单笔胜率
	盈利交易 / 总交易
	趋势跟踪 35-45%
	>35%
	低胜率 + 高赔率 = Taleb 正期望
	S9
	Profit Factor
	总盈利 / 总亏损
	>1.5 可交易
	>1.5
	比胜率更全局的盈利能力
	S10
	IC (日度横截面)
	每日预测 vs 实际 Pearson
	>0.03 有信号
	>0.03
	日度 IC 对中长期策略自然偏低
	S11
	ICIR
	IC 均值 / IC 标准差
	>0.5 可交易
	>0.5
	

	S12
	多空价差
	Top20% - Bottom20%
	>5 BP/天
	>8 BP
	

	S13
	单调性
	十分位收益递增
	7/9 及格
	≥7/9
	

	S14
	盈亏平衡成本
	策略归零的临界成本
	越高越好
	>40 BP
	安全边际：即使成本翻倍仍不亏
	S15
	IS vs OOS 衰减
	OOS 指标 / IS 指标
	<50% 正常
	<40%
	

	S16
	风格中性 Alpha
	剥离 Size/Momentum 因子后
	>0 即有纯 Alpha
	显著为正
	证明收益来自主力检测，不是抱团小盘
	S17
	资金容量估算
	基于 ADV 占比的策略上限
	>1亿 可运营
	估算值
	自身资金变大后是否被反噬
	________________


Part 3: Phase 7 执行计划
Pipeline（不变，3 脚本 + 1 报告）
Plaintext
[1. date_mapper.py]  ~10 min
       ↓
[2. inference_7.py]  ~3h (增加: z_core hook + 多horizon IC)
       ↓
[3. simulate_7.py]   ~30 min (重写: 中长期波段模拟)
       ↓
[4. report_7.py]     omega-vm


Script 2 修改：inference_7.py 增加项
* z_core 稀疏度：注册 forward hook 拦截 EpiplexityBottleneck 输出，计算每样本 L0 norm 比例，存入 predictions.parquet
* 多 horizon IC 数据：保存 raw (pred, target) 对，simulate 阶段用不同 lag 计算 IC 衰减曲线
Script 3 重写：simulate_7.py（中长期波段）
核心逻辑变化（对比原日内版本）：
维度
	原版（日内，已废弃）
	新版（中长期波段）
	持仓周期
	日内强制平仓
	20 volume bars 自然到期（数天到数周）
	换手
	每日 100%
	自然换手：信号到期退出，新信号入场
	组合构建
	每日全量重排
	滚动组合：每日只处理新信号 + 到期退出
	成本计算
	每日双边 25BP
	开仓 + 平仓各一次 = 25BP/笔
	涨跌停
	过滤
	过滤（不变）
	流动性
	过滤
	过滤 + 持仓量 < 2% ADV（不变）
	信号加权
	softmax(pred)
	softmax(pred)（不变）
	止损
	无
	trailing stop -10%（防止单笔灾难）
	模拟伪代码：
Python
portfolio = {}  # symbol -> {entry_date, entry_price, pred_bp, bars_held}


for each trading_day:
    # 1. 检查到期 & 止损
    for pos in portfolio:
        if pos.bars_held >= 20 or trailing_stop_hit:
            close position, record PnL - 12.5BP (卖出半程成本)


    # 2. 新信号入场
    today_signals = get_predictions(date)
    filtered = remove_limit_stocks(today_signals)
    filtered = remove_illiquid(filtered, adv_floor)
    ranked = cross_sectional_rank(filtered)


    # 3. Top quintile 开仓（不与已持仓重复）
    new_longs = ranked[top_20%] - portfolio.keys()
    for stock in new_longs (signal-weighted, max_positions cap):
        open position, deduct 12.5BP (买入半程成本)


    # 4. 记录日度 NAV
    mark_to_market(portfolio)


输出指标对应关系
指标
	来源脚本
	数据需求
	S1-S6 (收益/风险)
	simulate_7.py
	equity_curve.csv
	S7-S9 (交易质量)
	simulate_7.py
	trades.parquet (单笔PnL)
	S10-S13 (信号质量)
	simulate_7.py
	predictions.parquet + date_map
	S14 (盈亏平衡成本)
	simulate_7.py
	参数扫描 cost_bp=[25,30,35,40,50]
	S15 (IS/OOS衰减)
	simulate_7.py
	分段统计 shard<1594 vs ≥1594
	S16 (风格中性Alpha)
	simulate_7.py
	需额外：市值/行业数据（从parquet提取）
	S17 (容量估算)
	simulate_7.py
	macro_v_d × position_fraction
	M3 (MDL稀疏度)
	inference_7.py
	z_core hook
	M5 (IC Loss vs Huber)
	—
	Phase 6 已证
	M7 (视野衰减)
	simulate_7.py
	不同 lag 的 IC 计算
	________________


Part 4: 需要用户确认的决策
1. 废弃 INS-011 — 将 current_spec.yaml backtest 节重写为中长期波段
2. 修改 CLAUDE.md — 补充"主力行为检测"核心论点段落
3. 更新 INS-011 文件 — 标记为 SUPERSEDED
4. Phase 7 主线只做 M3/M5/M7 + 全部 S 类指标，消融实验 (M1/M2/M4/M6) 推到 Phase 8
________________


关键文件清单
文件
	操作
	architect/current_spec.yaml (L149-153)
	重写 backtest 节
	architect/insights/INS-011_intraday_only_backtest.md
	更新 status→SUPERSEDED
	CLAUDE.md (WHY 节)
	添加 主力行为检测段落
	tools/phase7_date_mapper.py
	新建
	tools/phase7_inference.py
	新建 (含 z_core hook)
	tools/phase7_simulate.py
	新建 (中长期波段模拟)
	tools/phase7_report.py
	新建
	________________


验证方式
1. 运行 omega_axioms.py 确认公理断言通过（spec 变更后）
2. linux1 全量推理 → predictions.parquet 行数 ≈ 9.96M
3. 模拟输出 → 检查 S7 (不对称收益比) 是否 > 3.0
4. 成本扫描 → 确认 S14 (盈亏平衡成本) > 40 BP
5. IS vs OOS 分段对比 → 确认无严重过拟合
