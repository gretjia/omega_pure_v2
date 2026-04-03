## WHY Chain

1. GCP pd-ssd 吞吐与磁盘容量线性挂钩（0.48 MB/s per GB），这不是常识
2. 800GB pd-ssd 的理论上限仅 384 MB/s（远低于 SSD 直觉的 "几 GB/s"）
3. 556GB 训练数据 × 20 epochs = 11.1TB 总 I/O，384 MB/s 完全不够
4. 配置时未查 GCP 磁盘性能文档，直觉认为 "SSD = 快"
5. 训练时间从预期 4h 膨胀到 12h

**根因**: 违反 Ω2（先量化后行动）。未查 GCP 磁盘性能公式就选择存储方案。

## 模式泛化

**云存储性能是 provisioned capacity 的函数，不是存储介质类型的属性**。这与本地 SSD 的心智模型完全不同:
- 本地 SSD: 吞吐取决于硬件规格，与容量无关
- 云 pd-ssd: 吞吐 = f(容量)，小磁盘 = 低吞吐

泛化规则: 选择任何云存储方案前，必须:
1. 查 GCP 磁盘性能文档
2. 计算 provisioned throughput = disk_size × rate
3. 计算 total I/O = data_size × epochs
4. 确认 throughput 满足训练时间预算
