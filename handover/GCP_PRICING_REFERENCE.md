# GCP Pricing Reference (2026-03-25)

基于用户实际 pricing sheet 提取，非公开目录价。

## Vertex AI Training: g2-standard-8 + 1×L4 (us-central1)

### Standard (On-Demand)

| 组件 | SKU ID | 单价 | 数量 | $/h |
|------|--------|------|------|-----|
| G2 Core | 976E-BCA3-15EF | $0.028736/core·h | 8 | $0.2299 |
| G2 Core Mgmt | B03F-5103-EE74 | $0.003748/core·h | 8 | $0.0300 |
| G2 RAM | 74D0-9075-AB7B | $0.003367/GiB·h | 32 GiB | $0.1077 |
| G2 RAM Mgmt | 2BF0-DBAA-E0D2 | $0.000439/GiB·h | 32 GiB | $0.0141 |
| L4 GPU | 37AD-572D-B2EC | $0.644046/GPU·h | 1 | $0.6441 |
| L4 GPU Mgmt | 64E9-CBF1-8858 | $0.084006/GPU·h | 1 | $0.0840 |
| **Total** | | | | **$1.1098/h** |

### Spot/Preemptible (GCE 层定价)

| 组件 | SKU ID | 单价 | 数量 | $/h |
|------|--------|------|------|-----|
| Spot G2 Core | 59A6-9C49-BDDB | $0.01/core·h | 8 | $0.0800 |
| Spot G2 RAM | BF80-650A-78E6 | $0.001171/GiB·h | 32 GiB | $0.0375 |
| Spot L4 GPU | AEC2-3D5C-61BF | $0.2231/GPU·h | 1 | $0.2231 |
| **Spot Compute Total** | | | | **$0.3406/h** |
| + Vertex AI Mgmt Fee (est) | | | | ~$0.128/h |
| **Spot + Mgmt Total** | | | | **~$0.47/h** |

### 折扣率

| 对比 | Standard | Spot | 折扣 |
|------|----------|------|------|
| L4 GPU | $0.644 | $0.223 | **65% off** |
| G2 Core | $0.029 | $0.010 | **66% off** |
| G2 RAM | $0.0034 | $0.0012 | **65% off** |
| 总计 | $1.11 | ~$0.47 | **~58% off** |

## CUD 状况

- **Compute Flexible CUD - 1 Year**: **$0.07/h** spend-based 承诺
  - 订阅 ID: 458fd6c5-9a83-43d7-8b93-5cbdbbff7775
  - 有效期: 2026-03-25 → 2027-03-24
  - 折扣率: 1 年 = 28%, 3 年 = 46%
  - 实际支付: $0.07 × 0.72 = $0.0504/h ($441/年)
  - 覆盖: **G2/E2/N2 等 vCPU 和 RAM** (含 Vertex AI Training 的 CPU/RAM 部分)
  - **不覆盖**: GPU (L4/A100 等) — GPU 需要 resource-based CUD
  - 承诺额 $0.07/h 远小于 HPO 实际 CPU/RAM 消耗，超出部分 on-demand
- **对 Phase 4 HPO 实际节省: ~$0.02/h (可忽略)**
- **如需 GPU 折扣**: 需购买 resource-based CUD (L4 可达 55% off, 但需锁定区域/数量)

## A100 Training 参考

| GPU | SKU | 单价/h | 备注 |
|-----|-----|--------|------|
| A100 80GB | 8FFC-6CDE-24D7 | $4.5173 | 配额: 12 |

## Phase 4 HPO 预算参考

| 场景 | 单价 | 100 trials × 2h |
|------|------|-----------------|
| Standard | $1.11/h | **$222** |
| Spot (if available) | ~$0.47/h | **~$94** |
| Spot + 50% 早停 | ~$0.47/h | **~$47** |
