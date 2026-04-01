# Gemini GCS I/O 优化审计

- **日期**: 2026-03-30
- **模型**: gemini-3.1-pro-preview
- **角色**: Google Cloud GCS + Vertex AI 性能工程师
- **审计对象**: train.py, omega_webdataset_loader.py, phase9_train_config.yaml

## 核心发现

模型 19.7K 参数极小，GPU 几秒吃完数据，99% 瓶颈在 I/O。

| 维度 | 评分 | 问题 |
|------|------|------|
| GCS→Local Staging | 3/10 | pd-ssd 800GB 读吞吐仅 384 MB/s |
| WebDataset I/O | 6/10 | .decode() 通用解码器 15% CPU 开销 |
| Vertex AI 配置 | 5/10 | 未利用 GCS FUSE v2 file-cache |
| 性价比 | 8/10 | Spot 代码完美，但 Nearline 有 $111 检索费陷阱 |

## 4 条优化建议（已采纳）

1. GCS FUSE v2 + Local SSD: 删除手动 staging，第 1 轮自动缓存，后 19 轮 NVMe 读
2. fast_npy_decoder: 替换 .decode()，绕过通用解码器
3. Spot 实例: $0.25/hr vs $0.75/hr，SIGTERM 代码已适配
4. DataLoader: num_workers=6, prefetch_factor=4

## 关键警告

- 训练数据 Bucket 必须 Standard 存储类别（Nearline 20 epoch = $111 检索费）
- omega_shard_0001~1992 单调命名可能触发 GCS Tablet Hotspotting
- g2-standard-8 网络上限 16 Gbps (~2 GB/s)，staging 5min 已是该机型极限
