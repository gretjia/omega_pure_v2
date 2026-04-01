# 范式切换原子 Checklist (C-054)

当修改以下任一项时，**全部 6 步必须作为原子事务完成**，不可分 session 执行：

触发条件：
- [ ] Loss 函数类型变更（如 Softmax→Huber）
- [ ] 归一化方式变更（如 Z-score→绝对 BP）
- [ ] 输出量纲变更（如 Z-score→BP）
- [ ] 新增/删除正则化项

## Checklist

### 1. 全栈 grep 扫描
```bash
# 找出所有引用旧范式的代码
grep -rn "TARGET_STD\|TARGET_MEAN\|旧变量名" *.py gcp/*.py tools/*.py
grep -rn "\.squeeze()\|旧算子" *.py gcp/*.py tools/*.py
```
- [ ] 训练代码 (train.py, gcp/train.py)
- [ ] 推理代码 (tools/phase7_inference.py, gcp/)
- [ ] 回测代码 (backtest_5a.py, gcp/)
- [ ] 数学核心 (omega_epiplexity_plus_core.py, gcp/)
- [ ] 仪表盘/日志代码（Tensorboard、pred_std 计算）

### 2. 重标定正则化超参
- [ ] λ_s: 量纲匹配新 Loss 梯度规模
- [ ] Huber δ / 其他截断参数: 匹配新输出分布
- [ ] 用数据验证: `loss.mean()` vs `λ_s * S_T` 比例合理（不应 >100x）

### 3. 重建 Docker + canary
- [ ] `bash gcp/safe_build_and_canary.sh <phase> <version>`
- [ ] 确认 Docker 构建时间 > 最后一次代码修复提交时间
- [ ] Canary 通过

### 4. E1 后独立烟测
- [ ] 用推理脚本（不是训练日志）跑 E0/E1 checkpoint
- [ ] 断言 pred_std 在物理区间
- [ ] 断言无 NaN/Inf

### 5. 更新 Spec + HPO
- [ ] architect/current_spec.yaml 反映新参数
- [ ] HPO 搜索空间适配新量纲
- [ ] omega_axioms.py --verbose 通过

### 6. 同步推理/回测脚本
- [ ] 推理脚本输出量纲正确（无逆向缩放）
- [ ] 回测脚本输入假设正确
- [ ] gcp/ 镜像与本地一致 (diff 验证)
