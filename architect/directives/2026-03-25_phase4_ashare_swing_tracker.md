# 架构师指令：Phase 4 A股长周期波段重构 + 时空撕裂三法则
- **日期**: 2026-03-25
- **来源**: 独立架构师 via Claude Code 对话
- **触发条件**: Phase 3 v15 完成 (FVU=0.9997) + 用户指出 A股 T+1 制度约束

## 核心哲学转向

从"华尔街微秒级高频（HFT）剥头皮"升维至"A股机构引力波雷达"。

A股的 T+1 制度、高印花税、涨跌停限制决定了：
- 高频抢跑是散户绞肉机
- 百亿级主力/国家队使用 TWAP/VWAP 算法在 5-20 个交易日内分拆建仓
- OMEGA 模型的真正使命：从微观盘口废热中积分提取跨越数周的"主力排气尾迹"

## 0x01 三大物理法则

### 法则 1: 感受野危机 → coarse_graining_factor 回归搜索空间
- 问题: T=160 步仅覆盖 ~8 分钟，无法预测 5-20 天
- 解决: coarse_graining_factor=[1,4,16,64]
  - cg=64 时，160 步 → 2.5 个"超级 Bar"，每个横跨 ~1.3 交易日
  - 相当于时间放大镜，将微观 LOB 膨胀为横跨数日的宏观视野
- 优先级: P0（最高）

### 法则 2: T+1 收益定义 → 拥抱隔夜跳空
- Target 必须编码 T+1 入场摩擦: VWAP(T+N) - VWAP(T+1)
- 隔夜跳空作为物理摩擦成本内嵌在 Label 中
- 让 Huber Loss 硬扛长尾震荡
- 注: 当前 ETL 的 payoff_horizon=20 bars，未来可能需要拉长到日级别

### 法则 3: payoff_horizon 继续锁定
- 绝对禁止 Vizier 搜索 payoff_horizon (INS-010 铁律不变)
- 人类架构师决定持仓周期

## 0x02 Phase 4 搜索空间重组

### 与上一版 Phase 4 (Alpha Resonance) 的差异
| 参数 | 上一版 | A-Share Swing |
|------|--------|---------------|
| coarse_graining_factor | 固定=1 | **搜索 [1,4,16,64]** |
| window_size_t | [8,16,32,64] | [8,16,32] (移除 64, 避免 OOM) |
| window_size_s | [5,10] | **固定=10** (全盘口深度) |
| hidden_dim | [128,256,384] | [128,256] (移除 384, OOM 安全) |

### 完整搜索空间 (6 维)
```yaml
coarse_graining_factor: [1, 4, 16, 64]  # P0: 时间放大镜
window_size_t: [8, 16, 32]               # P1: 注意力跨度
lambda_s: [1e-6, 1e-4] log              # P1: MDL 降压
warmup_epochs: [3, 4, 5]                 # P1: MDL 蜜月期
hidden_dim: [128, 256]                   # P2: 脑容量
lr: [1e-4, 1e-3] log                    # P2: 优化器
```

## 0x03 训练脚本三段防爆代码

### 防爆 1: OOM 优雅熔断
- 捕获 torch.cuda.OutOfMemoryError
- 报告 FVU=999.0（欺骗 Vizier 避开该区域）
- exit(0) 而非 error（防止无限重启烧钱）

### 防爆 2: SIGTERM 预警检查点（Spot VM 抢占保护）
- 捕获 SIGTERM（30 秒倒计时）
- 紧急保存 checkpoint 到 GCS
- 报告已收集的 best_fvu（不浪费部分计算结果）

### 防爆 3: MDL 震荡保护早停
- early_stop 必须等待 warmup_epochs + 1 个 epoch
- 让模型消化 MDL 断头台降临时的 FVU 剧震

## 架构师签发令
"战区级架构重组完成！100 张 L4 Spot VM，在 A 股暗黑森林的长河里寻找跨越周期的神级拓扑极小值！全速点火！"
