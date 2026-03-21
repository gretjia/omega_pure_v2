---
name: axiom-audit
description: 三层公理审计 — omega_axioms.py自检 + Codex recursive audit + Gemini数学审计
user-invocable: true
---

# Axiom Audit（三层公理审计）

三层独立验证，防止 AI 自测自验 (Bitter Lesson #7)。

## 步骤

### Layer A: omega_axioms.py 自检（37 项）

```bash
cd /home/zephryj/projects/omega_pure_v2 && python3 omega_axioms.py --verbose
```

验证内容：
- Layer 1 永恒物理公理: δ=0.5, POWER_INVERSE=2.0
- Layer 2 架构公理: 张量形状 [B,160,10,10], 特征 10 通道, ETL 参数
- Layer 2 扩展: training (Omega-TIB, λ_s, masking), target (VWAP forward return), HPO (FVU), backtest (payoff>3.0)
- Layer 2 新增: srl_calibration (OLS, per-stock c_i), model_architecture (4 层)
- 代码常数: SRL inverter (c_constant 或 c_friction), power_constant=2.0, torch.no_grad()

### Layer A+: Insight 一致性交叉验证

扫描 `architect/insights/INS-*.md` 中所有 `status: active` 的洞察，验证：
- 每个 insight 声明的 `axiom_impact` 与 `current_spec.yaml` 当前状态一致
- `影响文件` 中列出的文件确实存在且反映了裁决内容
- 无冲突洞察（两个 active insights 对同一参数有矛盾裁决）

```bash
# 快速检查: 列出所有 active insights 及其 axiom_impact
grep -l "status: active" architect/insights/INS-*.md | while read f; do
  echo "$(grep '^id:' $f | awk '{print $2}') | $(grep '^axiom_impact:' $f | awk '{print $2}') | $(grep '^title:' $f | cut -d: -f2-)"
done
```

### Layer B: Codex Recursive Audit（spec↔code 一致性）

仅在以下情况触发：
- 修改了 `current_spec.yaml`
- 修改了数学核心 (`omega_epiplexity_plus_core.py`)
- 修改了 ETL (`omega_etl_v3_topo_forge.py`)
- 修改了 Loader (`omega_webdataset_loader.py`)
- 新增了架构师指令

```bash
codex exec --full-auto "Read architect/current_spec.yaml and architect/gdocs/id*.md. Cross-check against <变更文件>. Output PASS/FAIL per check."
```

### Layer C: Gemini 数学推理审计

仅在以下情况触发：
- 修改了物理公式相关代码
- 修改了损失函数
- 修改了 SRL 反演逻辑
- 新增了数学模块

```bash
cat <变更文件> | gemini -p "纯数学推理审计: <具体检查项>。PASS/FAIL + 数学理由。"
```

## 输出格式

```
=== OMEGA AXIOM AUDIT (3-LAYER) ===

[Layer A] omega_axioms.py: PASS (37/37 checks)
[Layer B] Codex recursive: PASS / SKIP (无 spec 变更)
[Layer C] Gemini math: PASS / SKIP (无数学变更)

FINAL: PASS / FAIL
```

## 失败处理

- **Layer A FAIL**: 物理常数或架构参数违规 — 立即停止
- **Layer B FAIL**: spec 与代码不一致 — 需要修复对齐
- **Layer C FAIL**: 数学推导错误 — 需要架构师介入

## 工具参考

- `codex exec`: OpenAI Codex CLI (GPT 5.4 xhigh)，默认模型即可
- `gemini -p`: Google Gemini CLI，通过 stdin 传入代码，-p 指定 prompt
- `gdocs read <id>`: 读取 Google Docs 原文（架构师指令源）
