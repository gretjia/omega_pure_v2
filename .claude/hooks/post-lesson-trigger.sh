#!/usr/bin/env bash
# post-lesson-trigger.sh — PostToolUse hook (Meta-Harness V3)
# 当 OMEGA_LESSONS.md 被修改时, 提示 agent 自动运行 /lesson-to-rule
# 不阻止任何操作 (exit 0), 只注入上下文

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

# 只关注 OMEGA_LESSONS.md 的修改
case "$FILE_PATH" in
    *OMEGA_LESSONS*)
        # 检测是否有新的 C-xxx 编号被添加
        cd /home/zephryj/projects/omega_pure_v2

        # 提取 OMEGA_LESSONS.md 中最大的 C-xxx 编号
        LATEST_C=$(grep -oP 'C-\d+' OMEGA_LESSONS.md 2>/dev/null | sort -t- -k2 -n | tail -1 || echo "C-000")

        # 提取 incidents/INDEX.yaml 中已有的最大编号
        LATEST_IDX=$(grep -oP 'C-\d+' incidents/INDEX.yaml 2>/dev/null | sort -t- -k2 -n | tail -1 || echo "C-000")

        if [[ "$LATEST_C" != "$LATEST_IDX" ]]; then
            echo ""
            echo "┌──────────────────────────────────────────────────────────┐"
            echo "│  META-HARNESS V3 — NEW LESSON DETECTED                  │"
            echo "└──────────────────────────────────────────────────────────┘"
            echo ""
            echo "  新教训 $LATEST_C 已添加到 OMEGA_LESSONS.md"
            echo "  → 自动运行 /lesson-to-rule $LATEST_C 将教训转化为可执行规则"
            echo "  → 同时创建 incidents/$LATEST_C 完整 trace 目录"
            echo ""
        fi
        ;;
esac

exit 0
