# Omega 智能体原生审计数据库 (Agent-Native Audit Database) 设计方案
**—— Karpathy LLM Wiki 理念 × GCP Serverless 架构 终极融合版**

## 1. 核心理念融合：站在 Karpathy 的肩膀上
Andrej Karpathy 在其 "LLM Wiki" (Idea File) 中提出了一个深刻的洞察：**传统 RAG 每次都在“重新发现”知识（Stateless），而 LLM 应该作为“编译器”，把杂乱的原始输入（Raw）沉淀为结构化、相互链接的持久知识库（Wiki）**。

结合您的核心痛点（Agent 在大型项目中读取长文档导致 **Context Anxiety / 注意力衰减**），我们将 Karpathy 的“人工阅读 Wiki”升级为**“Agent 机器读取的神经元图谱”**。

*   **Karpathy 的 Raw 层** ➜ 您的 Immutable Traces (`/handover`, `/reports` 等生肉文件，绝对不删改，保留因果)。
*   **Karpathy 的 Pages 层** ➜ 我们的 **“6D 知识胶囊 (Atomic Concept Capsules)”**。不再是长篇大论的 Markdown，而是结构化的高密度 JSON/短文本，每次只给 Agent 喂几百 Token。
*   **Karpathy 的 Index 层** ➜ 我们的 **图谱路由与向量语义导航**。
*   **运维痛点** ➜ 采用 Google Cloud 个人开发者最友好的 Serverless 架构（Firestore + Vertex AI Vector Search）实现。

## 2. 架构全景：GCP 原生且免运维的最佳实践 (Solo Dev Architecture)
对于个人开发者，我们需要追求 **GraphRAG 的先进性** 与 **Serverless 的轻量化** 的完美平衡。这套方案零闲置成本、零服务器维护。

### 2.1 存储层：无服务器神经元仓库 (Google Cloud Firestore)
*   **角色**: 替代传统的沉重图数据库（如 Neo4j）。
*   **原理**: Firestore 是 Serverless NoSQL 数据库。每一个“6D 知识胶囊”就是一个 Firestore Document。图谱中的“边（Edge）”只需在 Document 的一个 Array 字段中存入其他 Document 的 ID（如 `derived_pointers: ["id_A", "id_B"]`）。
*   **优势**: 毫秒级按 ID 提取，天然支持高并发，个人开发者几乎永远在免费额度内。

### 2.2 导航层：语义与向量引擎 (Vertex AI Vector Search)
*   **角色**: 替代 Karpathy 架构中简单的 `index.md`，实现模糊概念的精准定位。
*   **原理**: 当 Agent 不知道具体 ID，只询问模糊概念（如“之前那个优化器 OOM 的事”）时，系统调用 Vertex AI 的 Embedding 模型，在 Vector Search 中瞬间匹配出对应的 Firestore Document ID。

### 2.3 动作网关：智能体突触 (Cloud Functions / Cloud Run)
*   **角色**: 作为 Agent 与底层数据库交互的中间件，对外暴露给 Agent 作为 Tool (基于 MCP 协议或普通函数调用)。
*   **接口**:
    *   `query_concept(query: str)`: 语义搜索入口。
    *   `get_capsule(id: str)`: 按 ID 精确提取。
    *   `ingest_raw_to_capsule(raw_path: str)`: (对应 Karpathy 的 Ingest) 将新的原始报告提炼为新胶囊写入。

## 3. 核心载体：6D 知识胶囊 (The 6D Atomic Concept Capsule)
当 Agent 查询 `Muon_Optimizer_Tuning` 时，Firestore 返回以下结构，彻底终结 Context Anxiety：

```json
{
  "capsule_id": "concept_muon_optimizer_tuning",
  "1_ground_truth": {
    "desc": "当前绝对生效的配置：learning_rate 0.04，处于 active_in_phase12 阶段。"
  },
  "2_history_dialectic": {
    "desc": "曾尝试 LR=0.05，在 C-042 事件中导致 NaN 爆炸，后退回 0.04。（防碎片化的辩证历史）"
  },
  "3_derived_pointers": [
    "concept_gradient_clipping", 
    "concept_batch_size_limit"
  ],
  "4_cross_domain_sparks": {
    "desc": "💡 提示：早期日志显示此配置与 [NVME I/O 吞吐带宽] 存在高频共现，排查性能请关注 I/O。"
  },
  "5_provenance_uri": [
    "raw_files/reports/phase11.md#L45-60",
    "raw_files/incidents/C-042_zscore_nan.md"
  ],
  "6_confidence_staleness": {
    "last_verified": "2026-03-20T10:00:00Z",
    "status": "valid"
  }
}
```
*(注：第5点 `provenance_uri` 是对抗 AI 幻觉和“碎尸化”底线，强制 Agent 随时可以找回 Karpathy 所说的 Raw Source)。*

## 4. 鲜活的交互生命周期 (The Live Environment Workflow)

### 阶段一：摄取与编织 (Ingest & Weave)
1. **Human**: 跑完一次训练，将 `phase12_report.md` 扔进 `raw/` 文件夹。
2. **LLM Compiler**: 触发后台函数。LLM 读取报告，提取出 3 个新概念（如新的 Loss 波动规律），在 Firestore 创建 3 个新的 6D 胶囊，并生成 Embedding 存入 Vertex AI。同时更新旧胶囊的 `derived_pointers` 指向新胶囊。

### 阶段二：按需审计 (Surgical Audit)
1. **Agent (Coder/Fixer)**: 遇到疑难杂症：“为何验证集 Loss 又波动了？”
2. **语义定位**: Agent 调用 `query_concept("validation loss spike")`，Vertex AI 返回最匹配的胶囊 ID `concept_loss_spike_v2`。
3. **极速提取**: Agent 拿到该胶囊（仅 300 Token），上下文绝对清爽。
4. **图谱游走 (Multi-hop)**: Agent 发现胶囊的 `derived_pointers` 提到了 `concept_data_pipeline_shuffle`，于是继续按 ID 提取这个新胶囊。
5. **回源求证**: 如果胶囊信息不够写代码，Agent 提取 `provenance_uri`，直接读取原始的 `phase11.md` 的那 15 行日志。

### 阶段三：自我演进 (Lint & Update)
1. **Agent (Fixer)**: 成功修复了 Bug，发现了一个关于硬件限制的新知识。
2. **反哺**: Agent 调用 `ingest_new_finding()`，在 Firestore 中长出一个新的神经元（胶囊），补全了系统的世界观。

## 5. 为什么这是最优解？
*   **精神内核对齐**：完美继承了 Karpathy 将 LLM 视作**“持久化编译器”**和**“重度链接的图谱维护者”**的理念，同时彻底纠正了“把原生逻辑总结成没用的废话”这一社区通病。
*   **Agent 效能爆发**：每次只需消化几百 Token 的结构化胶囊，消除“读到后面忘前面”的窘境，Multi-hop 推理能力拉满。
*   **极致 Solo 友好**：全套 Serverless (Firestore + Cloud Functions + Vertex AI Vector Search)，用完即销毁。极低的心智负担和成本，享受企业级 GraphRAG 的核心红利。