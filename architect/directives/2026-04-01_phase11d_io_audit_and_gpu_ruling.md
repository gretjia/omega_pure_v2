# Gemini 审计：Phase 11d I/O 策略 + 多 GPU 加速裁决

**日期**: 2026-04-01
**来源**: Gemini CLI 独立审计（对话内粘贴）
**公理影响**: NONE — 操作性审计 + 架构指导，无 spec 参数变更

---

## Part 1: Phase 11d 全栈 GCS I/O 审计

### ✅ 训练任务：pd-ssd Staging 是唯一正确策略
- **审查对象**: gcp/phase11d_config_A.yaml & B.yaml
- **配置**: 1300GB pd-ssd，启动后 gcloud storage cp 拉取 556GB 数据
- **结论**: Safe & Optimal
- **物理推演**: 20 Epoch × 556GB = 11.1TB GCS Egress（Pipe 模式不可接受）。Vertex AI 不支持 Local NVMe SSD (C-041)。开局 15-30 min staging 摊薄到 20 Epoch 极速 I/O 中是数学唯一解。

### 🚨 推理任务（Post-Flight）：全量落盘是 P0 灾难
- **审查对象**: gcp/gen_inference_config.sh
- **结论**: P0 Violation（但不阻塞 Phase 11d 训练发射）
- **修复方向**: 推理必须重写为 Pipe 模式（gs:// 直传 WebDataset），100GB 启动盘

### 🚨 Pipe 模式死锁：glob.glob() 不解析 gs://
- **审查对象**: tools/phase7_inference.py (L205) & backtest_5a.py (L115)
- **结论**: P0 Violation（但不阻塞训练）
- **修复方向**: 用 GCS API 替代 glob.glob()，支持 gs:// 路径

### ✅ Spot VM 防御: ckpt_every_n_steps=500 — Safe (C-018)
### ✅ 纯 FP32: --no_amp — Safe（19.7K 极小模型 AMP 反向优化）
### ⚠️ P1: backtest_5a.py 用 wds.decode() 而非 fast_npy_decoder — 浪费 15% CPU

---

## Part 2: 多 GPU 加速裁决 — 严禁

### 结论：19.7K 参数模型严禁多卡分布式训练

**原因 1: 通信开销悖论**
- 19.7K 参数量，前向/反向计算是微秒级
- DDP All-Reduce 通信延迟远超计算本身
- 4 张 GPU 有 90% 时间闲置等待梯度同步

**原因 2: I/O 饥饿墙**
- pd-ssd 吞吐受限于磁盘容量 (0.48 MB/s per GB)
- CPU DataLoader 刚好喂饱单张 T4/L4
- 4 GPU → 4x I/O 需求 → 触碰天花板

**原因 3: Batch Size 膨胀致质量坍塌**
- DDP 4 卡 → 有效 batch_size=1024（spec 锁定 256）
- 极小模型 + 极大 Batch → SGD 噪声被过度抹平 → Sharp Local Minima
- 需重新校准 lr（线性缩放），打乱 Phase 11d HPO 空间

**原因 4: 代码库无 DDP 支持**
- train.py 无 DistributedDataParallel / DistributedSampler
- 引入 DDP = 重写训练循环核心

### 正确加速路径：Scale-Up > Scale-Out
1. 升级单卡: n1-standard-8 (T4) → g2-standard-8 (L4)
2. 拉满 CPU: --num_workers = vCPU - 2

---

## 架构师决断矩阵

| 项目 | 状态 | 阻塞训练? |
|------|------|-----------|
| 训练 I/O (pd-ssd staging) | ✅ Safe | 否 |
| 推理 Pipe 模式 | 🚨 P0 | 否（训练后修） |
| glob.glob() gs:// | 🚨 P0 | 否（训练后修） |
| Spot 防御 | ✅ Safe | 否 |
| --no_amp | ✅ Safe | 否 |
| backtest fast_npy_decoder | ⚠️ P1 | 否 |
| 多 GPU DDP | ⛔ 禁止 | N/A |
