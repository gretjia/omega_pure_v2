---
id: INS-056
title: 19.7K 极小模型严禁多卡 DDP — Scale-Up Only
category: architecture
date: 2026-04-01
axiom_impact: NONE
status: active
source_directive: 2026-04-01_phase11d_io_audit_and_gpu_ruling.md
source_gdoc: null
---

# INS-056: 19.7K 极小模型严禁多卡 DDP — Scale-Up Only

## 裁决
OMEGA-TIB (19.7K params, hd=64) 严禁使用多卡分布式训练 (DDP/DataParallel)。通信延迟远超计算、I/O 饥饿、Batch Size 膨胀三重陷阱导致速度更慢且质量坍塌。加速唯一路径：升级单卡 (T4→L4) + 拉满 CPU DataLoader workers。

## 理由
* 19.7K 参数的梯度同步开销（All-Reduce latency）远超微秒级的前向/反向计算
* pd-ssd 吞吐刚好喂饱单卡，多卡触碰 I/O 天花板
* DDP 4 卡 → 有效 batch=1024（spec 锁定 256），SGD 噪声抹平 → 质量坍塌
* 代码库无 DDP 基础设施，引入 = 重写训练核心

## 影响文件
* 无需代码变更 — 这是一条永久架构约束
