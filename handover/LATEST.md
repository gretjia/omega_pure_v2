# Omega Pure V3 - Project LATEST Handover State
Last Updated: 2026-04-05 — **STATUS: ETL v5 Sort 在 linux1 运行中 (5/743, ETA ~33h) | 全生命周期审计完成，Phase 14 协议已锁定**

## Current State
- **Phase 13 训练完成**: Job `6005517512886714368`, E9 best (Rank IC = +0.0292, D9-D0 = +7.00 BP)
- **ETL v5 Sort 运行中**: linux1 tmux `sort_v5`, DuckDB 外部排序, 5/743 files done, ~157-163s/file, ETA ~33h
- **ETL v5 代码已审计**: Gemini PASS (Plan + Code), Codex 部分完成 (无 blocking issue)
- **下游烟测已通过**: DuckDB 排序文件 → Scanner pushdown → ETL → shard → loader 全链 PASS
- **Pushdown 效果实测**: 5 symbols/1 file 从 37.6s → 0.8s (47× 加速, 99.6% 数据跳过)
- **Checkpoints**: `gs://omega-pure-data/checkpoints/phase13_v1/`

## Audit Session (2026-04-05)
- **审计底稿**: `reports/audits_and_insights/2026-04-05_omega_tib_audit_workpapers.md` (5-Agent 协作编制)
- **Session 总结**: `handover/2026-04-05_SESSION_AUDIT_SUMMARY.md` (全流程记录)
- **7 个疑点**: Phase 6 失效归因、窗口断裂、hd 理由链、post_proj_norm 幽灵层、7BP vs 25BP 鸿沟、SRL 遮蔽、FRT 审计盲区
- **"2.4% SNR" 证伪**: 来自 Phase 12 失败模型输出，非数据固有属性。已废除常数地位
- **新教训**: C-077 (伪常数传播), C-078 (三方审计元模式)
- **Phase 14 协议已锁定**: Step 0 数据基线 → Step 1 Phase 6 复测(三分支门) → Step 2 宏观旁路 A/B → Step 3 HPO hd=[64,128]
- **Phase 6 Checkpoint 已确认路径**: `gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt` (需 gsutil ls 验证存在)

## Changes This Session
- **ETL v5 性能重构** (未提交, `tools/omega_etl_v3_topo_forge.py`):
  - `pq.ParquetFile.iter_batches()` → `pyarrow.dataset.Scanner.to_batches(filter=...)` (row group pushdown)
  - VWAP: `bar_ticks_prices/vols` 列表 → `bar_vwap_num/bar_vwap_den` 标量累加 (减少 GC 压力)
  - 列裁剪: 44/49 列 | `.to_pylist()` 替代 `.to_pandas().values`
  - `--wait_for_files` pipeline 模式 (sort + ETL 并行)
  - `freeze_support()` Windows multiprocessing 修复
  - Checkpoint v1→v2 迁移逻辑
- **新文件 `tools/sort_parquet_by_symbol.py`**: DuckDB 外部排序, 原子写, 断点续传, 进度 JSON
- **新文件 `run_etl_v5_pipeline.py`**: Sort + ETL 流水线编排
- linux1 安装了 `duckdb 1.5.1`
- 停止并清理了 linux1 + windows1 的旧 ETL v4 进程和输出

## Key Decisions
- **预排序 + Scanner pushdown** (非单纯代码优化): 根因是 parquet 按日期组织, symbol 随机混排 → 每个 row group 跨全范围 → N workers = N× 全量 I/O。排序使 row group min/max 变紧 → 87% I/O 跳过
- **DuckDB 替代 PyArrow 排序**: PyArrow 全表 sort 峰值 ~55GB (32GB 机器 swap), DuckDB 外部排序内存可控 (40GB limit + disk spill)
- **linux1 而非 windows1**: windows1 只有 32GB RAM (96GB 分配给 GPU VRAM?), linux1 有 61GB
- **不并行排序**: benchmark 证明 2 并行 (各 20GB) 比单进程 (40GB) 慢 — ZFS I/O 带宽已被单进程打满
- **large_string → string 降级可接受**: DuckDB 将 4 个 string 列从 64-bit offset 降为 32-bit offset, 对 ≤10 字符的 symbol/date 安全

## Next Steps
### ETL v5 管线（进行中）
1. **[P0] 等待 Sort 完成**: ~33h, linux1 tmux `sort_v5`, 断点续传保护
2. **[P0] Sort 完成后启动 ETL v5**: `run_etl_v5_pipeline.py` 或直接 `omega_etl_v3_topo_forge.py --base_dir ...sorted --workers 8 --wait_for_files`
3. **[P0] ETL 完成后**: merge shards → QC → upload GCS (`wds_shards_v4`)

### Phase 14 协议（绝对串行，上一步未出结果前禁止触发下一步）
4. **[Step 0] 数据侧基线**: 在验证集上计算 Target 原生统计量 (Mean/Std/Skew/Kurtosis)，建立不依赖模型的 Ground Truth
5. **[Step 1] Phase 6 纯净复测**: 禁用 torch.compile，加载 `gs://omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt`
   - 前置: 确认 checkpoint 存在 + 解决模型类兼容性 (Phase 6: window=(4,4), hd=64, 无 AttentionPooling/Pre-LN)
   - Branch A (RankIC≤0.01 或 D9-D0≤2BP): Phase 13 确认为唯一基线 → Step 2
   - Branch B (RankIC>0.05 且 D9-D0>10BP): Stop the World，回滚研究小窗口
   - Branch C (灰区): 两路保留 → Step 2 + 多尺度窗口 Backlog
6. **[Step 2] 宏观旁路 A/B 实验**: σ_D + V_D 加入特征流形，成功标准=统计显著正向增量
7. **[Step 3] 受控 HPO**: hd=[64,128]，严禁 hd≥256

## Warnings
- **Sort ETA ~33h**: 每文件 73.6M 行 × 49 列, DuckDB 排序 ~160s/file, 不可加速 (I/O bound)
- **linux1 反向隧道不稳定**: 本 session 断连 5+ 次, 建议 autossh 或 `ServerAliveInterval=30`
- **windows1 Python314 包在 user site-packages**: SYSTEM 账户看不到, wrapper.cmd 需设 PYTHONPATH
- **windows1 multiprocessing 需要 freeze_support**: `run_etl_v5_pipeline.py` 已处理, 但直接调 `topo_forge_pipeline` 的脚本必须加 `if __name__ == '__main__': freeze_support()`
- **未提交代码在 omega-vm 本地**: `tools/omega_etl_v3_topo_forge.py`, `tools/sort_parquet_by_symbol.py`, `run_etl_v5_pipeline.py`
- **已排序文件占用空间**: 886MB/file × 743 = ~643GB, linux1 有 2.3TB free

## Remote Node Status
- **linux1**: Sort tmux `sort_v5` 运行中 (5/743, ~157s/file), 61GB RAM, 2.3TB free disk, duckdb 1.5.1
- **windows1**: 已清理 (旧进程/shards/scripts 已删除), 31.8GB RAM, 1.1TB free, ETL_V5_PIPELINE task 已注册但已停止

## Architect Insights (本次会话)
本次会话无新架构洞察 (纯工程优化)。核心发现:
- Parquet 数据布局是 I/O 放大的根因, 不是代码逻辑
- DuckDB 外部排序在 string 列上比 PyArrow 内存效率高 ~2×, 速度快 ~1.4×
- ZFS NVMe 单进程已打满 I/O 带宽, 并行排序无收益

## Machine-Readable State
```yaml
phase: "13_postflight_pending"
status: "etl_v5_sort_running"
sort:
  node: linux1
  method: "tmux sort_v5"
  engine: "duckdb 1.5.1"
  progress: "5/743 files"
  speed: "~160s/file"
  eta: "~33h from start (2026-04-05 14:41)"
  output: "/omega_pool/parquet_data/latest_base_l1_sorted"
  resume: true
  atomic_write: true
etl_v5:
  code_ready: true
  audits: "Gemini PASS, Codex partial (no blocking issues)"
  smoke_test: "PASS (pushdown 47× speedup)"
  deploy_pending: "after sort completes"
  uncommitted_files:
    - tools/omega_etl_v3_topo_forge.py
    - tools/sort_parquet_by_symbol.py
    - run_etl_v5_pipeline.py
windows1:
  status: "cleaned, idle"
  scheduled_task: "ETL_V5_PIPELINE (stopped)"
next_milestone: "Sort complete → ETL v5 → merge → GCS upload → Post-Flight"
```
