---
name: lesson-to-rule
description: "将新教训自动转化为可执行规则 — Meta-Harness V3 Ω4 amplifier"
user_invocable: true
---

# /lesson-to-rule — 教训→规则 自动转化

> Ω4 的终极形态: 每条教训不只被记录, 还被编码为自动防护。
> Meta-Harness 论文: raw traces + executable enforcement >> compressed summaries

## 输入

`/lesson-to-rule <C-xxx>` 或 `/lesson-to-rule` (自动检测最近新增的未执法教训)

## 流程

### Stage 1: 读取事件上下文

1. 读取 `incidents/C-xxx_*/meta.yaml` — 获取 pattern, axiom, severity
2. 读取 `incidents/C-xxx_*/trace.md` — 获取完整执行记录
3. 读取 `incidents/C-xxx_*/root_cause.md` — 获取因果链
4. 如果 incidents/ 中没有此事件 → **自动创建 trace 目录**:
   a. 从 `OMEGA_LESSONS.md` 读取 2 行摘要
   b. 从 `git log --all --oneline --grep="C-xxx"` 提取相关 commit
   c. 创建 `incidents/C-xxx_<slug>/` 包含:
      - `meta.yaml` — 从摘要推断 pattern/axiom/severity
      - `trace.md` — 从 git show 重建执行上下文 (尽可能丰富)
      - `root_cause.md` — 从摘要提取 WHY chain
      - `resolution.md` — 从 git diff 提取修复内容
   d. 更新 `incidents/INDEX.yaml`
   e. 这样新教训自动迁移到 Trace Vault, 无需人工操作

### Stage 2: 分类失败模式

将事件归入已知模式:
- `config_sync` — 配置/默认值不同步
- `dimension_coupling` — 量纲/维度耦合变更
- `deploy_alignment` — Docker/部署与代码不对齐
- `io_strategy` — I/O 存储策略错误
- `normalization` — 归一化/标准化病态
- `checkpoint_state` — Checkpoint 状态泄漏
- `validation_skip` — 验证缺失或自验证
- `parameter_coupling` — 参数耦合变更未联动
- `resource_guess` — 资源估算靠猜测
- `full_stack_sync` — 全栈变更未同步

### Stage 3: 搜索现有规则

```bash
grep -l "source_incidents.*C-xxx" rules/active/*.yaml
```

- 如果已有规则覆盖此事件 → 输出 "✅ 已有规则 R-yyy 覆盖此事件" → 结束
- 如果有同 pattern 的规则但不覆盖此事件 → 提议扩展现有规则 (加入 source_incidents)
- 如果没有 → 生成新规则

### Stage 4: 生成规则

生成 `rules/active/R-xxx_<slug>.yaml` 文件, 遵循 `rules/RULE_SCHEMA.yaml`。

**规则生成约束**:
1. **简约性** (Karpathy): 如果需要超过 3 个 grep 条件, 标记为 `type: complex` 并输出:
   - "⚠️ 此规则过于复杂, 建议人工判断而非自动执法。已创建为 warn 级别。"
2. **误报控制**: enforcement 默认为 `warn` (不是 `block`), 除非:
   - 事件 severity == critical
   - 事件 pattern 已重复出现 2+ 次 (related 事件数 ≥ 2)
3. **pattern 安全**: 生成的 grep pattern 不可触发 lesson-enforcer.sh 自身 (参考 R-002 的 pattern_ref 方案)

### Stage 5: 回归测试

对 trace vault 中所有事件运行新规则 (dry-run):

```bash
# 伪代码: 遍历 incidents/*/trace.md, 检查规则是否能 catch 目标事件
for incident in incidents/C-*; do
    # 提取 trace 中的代码片段
    # 运行新规则的 grep pattern
    # 记录: caught / missed / false_positive
done
```

- 必须 catch 目标事件
- false_positive 率 < 10%
- 输出测试报告

### Stage 6: 输出

```
=== LESSON-TO-RULE REPORT ===

事件: C-xxx — <title>
模式: <pattern_tag>
现有规则: <无 / R-yyy (扩展)>

生成规则: R-zzz
  文件: rules/active/R-zzz_<slug>.yaml
  检查: <grep pattern description>
  执法: <block / warn / log>

回归测试: <caught N / missed M / false_positive K>

等待用户确认: [Y/n]
```

**用户确认后**: 写入规则文件 + 更新 `incidents/C-xxx_*/meta.yaml` 的 `enforcement` 和 `rule_id` 字段。

### Stage 7: 更新 INDEX

更新 `incidents/INDEX.yaml` 中该事件的 enforcement 状态。

## 安全约束

- 规则生成但**不自动激活** — 必须等待用户确认 (Ω5: 生产者 ≠ 验证者)
- 规则总数 hard cap 50 条 — 超过则提议合并或退休
- 不修改现有 block 级规则 — 只能新增或扩展 warn 级
- block 级升级需要用户显式确认
