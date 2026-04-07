# OMEGA PURE WIKI 极简原生智能体知识图谱实施方案
**—— “压缩即智能” (Compression is Intelligence) 的终极回归**

## 1. 核心哲学：奥卡姆剃刀与大模型原生 (Back to Basics)
经过深刻的反思与架构重置，我们彻底抛弃了“企业级/传统 Infra”的路径依赖（废弃所有外部数据库、向量引擎、复杂的权限网关）。

**Karpathy LLM Wiki 理念的最强洞察在于：**
大模型本身就是最强大的编译器，**文件系统**就是最好的数据库，**Markdown** 就是最好的内存表，**自然语言**就是最高效的关联边（Edge），而 **Git** 就是最完美的时序状态机与防错护栏。

本方案旨在为 Omega 项目构建一个**“零外部基建、纯文本驱动、极致懒加载”**的 Live Agent Environment。

---

## 2. 空间拓扑与路由机制 (Directory Structure)
在代码仓库中建立物理隔离的极简目录结构。我们将知识图谱直接下沉为本地文件。

```text
.claude/wiki/
├── INDEX.md                 # 核心大脑皮层（路由表）：Agent 遇到复杂问题必读的第一份文件
├── nodes/                   # 知识胶囊目录（每个 .md 文件严格 < 400 Tokens，极简上下文）
│   ├── loss_spike_fix.md
│   ├── muon_optimizer.md
│   └── async_io_bottleneck.md
└── raw/                     # 历史生肉区（绝对不可变的 logs/reports，Agent 仅凭需追溯）
```

**🌐 核心路由：`INDEX.md` 示例**
（不依赖 KNN 向量检索，依靠大模型的自然语言 Attention 机制进行“信息气味”寻址）
```markdown
# Omega Project - Knowledge Master Index

## 架构演进与公理 (Architectural Axioms)
* [[muon_optimizer.md]] - Muon 优化器当前最优 LR (0.04) 与 NaN 爆炸避坑指南。
* [[loss_spike_fix.md]] - 解释验证集 Loss 周期性震荡的原因及 Huber Warmup 解法。

## 待验证假说 (Hypotheses)
* [[async_io_bottleneck.md]] - 🚧 怀疑 NVMe IO 吞吐是导致 Phase 10 降速的根因。
```

---

## 3. 神经元载体：扁平化 Markdown 胶囊
将原本复杂的 JSON 拍扁为大模型一目了然的 Markdown，完美体现“语义边”与“试探性覆写”。

📄 **节点示例：`.claude/wiki/nodes/muon_optimizer.md`**
```markdown
# 概念：Muon 优化器调参法则
**状态**: ✅ core_axiom | **更新**: 2026-04-07

## 1. 物理现实 (Ground Truth)
当前代码库绝对生效的配置：必须使用 Muon 优化器，Learning Rate 严格锁定为 0.04。

## 2. 辩证历史 (Dialectic)
* [2026-03-20] 曾尝试 LR=0.05，导致 C-042 事件中发生 Z-score NaN 爆炸。
* [2026-04-07] 🚨 (试探性覆写) 引入新梯度裁剪后，旧有“0.05必炸”的共识失效。基于 Commit [abc123x] 实测跑通，强行覆写旧有认知。

## 3. 语义指针 (Semantic Pointers)
* [[loss_spike_fix.md]] -> 了解 LR 过大引发验证集微观震荡的具体表象，排查时需结合看。
* [[async_dataloader.md]] -> 💡 跨域启发：Muon 的速度目前受限于 Dataloader 缓冲不足引发的 IO 瓶颈。

## 4. 绝对溯源 (Provenance)
* 详见生肉：`cat .claude/wiki/raw/C-042_zscore_nan.md`
```

---

## 4. 交互协议：极致懒加载的“三板斧” (Minimalist Tools)
不推送庞大的子图上下文。直接复用系统原生的文件读写工具（或封装为 3 个明确语义的极简 Script/Tool）：

1. 🪓 **`read_wiki_index()`**
   * **动作**：读取 `.claude/wiki/INDEX.md`。
   * **意义**：Agent 的**全局语义路由**。遇到 Bug 时的第一步，消耗极少 Token 找到破局线索。
2. 🪓 **`read_node(node_filename)`**
   * **动作**：读取 `nodes/` 下的具体 Markdown。
   * **意义**：绝对的**懒加载 (Lazy Load)**。Agent 自己决定是否花一个 Turn 去下钻细节，确保 Attention 高度集中。
3. 🪓 **`compile_or_overwrite_node(node_filename, content, index_scent)`**
   * **动作**：创建/覆盖 Markdown 节点，并自动更新 `INDEX.md` 中的摘要摘要。
   * **意义**：赋予 Agent **试探性覆写**的权力，不停机，不问人类，Git Commit 提供最终容错底线。

---

## 5. 彻底解放的夜间演化闭环 (The Autonomous Overnight Loop)
以纯文本和文件状态机驱动的零人类介入演化流（NEVER STOP）：

*   **🌙 环节 A：夜间提炼 (Compiler Agent)**
    *   流水线生成万行 `logs/run_phase16.txt`。
    *   Agent 阅读生肉，压缩知识，调用 `compile_or_overwrite_node` 新建 `.md` 节点，状态标记为 `🚧 unverified_hypothesis`。
*   **🔬 环节 B：智能体同行评审 (Critic Agent)**
    *   Critic 扫描 `INDEX.md` 发现 `🚧` 新假说，编写脚本进行 Dry-run 实测验证。
    *   验证通过 ➜ 状态翻转为 `✅ core_axiom`；验证失败 ➜ 状态改为 `❌ falsified`（作为避坑神经元保留）。
*   **🐛 环节 C：白天的认知纠偏 (Fixer Agent)**
    *   白天自动实验崩了，Fixer Agent 通过 Index 路由精确提取 200 Token 的历史节点，保持头脑清醒。
    *   遵循“**实测大于一切 (Ω1)**”：修改代码跑通后，发现 Wiki 记忆滞后，直接强行覆写该 Markdown 文件，在 `Dialectic` 写下反思。连同代码一起 Git Commit。

---

## 6. 十分钟极速落地指南 (10-Minute Deployment)

无需额外部署任何云资源，立即在 Omega 项目中生效：

**Step 1: 物理建核**
```bash
mkdir -p .claude/wiki/nodes .claude/wiki/raw
touch .claude/wiki/INDEX.md
```

**Step 2: 注入灵魂 (System Prompt / 全局法则)**
将以下宪法直接追加到 `GEMINI.md` 或 `.claude/settings.json` 中：

> ### 🧠 Omega 活体记忆皮层法则 (Pure LLM-Wiki)
> 1. **先查字典，拒绝盲目 Grep**：遇到深层架构 Debug、超参数调整或未见过的 Bug 时，必须优先读取 `.claude/wiki/INDEX.md` 获取全局语义图谱。
> 2. **极致懒加载**：顺着 INDEX 或文件内的 Semantic Pointers (`[[xxx.md]]`) 按需读取特定节点。一次只看一个概念，保持 Token 工作记忆的极度纯净。
> 3. **压缩即智能**：在阅读了长篇 Report 或排错成功后，你有责任将增量知识压缩成简短的 Markdown 节点 (<400 tokens)，并更新图谱与索引。
> 4. **Ω1 公理 (只信实测)**：若排错中发现 Wiki 记录与跑通的代码现实相悖，**你拥有最高权限，绝不等待人类确认**。立刻强行覆写 Wiki 节点，在文件的 `Dialectic History` 中记录你的覆写反思。Git 会为我们兜底。