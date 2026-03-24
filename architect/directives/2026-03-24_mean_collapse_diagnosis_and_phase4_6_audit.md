# 架构师指令：均值坍缩诊断 + Phase 4/6 致命悖论审计
- **日期**: 2026-03-24
- **来源**: 独立架构师 via Claude Code 对话
- **触发条件**: Phase 3 训练 v10-v13 全部 FVU≈1.0（均值坍缩）
- **Claude 工程师审核**: 认可全部诊断，补充了 target per-batch vs 全局统计量的区别

## 0x00 背景

Phase 3 训练经历 v10-v13 四个版本，FVU 始终钉在 1.00-1.01：
- v10 (log1p, lr=1e-4, mask=0.5): FVU=1.0005
- v11 (Financial Relativity, lr=1e-4, mask=0.5): FVU=1.0032
- v12 (诊断, lr=0.01, mask=0): FVU=0.9997 (短暂突破)
- v13 (lr=1e-3, mask=0, hidden=128): FVU=1.0056→1.0076→1.0107→1.0057→1.2041→1.0039

模型退化为常数预测器（输出≈target 均值 -5 BP），MSE≈Var(target)≈46656，FVU≡1.0。

## 0x01 病理学诊断

### 诊断 1: Target 未归一化 + MSE 肥尾爆炸
- 金融收益率是尖峰胖尾分布，5σ 离群点（闪崩/大单）产生毁灭性平方级梯度惩罚
- Epoch 4 的 FVU=1.2041 就是极端 Outlier 冲击的证据
- 模型为避免被离群点炸毁，收缩预测值到均值附近 → 均值坍缩

### 诊断 2: MDL 过早绞杀 (Premature Regularization)
- S_T 在 280-450 震荡，模型还没学会任何有用映射就被 MDL 信息压缩惩罚
- 模型发现"压低权重迎合 S_T 惩罚"比"拟合噪音数据"更容易
- 等同于婴儿还没学会走路就被逼负重马拉松

## 0x02 全链路审计：Phase 4 & Phase 6 致命悖论

### 致命悖论 1: payoff_horizon 不可进 HPO（Phase 4）
- **物理矛盾**: payoff_horizon 定义任务目标本身，不同 horizon 的 Var(target) 完全不同
- **灾难后果**: Vizier 会发生"目标劫持"——选天然波动最小的 horizon 而非最强的网络拓扑
- **修正法则**: 由人类架构师锁定 payoff_horizon=20（基于交易成本和换手率），从 HPO 搜索空间中移除

### 致命悖论 2: LOB 微观 vs T+1 隔夜跳空（Phase 6）
- **物理矛盾**: LOB 特征的 Alpha 记忆半衰期只有秒到分钟级，T+1 隔夜跳空由宏观新闻决定
- **灾难后果**: 微观 Alpha 被宏观噪音碾碎
- **修正法则**: 严格日内（Strictly Intraday），收盘前强制平仓
- **补充约束**: asymmetry_payoff_ratio > 3.0 必须叠加 Expectancy > Slippage + Fee

## 0x03 修复指令

### 手术 1: Target 归一化 + 离群点截断
- Target Z-score: (target - mean) / std
- 5σ 硬截断: clamp(target_z, -5.0, 5.0)
- Claude 补充: 建议用全局统计量 (mean=-5, std=216) 而非 per-batch 计算

### 手术 2: MSE → Huber Loss
- 误差 < delta(1.0): L2 保障微观拟合精度
- 误差 > delta(1.0): L1 抵抗极端离群值梯度爆炸

### 手术 3: MDL 延迟退火
- 前 warmup_epochs=2 强制 lambda_s=0
- 之后恢复 lambda_s=0.001

### 前置条件: 单 batch 过拟合测试（The Sanity Check）
- 取 1 个 batch (256 samples)，关闭 shuffle/masking，循环训练 500 步
- **判决标准**: FVU 必须降到 0.01 以下
- 如果不能过拟合 → 模型架构存在物理级 Bug（梯度断裂/attention mask 错误）
- 只有过拟合测试通过，才值得实施上述修复

## 架构师提供的代码

```python
def compute_robust_loss(pred, target, z_core, current_epoch, warmup_epochs=2):
    target_mean = target.mean()
    target_std = target.std() + 1e-8
    target_z = (target - target_mean) / target_std
    target_clipped = torch.clamp(target_z, min=-5.0, max=5.0)
    pred_z = pred
    base_loss = F.huber_loss(pred_z, target_clipped, delta=1.0)
    lambda_s_current = 0.001 if current_epoch > warmup_epochs else 0.0
    S_T = torch.norm(z_core, p=1) if z_core is not None else torch.tensor(0.0)
    total_loss = base_loss + lambda_s_current * S_T
    with torch.no_grad():
        pred_real = (pred_z * target_std) + target_mean
        mse_real = F.mse_loss(pred_real, target)
        val_fvu = mse_real / (torch.var(target) + 1e-8)
    return total_loss, val_fvu
```
