# 架构师指令：V3 空间轴恢复与相对容量时钟

**日期**: 2026-03-18
**来源**: 首席架构师 (Google Docs 递归审计)
**摄取者**: 人工初始化

---

## 指令内容

1. **空间轴恢复**: V2 的 `[160, 7]` 张量丢失了 LOB 深度信息。V3 必须恢复为 `[160, 10, 7]`，其中 10 为 LOB 买卖各 10 档深度
2. **相对容量时钟**: `vol_threshold` 不再是全局固定值，改为每只股票动态计算 = Rolling ADV × 2% (ADV_FRACTION = 0.02)
3. **环形缓冲区**: 使用滑动窗口 (stride=20) 替代 tumbling 窗口，保持时间连续性
4. **WebDataset 格式**: 输出从 Parquet 改为 `.tar` shard，每个样本包含 `manifold_2d.npy` + `target.npy` + `meta.json`
5. **云原生**: 目标是直接流式加载到 GCP Vertex AI，避免 DDP OOM

## 对 current_spec.yaml 的影响

- `tensor.shape` 更新为 `[B, 160, 10, 7]`
- `tensor.spatial_axis` 设为 10
- `etl.adv_fraction` 设为 0.02
- `etl.stride` 设为 20
- `training.target_model` 设为 SpatioTemporal2DMAE
