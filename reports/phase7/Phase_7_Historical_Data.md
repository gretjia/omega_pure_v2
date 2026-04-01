完整历史数据汇总（Phase 7 决策依据）
________________


一、模型演进时间线
阶段
	日期
	Loss
	关键结果
	教训
	Phase 3 v15
	03-24~25
	Huber / MSE
	Epoch 1 FVU=0.9997 (突破1.0)，之后 MDL 杀死信号
	λ_s=0.001 太猛，信号梯度~10⁻⁴ 被 MDL 碾压
	Phase 4 HPO
	03-25~26
	Huber / MSE
	30+70 trials, T16 best FVU=0.998896
	6维搜索确认架构有效，但 MSE Loss 触及天花板
	Vanguard V1
	03-27
	Huber / MSE
	Spread = -1.67 BP (反向信号!)
	Loss 逼反了方向，架构本身没问题
	Vanguard V2
	03-28
	IC Loss
	Spread = +11.07 BP, 单调性 9/9
	IC Loss 一招翻盘，+27.9% 改善
	Phase 6 HPO
	03-28~29
	IC Loss
	T36 IC=+0.0667, Spread=+12.55 BP
	7维搜索，70 trials，收敛区域完全锁定
	________________


二、Phase 6 Top-3 完整参数
参数
	T36 (Best)
	T29 (Backup)
	T55
	IC
	+0.0667
	+0.0661
	+0.0659
	Spread (BP)
	12.55
	11.45
	9.14
	单调性
	7/9
	8/9
	5/9
	Top 10% 均值
	14.56 BP
	14.37 BP
	12.35 BP
	扣10BP净利
	+4.56
	+4.37
	+2.35
	hidden_dim
	128
	64
	64
	window_size_t
	32
	32
	32
	lr
	3.0e-4
	3.2e-4
	2.8e-4
	lambda_s
	1e-7
	1e-7
	1e-7
	warmup_epochs
	2
	2
	2
	batch_size
	128
	128
	128
	anchor_weight
	1e-4
	1e-3
	1e-4
	cg
	1
	1
	1
	收敛共识：wt=32, bs=128, λ=1e-7, wu=2 — 所有 Top-10 结果在此高度一致。
________________


三、模型架构参数量
hidden_dim
	参数量
	用途
	64
	19,717
	T29 / T55
	128
	77,125
	T36 (Phase 7 主力)
	256
	305,605
	未中选
	________________


四、数据规模
项目
	值
	总样本
	9.96M
	总 shards
	1992 (每 shard 5000 样本)
	总存储
	164GB WebDataset
	日期范围
	2023-01-03 → 2026-01-30 (552 交易日)
	Train
	Shard 0-1593 (2023-01 → 2025-06)
	Val
	Shard 1594-1992 (2025-06 → 2026-01)
	A股票池
	5312 只 (过滤后)
	Target 均值
	-5.08 BP
	Target 标准差
	216.24 BP
	________________


五、Volume-Clock 物理参数
参数
	值
	含义
	ADV_FRACTION
	0.02
	每根bar = 消耗2%日均量
	MACRO_WINDOW
	160 bars
	感受野（~3天宏观建仓周期）
	STRIDE
	20 bars
	滑动步长
	PAYOFF_HORIZON
	20 bars
	持仓周期（锁定，禁入HPO）
	vol_threshold
	max(ADV×2%, 1000)
	动态阈值
	空间深度
	10 档 LOB
	5 bid + 5 ask
	关键推算：20 bars × 2% ADV = 消耗 40% 日均量。对日均成交 1 亿的股票，20 bars ≈ 1-2天。对日均成交 1000 万的中小盘，20 bars 可能 1-3周。
________________


六、张量通道定义
Ch
	名称
	含义
	0
	Bid_P
	买价 (每档)
	1
	Bid_V
	买量 (每档)
	2
	Ask_P
	卖价 (每档)
	3
	Ask_V
	卖量 (每档)
	4
	Close
	收盘价
	5-6
	reserved
	预留 (ETL 填 0)
	7
	delta_p
	微观价格冲击 $\Delta P$
	8
	macro_v_d
	20日滚动 ADV
	9
	macro_sigma_d
	20日滚动 ATR
	________________


七、SRL 物理公式
$$Q_{\text{hidden}} = \text{sign}(\Delta P) \times \left( \frac{|\Delta P|}{c_i \times \sigma_D} \right)^{2.0} \times V_D$$
* $\delta = 0.5 \rightarrow \text{power} = 1/\delta = 2.0$ (永恒，不可学习)
* $c_i$: per-stock 摩擦系数 [0.05, 10.0]
* $c_{\text{default}} = 0.842$ (TSE回退值)
________________


八、Loss 函数
$$\text{Total} = (1 - \text{Pearson\_IC}) + \text{anchor\_weight} \times \text{MSE} + \lambda_s \times \|z_{\text{core}}\|_{L1}$$
* Phase 6 锁定: $\lambda_s = 1\times10^{-7}$, anchor = $1\times10^{-4}$, warmup = 2 epochs
________________


九、成本假设历史
来源
	假设
	说明
	Phase 5a 回测
	10 BP
	印花税5 + 佣金3 + 滑点2
	CLAUDE.md
	15 BP
	保守估计
	Gemini 审计
	20-25 BP
	含市场冲击 (印花税5 + 佣金6 + 滑点7 + 冲击7)
	Phase 7 锁定
	25 BP
	采纳 Gemini 建议
	________________


十、VIA NEGATIVA（已证伪路径）
数学/架构类：
* Wall-Clock 时间轴 ✗ → 改为 Volume-Clock
* 拍扁空间轴 [160,7] ✗ → 保留 4D [B,T,S,F]
* 固定绝对阈值 ✗ → 改为动态 ADV×2%
* 翻转窗口 ✗ → 改为滑动窗口 stride=20
* MSE/Huber Loss ✗ → 改为 IC Loss（有方向翻转的证据）
* MDL $\lambda=0.001$ ✗ → 改为 $\lambda=1\times10^{-7}$（此前信号太弱被 MDL 杀死）
工程类：
* gc.collect() 紧循环 ✗（导致 -56% 性能下降）
* 多 worker ETL ✗（I/O 复制导致 2.5x 更慢）
* SSH 不继承 OOM 保护 ✗
* float("inf") 报错 Vizier ✗
________________


十一、Gemini 48h 审计 8 条教训
1. 物理常数由人类锁定，AI 只提供参考区间。
2. SSH 子进程不继承 OOM 保护 → 改用 systemd-run。
3. cgroup CPU 限流 → 使用 heavy-workload.slice。
4. gc.collect() 会引发性能灾难。
5. 未授权删除 188GB 数据 → 破坏性操作必须人工确认。
6. AI 自测自验 = 系统性自欺。
7. 发现非 A 股数据污染 (3054/8366 = 35%)。
8. 双实例 ETL 无锁会导致 OOM。
________________


十二、linux1 节点状态
资源
	状态
	CPU
	32 cores AMD
	RAM
	64GB (46GB free)
	GPU
	Radeon 8060S 64GB — 不可用 (HIP kernel error)
	磁盘
	/omega_pool 7% used (93% free)
	推理速度
	~20 min / 1.88M samples (CPU)
	全量推理预估
	9.96M / 1.88M × 20min ≈ 106 min
	________________


十三、Checkpoint 路径
模型
	GCS 路径
	T36 (主力)
	gs://omega-pure-data/checkpoints/phase6_icloss/trial_36/best.pt
	T29 (备选)
	gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt
	Vanguard V2
	gs://omega-pure-data/checkpoints/vanguard_v2_icloss/
	T16 (Phase 4)
	gs://omega-pure-data/checkpoints/phase4_standard/trial_16/best.pt
