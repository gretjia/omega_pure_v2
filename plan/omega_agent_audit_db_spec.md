# Omega 智能体原生审计数据库 (Agent-Native Audit Database) 设计方案
**—— Karpathy LLM Wiki 理念 × GCP Serverless 架构 终极融合版**

## 1. 核心理念融合：站在 Karpathy 的肩膀上
Andrej Karpathy 在其 "LLM Wiki" (Idea File) 中提出了一个深刻的洞察：**传统 RAG 每次都在“重新发现”知识（Stateless），而 LLM 应该作为“编译器”，把杂乱的原始输入（Raw）沉淀为结构化、相互链接的持久知识库（Wiki）**。

结合您的核心痛点（Agent 在大型项目中读取长文档导致 **Context Anxiety / 注意力衰减**），我们将 Karpathy 的“人工阅读 Wiki”升级为**“Agent 机器读取的神经元图谱”**。

*   **Karpathy 的 Raw 层** ➜ 您的 Immutable Traces (`/handover`, `/reports` 等生肉文件，绝对不删改，保留因果)。
*   **Karpathy 的 Pages 层** ➜ 我们的 **“6D 知识胶囊 (Atomic Concept Capsules)”**。不再是长篇大论的 Markdown，而是结构化的高密度 JSON/短文本，每次只给 Agent 喂几百 Token。
*   **Karpathy 的 Index 层** ➜ 我们的 **图谱路由与向量语义导航**。
*   **运维痛点** ➜ 采用 Google Cloud 个人开发者最友好的 Serverless 架构（Firestore + Native Vector Search）实现。

## 2. 架构全景：GCP 原生且免运维的最佳实践 (Solo Dev Architecture)

### 2.1 存储层与导航层合一：无服务器神经元仓库 (Google Cloud Firestore + Native Vector)
*   **极致降本（独立审计师修正）**：废弃独立的 Vertex AI Vector Search，全面拥抱 Firestore 原生 K-NN 向量检索。
*   **原理**: Firestore 是 Serverless NoSQL 数据库。每一个“6D 知识胶囊”就是一个 Firestore Document。我们将胶囊的 Embedding 向量直接存入文档的 `FieldValue.vector()` 字段。
*   **优势**: 
    *   单库免运维，告别双库同步延迟和两套 API 的心智负担。
    *   **混合检索 (Hybrid Search)**：支持先做 Metadata 标量过滤（如 `status == 'active'`），再做向量相似度计算。

### 2.2 动作网关：智能体突触 (Cloud Functions / Cloud Run)
*   **角色**: 作为 Agent 与底层数据库交互的中间件，对外暴露给 Agent 作为 Tool (基于 MCP 协议或普通函数调用)。
*   **核心原则：极致懒加载 (Strict Lazy Load)**
    *   坚守“Token 极简主义”：**不请求，不推送**。中间件绝不自作聪明地打包“子图”塞给 Agent。Agent 每次只拿到 300 Token 的核心胶囊，强迫其专注当前节点，需要时再发起下一次 API 调用。

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
  "3_semantic_pointers": [ // 摒弃伪精确的浮点权重，使用自然语言上下文
    {"id": "concept_gradient_clipping", "context": "解决 NaN 爆炸的具体工程实现"},
    {"id": "concept_batch_size_limit", "context": "LR 与 Batch Size 的耦合约束关系"}
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
    "status": "core_axiom" // 状态机：unverified_hypothesis -> core_axiom -> falsified
  }
}
```

## 4. 原生智能体演化生命周期 (LLM-Native Agentic Evolution)

这套系统坚决摒弃“古典确定性软件工程”的防守型思维（如人类阻塞审批、停机神谕），全面拥抱“允许犯错与自我修剪”的生物学演化逻辑。

### 阶段一：摄取与智能体同行评审 (Agentic Peer Review)
1. **Human/System**: 跑完一次夜间训练，产生 `phase12_report.md`。
2. **Compiler Agent**: 读取报告，提取新概念写入 Firestore，标记为 `["status": "unverified_hypothesis"]`。
3. **Critic Agent (异步)**: 利用内置验证工具跑测试。测试通过则状态翻转为 `core_axiom`；失败则标记为 `falsified`（作为宝贵的避坑神经元保留）。**绝不阻塞夜间的自我演进。**

### 阶段二：按需审计与极简视野 (Surgical Audit)
1. **Fixer Agent**: 遇到疑难杂症。调用语义搜索，命中并提取单个核心胶囊（300 Token）。
2. **语义路由 (Semantic Routing)**: Agent 阅读 `3_semantic_pointers` 中的自然语言上下文（"Information Scent"），决定是否需要花费一个回合 (Turn) 去请求下一个胶囊。

### 阶段三：试探性覆写 (Tentative Overwrite) 与自我推翻
1. **现实冲突**: Fixer Agent 发现当前跑通的代码库配置与胶囊记录的 `Ground Truth` 相悖。
2. **Omega 元公理执行**: 坚守 Ω1（只信实测）。Agent **不宕机、不停机呼叫人类**。
3. **记忆覆写**: Agent 优先相信跑通的代码（现实），直接修正知识库，并在 `2_history_dialectic` 中追加记录：
   *“🚨 [2026-04-07] 认知冲突：旧记忆认为 X 必错，但当前实测证明其更优。旧公理受限于当时框架局限，已强行覆写。”*

## 5. 结语：从“静态档案库”到“数字活皮层”
*   **极致降本**：吸收 GCP Serverless 的务实建议，单库免运维，白嫖额度。
*   **原生演化**：系统拥有产生无用突触的权利（异步跑测修剪）、保持极小视野的权利（懒加载逼出深度推理）、以及记忆与现实冲突的权利（实测覆写完成范式转移）。
*   **效能爆发**：彻底终结 Context Anxiety，Overnight Loop 现可毫无阻碍起点火运行。