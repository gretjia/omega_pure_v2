---
id: INS-012
title: MDL 断头台 — λ_s=0.001 绞杀微弱 Alpha
category: training
date: 2026-03-25
axiom_impact: UPDATE_REQUIRED
status: active
source_directive: 2026-03-25_phase4_hpo_authorization.md
source_gdoc: null
---

# INS-012: MDL 断头台 — λ_s=0.001 绞杀微弱 Alpha

## 裁决
Phase 3 v15 的 λ_s=0.001 构成对微弱 Alpha 信号的致命正则化过当。MDL 启动后，模型理性地选择放弃 Alpha（收益 ~10⁻⁴）以避免结构惩罚（代价 ~10⁻²），在一个 Epoch 内切除 95.3% 的特征感知权重。

## 理由
金融低信噪比环境中的 Alpha 信号极其微弱。在 Huber Loss 空间中，Alpha 的梯度贡献远小于 MDL L1 正则化的梯度。当 λ_s × S_T >> Alpha 贡献时，优化器会理性地压缩模型到"输出均值"的退化解，因为这条路径的总损失更低。

数据证据：
- Epoch 1 (λ_s=0): S_T=10.82, FVU=0.9997 (Alpha captured)
- Epoch 2 (λ_s=0.001): S_T 从 10.82 暴跌至 0.51, FVU 反弹至 1.0220

## 影响文件
- `train.py`: lambda_s 默认值需从 0.001 降低，或完全交给 HPO 搜索
- `architect/current_spec.yaml`: training.lambda_s 搜索范围改为 [1e-6, 1e-4]
- `gcp/submit_training.sh`: Phase 4 HPO 配置需反映新搜索范围
