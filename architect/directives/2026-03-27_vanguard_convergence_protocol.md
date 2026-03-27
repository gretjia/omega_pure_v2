# 架构师指令：先锋定标战役 (Vanguard Protocol) — 全量收敛测试
- **日期**: 2026-03-27
- **来源**: 独立架构师 via Claude Code 对话
- **触发条件**: Phase 5a 信号方向测试显示欠训练模型(40K steps)无截面区分度

## 核心指令

### 1. 提取最强纯血基因
直接使用 T16 配置 (Phase 4 RECON 排名第一):
- cg=1, hidden=128, λ_s=6.84841e-06, lr=3.77207e-04, warmup=5, window_t=16

### 2. 解除算力封印 (Train to Full Convergence)
- 关闭早停
- 15-20 个 Epochs (vs RECON 的 8 epochs)
- 让模型彻底度过 warmup → 承受 MDL 断头台 → 跨越"均值陷阱"
- 目标: 从 0.6 passes → 3-5 passes 的数据覆盖

### 3. 监控截面方差 (Std Expansion)
训练日志必须实时监控 Std(ŷ):
- 模型预测值的标准差
- 只有 Std(ŷ) 从 ~0 开始放大，才说明模型对股票"区别对待"
- 如果 Std(ŷ) 始终坍缩于 0 → 模型在输出常数（均值陷阱）

### 4. 终极审判 (The Crucible)
用跑满 20 Epoch 的完全体 T16 模型再次执行 Phase 5a 分层回测

## 架构师决策树 (Decision Matrix)

### FAIL 路径: Spread ≤ 0, 无单调性
- 诊断: Huber Loss (MSE) 在极低信噪比下失效
- MSE 天然向均值回归，不关心截面排序
- 砸 1000 个 HPO 也无用
- **行动**: 架构动刀
  - Target → Cross-sectional Z-score (截面标准化)
  - Loss → Pearson Correlation Loss 或 ListMLE (直接优化排序)
  - 强迫网络关心"谁比谁强"而非"绝对值多少"

### PASS 路径: Spread > 0, Monotonicity 显现
- 诊断: 架构和 Loss 没问题，仅火候不够
- **行动**: 全军出击
  - 拿到可直接实盘的模型
  - 在 cg=1, warmup=5 狭窄空间内 Vizier Exploitation
