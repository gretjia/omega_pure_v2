---
name: harness-reflect
description: "Harness 自省循环 — 评估规则效果、发现缺口、提议改进"
user_invocable: true
---

# /harness-reflect — Meta-Harness V3 自我进化

> Karpathy autoresearch: propose → execute → evaluate → keep/discard → LOOP
> 没有反馈循环的 harness 只会膨胀, 不会进化。

## 触发时机

- 用户主动: `/harness-reflect`
- Session 结束时: stop-guard.sh 建议运行 (如果本 session 有新教训)
- 定期: 每 5 个 session 或每周一次

## 流程

### Stage 1: Inventory — 盘点

```
读取:
  - incidents/INDEX.yaml → 全部事件清单
  - rules/active/*.yaml → 全部活跃规则
  - rules/enforcement.log → 触发记录
  - OMEGA_LESSONS.md → 教训总数
```

输出:
```
=== HARNESS INVENTORY ===
事件总数: N (incidents/)
规则总数: M (rules/active/)
已执法事件: X / N (X%)
Doc-only 事件: Y
最近 30 天新增事件: Z
最近 30 天新增规则: W
```

### Stage 2: Gap Analysis — 缺口分析

遍历 incidents/INDEX.yaml, 找出 `enforcement: "doc_only"` 或 `enforcement: "none"` 的事件。

按 severity 排序, 输出 Top 5:

```
=== UNPROTECTED INCIDENTS (Top 5) ===
1. C-xxx [critical] — <title> — 无自动防护
2. C-yyy [high] — <title> — 无自动防护
...

建议: 对 Top 3 运行 /lesson-to-rule
```

### Stage 3: Effectiveness — 规则效果评分

遍历 rules/active/*.yaml, 计算每条规则的效果:

```python
for rule in rules:
    age_days = (today - rule.stats.created).days
    trigger_rate = rule.stats.times_triggered / max(age_days, 1)
    bypass_rate = rule.stats.times_bypassed / max(rule.stats.times_triggered + rule.stats.times_bypassed, 1)
    fp_rate = rule.stats.false_positives / max(rule.stats.times_triggered, 1)
```

**标记异常**:
- `trigger_rate == 0 且 age > 30 days` → "🔇 从未触发 — 候选退休或规则失效?"
- `bypass_rate > 0.5` → "⚠️ 绕过率 > 50% — 规则需要重写"
- `fp_rate > 0.2` → "⚠️ 误报率 > 20% — 规则太宽松"

输出效果报告表。

### Stage 4: Pattern Clustering — 重复模式检测

读取最近 10 个事件的 `root_cause.md`, 搜索是否有新的重复模式正在形成:

```
检查:
  - 同一 pattern 标签出现 3+ 次 → "⚠️ 模式聚集: <pattern>"
  - 同一文件涉及 3+ 个事件 → "⚠️ 热点文件: <file>"
  - 同一 axiom 违反 5+ 次 → "⚠️ 薄弱公理: <Ωx>"
```

### Stage 5: Pruning — 修剪提案

```
如果 rules/active/ 规则数 > 40:
  → 建议合并同 pattern 规则
  → 建议退休从未触发的旧规则 → 移到 rules/retired/

如果 OMEGA_LESSONS.md 案例库 > 80 条:
  → 建议归档已有完整 incidents/ 的旧条目 (保留编号引用)
```

### Stage 6: Harness Health Score

```python
enforcement_ratio = enforced_incidents / total_incidents
repeat_rate = repeated_patterns / total_incidents  
fix_commit_ratio = fix_commits_last_30d / total_commits_last_30d

health_score = enforcement_ratio * (1 - repeat_rate) * (1 - fix_commit_ratio)
# 范围 0.0 ~ 1.0
# 目标: > 0.7
```

输出:
```
=== HARNESS HEALTH SCORE ===

  执法覆盖率:  X% (目标 > 80%)
  重复模式率:  Y% (目标 < 10%)
  修复 commit 比: Z% (目标 < 15%)

  综合健康分: 0.XX → 趋势: ↑/↓/→
  
  上次评估: YYYY-MM-DD | 分数: 0.YY
```

### Stage 7: Pipeline Health（管线生命体征 — Living Harness 核心）

读取 `architect/chain_of_custody.yaml`, 评估管线健康:

```
=== PIPELINE HEALTH ===

管线总数: N (chain_of_custody.yaml)
阶段分布:
  ingested: X | ins_created: Y | spec_draft: Z | spec_final: W
  coded: A | audited: B | deployed: C | failed: D

INS 质量:
  完整 INS (6 section 齐全): M / N (M%)
  缺失最多的 section: [前提假设] (K 个 INS 缺失)

Spec 状态:
  DRAFT 字段数: X (最老 DRAFT: Y 天前)
  Spec-Code 漂移: `python3 tools/spec_code_alignment.py` → Z 个不对齐

失败回溯:
  有 failure 记录的管线: F 个
  失败根因分布:
    假设错误: X | 漂移: Y | 审计漏洞: Z | 其他: W
  最常被违反的 INS 假设类型: <数据格式 / 参数来源 / ...>
```

**关键指标**:
- **INS 完整率** < 80% → "⚠️ 信息在 ingest 阶段丢失, 下游会重蹈 C-059"
- **DRAFT 存活 > 7 天** → "⚠️ spec 假设未验证就在使用"
- **Spec-Code 漂移 > 0** → "⚠️ 代码与 spec 不一致, C-057 类风险"
- **失败管线 / 总管线 > 30%** → "⚠️ 管线失败率过高, 检查 ingest 质量"

### Stage 8: 行动建议

基于 Stage 1-7 全部分析, 输出具体行动建议 (最多 5 条):

```
=== RECOMMENDED ACTIONS ===

[规则层]
1. [优先] 为 C-xxx 创建规则 — /lesson-to-rule C-xxx
2. [可选] 退休 R-yyy (30 天未触发)

[管线层]
3. [优先] 补充 INS-xxx 的 [前提假设] section
4. [优先] Finalize spec DRAFT: <field> (已 DRAFT X 天)
5. [优先] 修复 spec-code 漂移: <param> spec=X code=Y
```

## 输出存储

每次运行的报告存储到 `rules/reflections/YYYY-MM-DD.md`, 用于追踪 harness 进化趋势。

## 安全约束

- 不自动删除规则 — 退休提案需用户确认
- 不自动升级 warn → block — 需用户确认
- 不修改 incidents/ 内容 — 只读
- 不修改 chain_of_custody 的 failures — 只读 (写入由其他 skill 负责)
- 健康分计算使用 `git log` 实测数据 (Ω1: 只信实测)
