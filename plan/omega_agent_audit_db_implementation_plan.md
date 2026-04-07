# Omega 智能体原生审计数据库 (Agent-Native Audit Database) 完整开发与实施规范 (Implementation SPEC & PLAN)

## 1. 工程目标与架构准则 (Engineering Objectives)
*   **目标**：将《Omega 智能体原生审计数据库设计方案》落地为可执行的代码与云端基础设施。构建一个 Serverless、以 Firestore 为核心、大模型原生的 6D 知识胶囊图谱。
*   **核心法则**：
    1. **Token 极简主义**：懒加载，绝不主动推送多余上下文。
    2. **演化优于静态**：支持智能体的试探性覆写（Tentative Overwrite）与假说测试。
    3. **零运维单库**：使用 Firestore 原生向量检索，废弃 Vertex AI Vector Search 独立实例。

## 2. 技术栈与 GCP 资源映射 (Tech Stack & Cloud Resources)

| 组件 | 技术选型 | 说明 / 角色 |
| :--- | :--- | :--- |
| **存储与图谱引擎** | **Google Cloud Firestore** | 存储 6D 知识胶囊 (JSON Document)。使用 `FieldValue.vector()` 原生存储 Embedding。 |
| **向量生成** | **Vertex AI Embeddings API** | 使用 `text-embedding-004` (或最新多模态模型) 将自然语言转化为高维向量。 |
| **Agent 工具网关** | **Python (本地 Tools) / MCP** | 由于单人开发环境，首期不部署 Cloud Functions，而是直接将接口写成 Python 脚本放在 `tools/audit_db/` 目录下，供大模型作为本地 Tool (或 MCP Server) 随时调用。 |

## 3. 数据库 Schema 设计 (Firestore Data Model)

**Collection Name**: `omega_knowledge_capsules`

**Document Structure (6D Capsule)**:
```typescript
interface KnowledgeCapsule {
  // 基础元数据
  id: string;                      // 例如: "concept_learning_rate_schedule"
  concept_name: string;            // 人类可读的概念名称
  created_at: Timestamp;
  updated_at: Timestamp;
  status: "unverified_hypothesis" | "core_axiom" | "falsified";

  // 1. Ground Truth (当前绝对生效的现实)
  ground_truth: string;            // 例如: "LR=0.04, 采用 Muon 优化器"

  // 2. History & Dialectic (辩证历史：打脸与覆写记录)
  history_dialectic: string[];     // Array of strings, 追加记录。例: ["[2026-04-07] 旧共识 LR=0.05 导致 NaN，已覆写"]

  // 3. Semantic Pointers (自然语言语义边 - The Graph)
  semantic_pointers: {
    target_id: string;             // 指向其他 Capsule 的 ID
    context_scent: string;         // "Information Scent" - 例: "解决 NaN 的底层裁剪机制"
  }[];

  // 4. Cross-Domain Sparks (交叉启发)
  cross_domain_sparks: string;     // 自动或半自动生成的弱连接提示

  // 5. Provenance URI (绝对溯源 - 防幻觉底线)
  provenance_uris: string[];       // 原始文件定位: ["/reports/phase11.md#L45-60"]

  // 向量场 (Firestore Native Vector)
  embedding_vector: VectorValue;   // 维度基于 Vertex AI 模型 (例如 768 或 1536 维)
}
```

## 4. 智能体交互工具接口 (Agent Tool Definitions)

这些工具将存放在 `tools/audit_db_client.py` 中，通过标准的 JSON Schema 提供给大模型。

### Tool 1: `query_capsule_by_semantics(query: str, status_filter: str = "all") -> str`
*   **用途**：Agent 遇到模糊概念时的首选入口（语义路由）。
*   **逻辑**：
    1. 调用 Vertex AI 生成 `query` 的 Embedding。
    2. 在 Firestore 执行 KNN 向量检索：`collection.where("status", "in", filter).find_nearest("embedding_vector", query_embedding, limit=1)`
*   **返回**：**仅返回最匹配的 1 个** 6D 胶囊 JSON（严守懒加载和 Token 极简法则）。

### Tool 2: `get_capsule_by_id(capsule_id: str) -> str`
*   **用途**：Agent 在阅读胶囊的 `semantic_pointers` 后，决定顺藤摸瓜跳向下一个节点。
*   **逻辑**：Firestore 直接 `get()`。

### Tool 3: `ingest_hypothesis(concept_name: str, ground_truth: str, provenance: list, pointers: list) -> str`
*   **用途**：夜间循环 (Overnight Loop) 产生新知识时，Compiler Agent 将新发现提炼并写入。
*   **逻辑**：
    1. 自动生成 Embedding。
    2. 写入 Firestore，强制默认 `status = "unverified_hypothesis"`。
*   **返回**：新建的 `capsule_id`。

### Tool 4: `tentative_overwrite(capsule_id: str, new_truth: str, dialectic_entry: str, source_commit: str) -> str`
*   **用途**：实现核心法则 Ω1（实测大于一切）。当 Agent 发现旧胶囊与当前跑通的代码现实冲突时调用。
*   **逻辑**：
    1. 更新该胶囊的 `ground_truth = new_truth`。
    2. 将 `dialectic_entry` 追加到 `history_dialectic` 数组中。
    3. 更新 `updated_at`。
*   **返回**：覆写成功状态。

### Tool 5: `falsify_axiom(capsule_id: str, reason: str) -> str`
*   **用途**：Critic Agent 在异步跑测失败后，将某个假说或公理标记为错误（避坑神经元）。
*   **逻辑**：更新 `status = "falsified"`，并在 history 中追加 `reason`。

## 5. 分阶段开发路线图 (Phased Implementation Plan)

### Phase 1: 基建与脚手架 (Infrastructure Setup) - 预计 1 天
*   [ ] **GCP 准备**: 
    *   在 Google Cloud Console 中初始化 Firestore (Native Mode)。
    *   开启 Vertex AI API，获取 `text-embedding-004` 权限。
*   [ ] **本地认证**: 配置 `gcloud auth application-default login`，确保本地 Python 脚本能免秘钥直连 Firestore。
*   [ ] **脚手架编写**: 在 `tools/audit_db/` 目录下创建基础 DB 客户端类，封装 Firestore 读写和 Vector API。

### Phase 2: 核心工具实现 (Tool Implementation) - 预计 1-2 天
*   [ ] **Tool 编写**: 完成上述 5 个 Tool 的 Python 函数实现。
*   [ ] **Schema 对齐**: 确保每次写入都能严格遵循 6D 胶囊的 JSON 结构，拒绝 LLM 吐出多余的 slop。
*   [ ] **CLI 测试**: 编写一个简单的 CLI 测试脚本，手动模拟一轮：写入胶囊 -> 向量查询 -> ID 提取 -> 覆写打脸。

### Phase 3: 冷启动与种子神经元注入 (Cold Start & Seeding) - 预计 1 天
*   *策略：坚决不写批处理脚本扫描上万行老日志。*
*   [ ] **人工指挥 Agent**: 在聊天窗口中，指示 Agent 查阅 `/incidents/C-042_zscore_nan.md` 和 `phase15_step2_mlp_config.yaml` 等 5 个最具代表性的转折点。
*   [ ] **生成种子**: 要求 Agent 调用 `ingest_hypothesis`，生成首批约 10-15 个具有极高密度和历史辩证价值的核心种子胶囊。

### Phase 4: 原生智能体闭环集成 (Autonomous Loop Integration) - 预计 2 天
*   [ ] **系统 Prompt 更新**: 在 `.claude/settings.json` 或 `GEMINI.md` 中，赋予全局 Agent 使用 `query_capsule_by_semantics` 的最高优先级。
    *   *Prompt 注入*：“遇到架构疑问时，严禁盲目 grep，必须先通过 semantic 工具查询 6D 知识图谱。阅读时保持极简视野，仅当你看到高价值的 Information Scent 时才进行下一次跳转。”
*   [ ] **夜间循环对齐**: 修改现有的 `safe_build_and_canary.sh` 或相关后置 Hook，在训练/评估完成后，自动触发 Compiler Agent 去提取新假说（调用 `ingest_hypothesis`）。

## 6. 验收标准 (Definition of Done)
1. **查询极致压缩**: 任意一次架构提问，系统能在一秒内返回单个 JSON（<500 tokens），且精准命中问题。
2. **多跳成功率**: Agent 能独立完成 `Semantic Search (找起始点)` -> `Read Pointer` -> `Get by ID (下钻)` 的二连跳逻辑。
3. **覆写测试**: Agent 在查阅一段陈旧的假说胶囊后，若被告知“最新代码已移除此特性”，它能自主调用 `tentative_overwrite` 将覆写历史记入图谱。