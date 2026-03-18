# OMEGA PURE — AI Agent 完整操作手册

本文档是新 AI agent 接手本项目的完整上手指南。包含项目架构、工作流自动化、工具链使用、安全红线的全面说明。

---

## 0. 快速启动清单

新 agent 开始工作前，必须完成以下步骤：

1. **`CLAUDE.md` 已自动加载** — 包含 49 条规则，覆盖物理公理、破坏性操作红线、工程规范
2. **读 `VIA_NEGATIVA.md`** — 10 条已证伪的路径，不可重蹈
3. **读 `handover/LATEST.md`** — 当前项目状态单一真相源
4. **读 `architect/current_spec.yaml`** — 当前张量规范和参数
5. **运行 `/axiom-audit`** — 验证环境公理完整性

完成这 5 步后，你对项目的理解就足够开始工作了。

---

## 1. 项目概述

### 做什么
量化金融研究项目。从 A股 L1 tick 数据中，使用拓扑注意力 + MDL 压缩提取机构主力行为信号。

### 核心数据流
```
A股 L1 Tick 数据 (2.2TB raw)
    ↓ ETL (Volume-Clock resampling)
Volume-Clocked 张量 [B, 160, 10, 7]
    ↓ WebDataset (.tar shards)
训练数据 → GCP Vertex AI (L4/A100)
    ↓ Finite Window Topological Attention + MDL Loss
机构行为信号
```

### 核心张量
- 形状：`[B, 160, 10, 7]` — Batch × Time × Spatial(LOB深度) × Features
- Features: `[Bid_P, Bid_V, Ask_P, Ask_V, Close, SRL_Residual, Epiplexity]`
- 规范来源：`architect/current_spec.yaml`

---

## 2. 不可违反的物理公理

### Layer 1: 永恒常数（不可修改，不可设为可学习参数）

| 常数 | 值 | 含义 |
|------|-----|------|
| δ (delta) | 0.5 | 平方根法则指数 I ∝ Q^δ |
| c (c_tse) | 0.842 | TSE 实证冲击系数 |
| POWER_INVERSE | 2.0 | 1/δ |

这些值硬编码在 `omega_axioms.py` 和 `omega_epiplexity_plus_core.py` 中。任何试图修改它们的操作都会被 hook 自动拦截。

### Layer 2: 架构参数（可演进，修改需用户确认）

| 参数 | 当前值 | 来源 |
|------|--------|------|
| tensor.time_axis | 160 | ACF 衰减上限 |
| tensor.spatial_axis | 10 | LOB 深度档位 |
| tensor.feature_axis | 7 | 特征维度 |
| etl.vol_threshold | 50000 | 冷启动默认值 |
| etl.window_size | 160 | 最大感受野 |
| etl.stride | 20 | 滑动窗口步长 |
| etl.adv_fraction | 0.02 | 动态阈值 = ADV × 此值 |
| training.lambda_s | 0.001 | MDL 结构惩罚权重 |

修改这些参数的流程：架构师指令 → `/architect-ingest` → 用户确认 → 更新 `current_spec.yaml` → `/axiom-audit` 验证

---

## 3. 文件地图

```
omega_pure_v2/
├── CLAUDE.md                              # 项目宪法（自动加载）
├── VIA_NEGATIVA.md                        # 已证伪路径（必读）
├── omega_axioms.py                        # 双层公理断言
├── omega_epiplexity_plus_core.py          # 数学核心（FROZEN）
├── omega_webdataset_loader.py             # WebDataset 加载器
│
├── architect/
│   ├── current_spec.yaml                  # 架构规范（单一真相源）
│   ├── INDEX.md                           # 架构师指令时间线
│   └── directives/                        # 指令归档
│
├── tools/
│   ├── omega_etl_v3_topo_forge.py         # V3 ETL（已暂停）
│   ├── etl_lazy_sink_linux_optimized.py   # V2 ETL（已弃用）
│   └── empirical_calibration.py           # 物理常数标定
│
├── handover/
│   ├── LATEST.md                          # 当前状态（单一真相源）
│   ├── README.md                          # 导航索引
│   ├── agent_manuals.md                   # ← 本文档
│   ├── HARDWARE_TOPOLOGY.md               # 硬件拓扑和 SSH 路由
│   ├── ETL_ENGINEERING_LESSONS.md         # 工程教训
│   ├── EXPERIMENTAL_DESIGN_AND_ROADMAP.md # 实验设计和路线图
│   └── V3_SMOKE_TEST_PLAN.md             # V3 烟测计划
│
├── audit/
│   └── gemini_bitter_lessons.md           # Gemini 灾难复盘
│
├── .claude/
│   ├── settings.json                      # 项目级 hooks 配置（提交到 git）
│   ├── settings.local.json                # 本地权限（不提交）
│   ├── hooks/
│   │   ├── block-destructive.sh           # PreToolUse: 拦截危险命令
│   │   ├── post-edit-axiom-check.sh       # PostToolUse: 编辑核心文件后自动公理检查
│   │   └── stop-guard.sh                  # Stop: 提醒未提交的核心变更
│   ├── skills/
│   │   ├── architect-ingest/SKILL.md      # /architect-ingest
│   │   ├── dev-cycle/SKILL.md             # /dev-cycle
│   │   ├── deploy-cycle/SKILL.md          # /deploy-cycle
│   │   ├── axiom-audit/SKILL.md           # /axiom-audit
│   │   ├── pre-flight/SKILL.md            # /pre-flight
│   │   └── node-health-check/SKILL.md     # /node-health-check
│   └── agents/
│       ├── recursive-auditor.md           # 递归审计员（opus, 只读）
│       ├── architect-liaison.md           # 架构师联络官（opus）
│       ├── infra-scout.md                 # 基础设施侦察（haiku）
│       └── deployment-guard.md            # 部署守卫（sonnet）
```

---

## 4. 自动化三层架构

### Layer 1: Hooks（无感自动化 — 你不需要做任何事）

Hooks 在 `.claude/settings.json` 中配置，由 Claude CLI 自动执行：

| Hook | 触发时机 | 做什么 | 退出码 |
|------|----------|--------|--------|
| `block-destructive.sh` | 每次执行 Bash 前 | 拦截 `rm -rf`、`git push --force`、`git reset --hard`、修改物理常数 | exit 2 = 阻止 |
| `post-edit-axiom-check.sh` | 每次 Edit/Write 后 | 如果修改了数学核心文件，自动运行 `omega_axioms.py` | exit 1 = 公理违规 |
| `stop-guard.sh` | Claude 结束回复时 | 检查核心文件是否有未提交变更，仅提醒不阻止 | 永远 exit 0 |

**数学核心文件**（触发 post-edit hook 的文件）：
- `omega_epiplexity_plus_core.py`
- `omega_axioms.py`
- `architect/current_spec.yaml`
- `tools/*etl*.py`
- `tools/*forge*.py`

### Layer 2: Skills（一键触发 — 用户主动调用）

| 命令 | 用途 | 关键阶段 |
|------|------|----------|
| `/architect-ingest` | 摄取架构师指令 | 归档 → 公理影响检测(3级) → 提议 spec 更新 |
| `/dev-cycle <描述>` | 完整开发周期 | Plan → Audit → Fix → Code → Audit → Fix → Axiom → Summary |
| `/deploy-cycle <节点>` | 部署到远程节点 | Pre-flight → Axiom → Health → Deploy → Verify → Document |
| `/axiom-audit` | 公理完整性验证 | 运行 `omega_axioms.py --verbose` + 交叉验证 |
| `/pre-flight` | 部署前预检 | 9 项 GO/NO-GO 检查 |
| `/node-health-check` | 集群健康检查 | SSH 巡检所有节点 |

### Layer 3: Agents（智能委托 — 需要推理判断的任务）

| Agent | 模型 | 职责 | 关键约束 |
|-------|------|------|----------|
| `recursive-auditor` | opus | 独立数学审计 | **只读**，不可修改任何文件 |
| `architect-liaison` | opus | 架构师指令生命周期 | 接收 ≠ 执行，spec 更新需确认 |
| `infra-scout` | haiku | 快速集群健康检查 | 纯只读 SSH 检查 |
| `deployment-guard` | sonnet | 部署门禁 | 任一检查失败 → NO-GO |

---

## 5. 标准工作流

### 工作流 A: 架构师指令 → 代码变更

这是最常见的工作流。架构师通过 Google Docs 发来指令，用户粘贴到对话中。

```
用户粘贴架构师指令
        ↓
/architect-ingest
  ├─ architect-liaison agent 摄取 + 归档到 architect/directives/
  ├─ 公理影响检测（自动）
  │   ├─ NO AXIOM IMPACT → 正常流转
  │   ├─ AXIOM UPDATE REQUIRED → 列出变更 → 用户确认 → 更新 spec → 验证
  │   └─ AXIOM VIOLATION → ⛔ 阻止（Layer 1 不可修改）
  ├─ 提议 spec 更新（diff 预览）→ 用户确认
  └─ 列出受影响的代码文件
        ↓
/dev-cycle <变更描述>
  ├─ Stage 1: Plan — 草拟实现计划（进入 Plan Mode）
  ├─ Stage 2: Audit Plan — recursive-auditor 审计计划对齐 spec
  ├─ Stage 3: Fix Plan — 如果审计失败，修正后重新审计（最多 3 次）
  ├─ Stage 4: Code — 退出 Plan Mode，执行代码变更
  │   └─ [PostToolUse hook 自动运行公理检查]
  ├─ Stage 5: Audit Code — recursive-auditor 审计代码
  ├─ Stage 6: Fix Code — 如果审计失败，修正后重新审计（最多 3 次）
  ├─ Stage 7: Axiom Check — python3 omega_axioms.py --verbose
  └─ Stage 8: Summary — 变更摘要，等待用户确认 commit
        ↓
用户确认 → git commit + push
```

### 工作流 B: 部署到远程节点

```
/deploy-cycle linux1
  ├─ Stage 1: Pre-flight — 9 项 GO/NO-GO（SSH, 磁盘, 内存, 进程, 依赖...）
  ├─ Stage 2: Axiom Audit — 确认代码公理完整
  ├─ Stage 3: Node Health — 集群健康报告
  ├─ Stage 4: Deploy — SCP + systemd-run（用户确认后执行）
  ├─ Stage 5: Verify — 确认进程运行 + 初始日志
  └─ Stage 6: Document — 更新 handover/LATEST.md
        ↓
用户确认 → git commit
```

### 工作流 C: 日常巡检

```
/node-health-check
  └─ SSH 到所有节点，输出结构化健康报告
```

---

## 6. 破坏性操作红线

以下操作必须获得用户**明确确认**，无例外：

| 操作 | 保护机制 |
|------|----------|
| 删除数据文件（.parquet, .tar, shard） | CLAUDE.md 规则 #10, #14 |
| 修改物理常数（δ, c） | Hook 自动拦截 + CLAUDE.md 规则 #11 |
| `git push` / SCP 到生产节点 | CLAUDE.md 规则 #12 |
| 修改 `architect/current_spec.yaml` | CLAUDE.md 规则 #13 |
| `rm -rf` | Hook 自动拦截 |
| `git push --force` / `git reset --hard` | Hook 自动拦截 |
| 同时运行多个 ETL 实例 | 单实例文件锁 fcntl.LOCK_EX |

### 被 Hook 拦截时怎么办
- Hook 拦截会在 stderr 显示 `BLOCKED: <reason>`
- **不要尝试绕过 hook**。重新考虑你的方法
- 如果你认为拦截是误判，告知用户让他们决定

---

## 7. 硬件拓扑和 SSH 路由

| 节点 | SSH 别名 | 角色 | 规格 |
|------|----------|------|------|
| omega-vm | (本机) | 控制节点 | GCP US, 16GB, 无 GPU |
| linux1 | `linux1-lx` | 重计算 | AMD AI Max 395, 128GB, 4TB+8TB |
| windows1 | `windows1-w1` | 重计算 | AMD AI Max 395, 128GB, 4TB+8TB |
| mac studio | `zephrymac-studio` | 架构师控制台 | Apple M4, 32GB |

从 omega-vm 连接：
```bash
ssh linux1-lx        # → linux1
ssh windows1-w1      # → windows1
ssh zephrymac-studio  # → mac studio
```

重计算任务必须使用：
```bash
ssh linux1-lx systemd-run --slice=heavy-workload.slice --scope python3 <script>
```

详细拓扑见 `handover/HARDWARE_TOPOLOGY.md`。

---

## 8. 公理检查系统

### omega_axioms.py

双层设计：
- **Layer 1**: 硬编码物理常数，`assert DELTA == 0.5` 级别的断言
- **Layer 2**: 从 `architect/current_spec.yaml` 动态加载架构参数，交叉验证代码

运行方式：
```bash
python3 omega_axioms.py           # 静默自检
python3 omega_axioms.py --verbose # 详细输出
```

### 何时运行公理检查

| 场景 | 谁运行 | 方式 |
|------|--------|------|
| 编辑核心文件后 | PostToolUse hook | 自动 |
| 开发周期末尾 | `/dev-cycle` Stage 7 | 自动 |
| 部署前 | `/deploy-cycle` Stage 2 | 自动 |
| 手动验证 | 用户 | `/axiom-audit` |
| 架构变更后 | `/architect-ingest` | 自动 |

---

## 9. VIA NEGATIVA 速查

这些是已经付出真实代价证伪的路径，**绝不重蹈**：

1. **Wall-Clock 时间轴** → 拓扑撕裂（必须用 Volume-Clock）
2. **拍扁空间轴 [160,7]** → 维度坍缩（必须保持 [B,T,S,F] 四维）
3. **固定绝对容量阈值** → 大小盘不可比（必须动态 ADV×2%）
4. **Tumbling 不重叠窗口** → 信息腰斩（必须滑动窗口 stride=20）
5. **gc.collect() 紧密循环** → 56% 性能回退
6. **use_threads=True 无条件使用** → 反优化
7. **SSH 继承 oom_score_adj=-1000** → 内核死锁
8. **双实例 ETL** → 内存翻倍 OOM
9. **AI 自测自验** → 自洽性掩盖正确性
10. **接收指令即执行** → 188GB 数据丢失

完整分析见 `VIA_NEGATIVA.md`。

---

## 10. 用户画像

- **独狼量化研究员**，零编程基础 vibe coder
- 优势是品味、市场洞察、Taleb 反脆弱哲学
- **中文为主**，技术术语可用英文
- 代码解释需要**简明扼要**，避免过度技术化
- 不要给出时间估算
- 不要过度工程化 — 简单 > 聪明

---

## 11. 常见操作快速参考

### 检查项目状态
```bash
python3 omega_axioms.py --verbose  # 公理检查
git status                          # 文件变更
git log --oneline -10               # 最近提交
```

### 读取关键配置
```bash
cat architect/current_spec.yaml     # 当前架构规范
```

### 远程节点快查
```bash
ssh linux1-lx free -h               # linux1 内存
ssh linux1-lx df -h /               # linux1 磁盘
ssh linux1-lx ps aux | grep python  # linux1 Python 进程
```

### ETL 启动（需用户确认 + pre-flight）
```bash
# 先 /pre-flight，通过后：
ssh linux1-lx systemd-run --slice=heavy-workload.slice --scope \
  python3 /path/to/omega_etl_v3_topo_forge.py
```

---

## 12. 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| Hook 拦截了你的命令 | 触发了危险模式匹配 | 不要绕过，重新考虑方法 |
| `omega_axioms.py` 失败 | Layer 1 常数被修改 或 spec 不一致 | 检查 `git diff`，回滚修改 |
| SSH 超时 | 节点离线或网络问题 | 运行 `/node-health-check` 诊断 |
| ETL OOM | 内存不足或双实例 | 检查 `ps aux`，确认单实例锁 |
| 审计循环超 3 次 | 计划/代码与 spec 深度冲突 | 暂停，征求用户意见 |
| `current_spec.yaml` 与代码不一致 | 架构变更未同步 | 运行 `/architect-ingest` 重新同步 |
