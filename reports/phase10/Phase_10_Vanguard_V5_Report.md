Phase 10 Vanguard V5 — 完整训练报告
基础信息
项目
	值
	Job ID
	8443272505497485312
	Docker
	omega-tib:phase10-v5
	硬件
	g2-standard-8 + L4 GPU (On-demand)
	模型
	OmegaTIBWithMasking, 21,413 参数
	Loss
	Softmax Portfolio Loss + L2 mean-shift + MDL
	数据
	1593 train / 399 val shards (80/20 temporal split)
	验证样本
	1,904,747
	数据 staging
	1992 shards in 1667s (27.8 min)
	总耗时
	12.5h (15:25 → 03:53 UTC)
	总费用
	~$9.6
	超参数
* lr=3.2e-4, lambda_s=1e-7, temperature=1.0, l2_weight=1e-4
* batch_size=256, warmup_epochs=2, mask_prob=0.5
* hidden_dim=64, window_size_t=32, epochs=20, steps_per_epoch=10000
* scheduler=OneCycleLR(pct_start=0.05, cos anneal)
________________


全 20 Epoch 训练曲线
Val PfRet
Plaintext
0.21 |                                              ★16
0.20 |                                          ·····17·18·19
0.19 |                                    14·
0.18 |                              9·10·
0.17 |            2··3·                11·   13·
0.16 |
0.15 |                          5·6·         12·
0.14 |
0.13 |
0.12 |                                   15·
0.11 |                      7·
0.10 |
0.09 |
0.08 |                  4·        8·
0.07 |
0.03 |          1·
0.01 |    0·
     +----+----+----+----+----+----+----+----+----+----→ Epoch
     0    2    4    6    8   10   12   14   16   18  19


Val Std_yhat (BP)
Plaintext
6400 |                        9·
5800 |                          10·     13·
5400 |                      8·
5100 |                                        16·
4900 |                                     15· ·17·18·19
4500 |                  4·              14·
4200 |                    5·         12·
3300 |                      6·  11·
3200 |            3·
2700 |                    7·
2500 |          2·
 500 |    0··1·
     +----+----+----+----+----+----+----+----+----+----→ Epoch
     0    2    4    6    8   10   12   14   16   18  19


________________


逐 Epoch 数据表
Epoch
	Train PfRet
	Val PfRet
	Val Loss
	Val Std (BP)
	S_T
	耗时(s)
	阶段
	0
	0.051
	0.011
	-0.009
	435
	50
	1246
	冷启动
	1
	0.016
	0.033
	-0.033
	518
	58
	2194
	MDL warmup
	2
	0.073
	0.166
	-0.163
	2518
	114
	2195
	爆发
	3
	0.047
	0.168
	-0.161
	3208
	254
	2194
	Peak 1
	4
	0.085
	0.083
	-0.056
	4456
	266
	2202
	崩塌
	5
	0.098
	0.136
	-0.115
	4239
	288
	2197
	反弹
	6
	0.075
	0.133
	-0.130
	3340
	252
	2198
	震荡
	7
	0.060
	0.108
	-0.105
	2721
	148
	2196
	谷底
	8
	0.070
	0.074
	-0.044
	5382
	221
	2209
	最低点
	9
	0.121
	0.186
	-0.169
	6372
	345
	2201
	二次爆发
	10
	0.126
	0.189
	-0.162
	5801
	291
	2197
	Peak 2
	11
	0.117
	0.175
	-0.173
	3055
	267
	2198
	Std收敛
	12
	0.101
	0.153
	-0.140
	4067
	220
	2190
	回落
	13
	0.123
	0.172
	-0.166
	5608
	275
	2187
	反弹
	14
	0.136
	0.191
	-0.188
	4410
	267
	2191
	Peak 3
	15
	0.108
	0.122
	-0.113
	4851
	226
	2191
	暴跌
	16
	0.152
	0.210
	-0.204
	5055
	215
	2189
	Best
	17
	0.138
	0.206
	-0.201
	4752
	205
	2198
	收敛
	18
	0.128
	0.208
	-0.202
	4926
	211
	2185
	收敛
	19
	0.130
	0.207
	-0.201
	4918
	218
	2187
	收敛
	________________


三阶段物理分析
Phase A (Epoch 0-3): 快速学习
* Val PfRet: 0.011 → 0.168 (16x)
* Std: 435 → 3208 BP (温和上升)
* MDL warmup epoch 0-1，epoch 2 开始 lambda_s 生效
Phase B (Epoch 4-15): 高方差震荡
* Val PfRet 在 0.07~0.19 之间剧烈振荡
* OneCycleLR 高 lr 平台期 → 梯度过大 → 预测值震荡
* Peak 逐步抬升: 0.168 → 0.189 → 0.191
Phase C (Epoch 16-19): 余弦退火收敛
* Val PfRet 稳定在 0.206~0.210
* Std 稳定在 4750~5055 BP
* S_T 稳定在 ~210 (MDL 结构复杂度)
* lr 接近 0，模型锁定
________________


Best Model
指标
	值
	Checkpoint
	gs://omega-pure-data/checkpoints/phase10_softmax_v5/best.pt
	Epoch
	16
	Val Portfolio Return
	0.2103
	Val Loss
	-0.2040
	Val Std_yhat
	5055 BP
	Train Portfolio Return
	0.1524
	OOS/IS Ratio
	1.38 (Val > Train)
	________________


与 Phase 6/9 对比
维度
	Phase 6 (对称 Pearson)
	Phase 9 (非对称 Pearson)
	Phase 10 (Softmax)
	最优 Epoch
	14
	— (全败)
	16
	Val IC
	0.066
	-0.001 (崩溃)
	N/A (不同 metric)
	Val PfRet
	N/A
	N/A
	0.210
	OOS/IS
	1.00
	0 (崩溃)
	1.38
	Std_yhat 爆炸
	无
	9300% 爆炸
	5055 BP (可控)
	收敛?
	是
	否
	是 (Epoch 16-19)
	________________


待解决问题
1. Std_yhat=5055 BP 偏高 — L2 mean-shift penalty 对 Softmax 无效 (mean≈0 天然成立)，需改为 variance penalty。
2. Val > Train (OOS/IS=1.38) 异常 — 可能是 batch Z-score 在 val 上的统计噪音，需要回测验证。
3. Val PfRet 不等于实盘收益 — 需通过 Phase 8 simulate 回测才能判断真实 asymmetry ratio。
下一步
1. 用 best.pt 跑全量推理 (1992 shards)，导出 predictions + z_sparsity。
2. 送入 Phase 8 回测模拟器，计算 Sharpe / asymmetry ratio / profit factor。
3. 与 Phase 6 T29 旗舰对比。
