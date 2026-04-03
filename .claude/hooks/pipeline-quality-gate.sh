#!/bin/bash
# pipeline-quality-gate.sh — Living Harness Pipeline Nervous System
# PostToolUse hook: 在写入关键管线文件后，检查质量门禁
#
# 监控 3 类文件:
#   1. architect/insights/INS-*.md → 检查必填 section 完整性
#   2. architect/current_spec.yaml → 检查 DRAFT 字段是否过期
#   3. OMEGA_LESSONS.md → 触发失败回溯 (链接到 chain_of_custody)
#
# 不阻止操作 (exit 0)，只注入上下文提醒

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || echo "")

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

cd /home/zephryj/projects/omega_pure_v2 2>/dev/null || exit 0

# ════════════════════════════════════════════════════════════
# Gate 1: INS 完整性检查
# ════════════════════════════════════════════════════════════
if echo "$FILE_PATH" | grep -qE "architect/insights/INS-.*\.md$"; then
    # 获取文件内容 (从 hook input, 因为 PostToolUse 时文件已写入)
    INS_CONTENT=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin).get('tool_input', {})
print(d.get('content', '') + d.get('new_string', ''))
" 2>/dev/null || echo "")

    # 如果 hook input 没内容, 尝试读文件
    if [ -z "$INS_CONTENT" ] && [ -f "$FILE_PATH" ]; then
        INS_CONTENT=$(cat "$FILE_PATH")
    fi

    if [ -n "$INS_CONTENT" ]; then
        MISSING=""

        echo "$INS_CONTENT" | grep -q "## 前提假设" || MISSING="${MISSING} [前提假设]"
        echo "$INS_CONTENT" | grep -q "## 被拒绝的替代方案" || MISSING="${MISSING} [被拒绝的替代方案]"
        echo "$INS_CONTENT" | grep -q "## 验证协议" || MISSING="${MISSING} [验证协议]"
        echo "$INS_CONTENT" | grep -q "## 参数标定来源" || MISSING="${MISSING} [参数标定来源]"
        echo "$INS_CONTENT" | grep -q "## 裁决" || MISSING="${MISSING} [裁决]"
        echo "$INS_CONTENT" | grep -q "## 影响文件" || MISSING="${MISSING} [影响文件]"

        if [ -n "$MISSING" ]; then
            INS_ID=$(basename "$FILE_PATH" .md | head -c 7)
            echo ""
            echo "┌──────────────────────────────────────────────────────────┐"
            echo "│  LIVING HARNESS — INS QUALITY GATE                      │"
            echo "└──────────────────────────────────────────────────────────┘"
            echo ""
            echo "  $INS_ID 缺少以下 section:${MISSING}"
            echo ""
            echo "  C-059 教训: 前提假设不写明 = 定时炸弹 (ETL 单位假设导致 9h GPU 浪费)"
            echo "  C-055 教训: 参数标定来源不标注 = 直觉阈值被当物理常数"
            echo ""
            echo "  → 请补充缺失 section 后继续"
            echo ""
        fi
    fi
fi

# ════════════════════════════════════════════════════════════
# Gate 2: Spec DRAFT 过期检查
# ════════════════════════════════════════════════════════════
if echo "$FILE_PATH" | grep -qE "architect/current_spec.yaml$"; then
    DRAFT_COUNT=$(grep -c "DRAFT" architect/current_spec.yaml 2>/dev/null || echo 0)
    if [ "$DRAFT_COUNT" -gt 0 ]; then
        echo ""
        echo "┌──────────────────────────────────────────────────────────┐"
        echo "│  LIVING HARNESS — SPEC DRAFT REMINDER                   │"
        echo "└──────────────────────────────────────────────────────────┘"
        echo ""
        echo "  current_spec.yaml 包含 $DRAFT_COUNT 个 [DRAFT] 字段"
        echo "  DRAFT 字段尚未经过外部审计验证 (C-059 教训)"
        echo "  → /dev-cycle Stage 8.5 审计通过后会自动 finalize"
        echo ""
    fi
fi

# ════════════════════════════════════════════════════════════
# Gate 3: 失败回溯触发 (lesson → chain of custody)
# ════════════════════════════════════════════════════════════
if echo "$FILE_PATH" | grep -qE "OMEGA_LESSONS"; then
    if [ -f "architect/chain_of_custody.yaml" ]; then
        # 提取最新 C-xxx 编号
        LATEST_C=$(grep -oP 'C-\d+' OMEGA_LESSONS.md 2>/dev/null | sort -t- -k2 -n | tail -1 || echo "")
        if [ -n "$LATEST_C" ]; then
            echo ""
            echo "┌──────────────────────────────────────────────────────────┐"
            echo "│  LIVING HARNESS — FAILURE TRACE BACK                    │"
            echo "└──────────────────────────────────────────────────────────┘"
            echo ""
            echo "  新教训 $LATEST_C 已记录。Living Harness 建议:"
            echo "  1. → /lesson-to-rule $LATEST_C (生成执法规则)"
            echo "  2. → 更新 architect/chain_of_custody.yaml"
            echo "       在相关 directive 的 failures 中追加:"
            echo "       - lesson: $LATEST_C"
            echo "         stage_failed: <哪个阶段出问题>"
            echo "         root_cause: <一句话根因>"
            echo "         assumption_violated: <哪个前提假设错了>"
            echo "  3. → 检查对应 INS 的'验证协议'是否需要更新"
            echo ""
        fi
    fi
fi

exit 0
