#!/usr/bin/env bash
# post-bash-error-tracker.sh — PostToolUseFailure + PostToolUse hook (Bash)
# Karpathy 原则: 错误发生时立刻记录，不攒到 session 结束
#
# 两种触发路径:
#   PostToolUseFailure (exit ≠ 0): JSON 有 error 字段，无 stdout/stderr
#   PostToolUse (exit = 0):        JSON 有 tool_response.stdout/stderr — 检测隐性错误模式
#
# 追踪文件: logs/session_errors.jsonl
# 兜底: /handover-update 会扫描此文件，处理遗漏

set -uo pipefail

INPUT=$(cat)
PROJECT_DIR="/home/zephryj/projects/omega_pure_v2"
TRACKER_FILE="$PROJECT_DIR/logs/session_errors.jsonl"

# --- 解析 JSON (兼容两种事件格式) ---
PARSED=$(echo "$INPUT" | python3 -c "
import sys, json

data = json.load(sys.stdin)
event = data.get('hook_event_name', '')
command = data.get('tool_input', {}).get('command', '')

if event == 'PostToolUseFailure':
    # 失败事件: 只有 error 字符串
    error_msg = data.get('error', 'unknown error')
    print(json.dumps({
        'command': command[:200],
        'is_failure': True,
        'error': error_msg[:400],
        'output': ''
    }))
else:
    # 成功事件: 有 stdout/stderr — 检测隐性错误
    resp = data.get('tool_response', {})
    stdout = resp.get('stdout', '') if isinstance(resp, dict) else str(resp)
    stderr = resp.get('stderr', '') if isinstance(resp, dict) else ''
    print(json.dumps({
        'command': command[:200],
        'is_failure': False,
        'error': '',
        'output': ((stderr or '') + ' ' + (stdout or ''))[-400:]
    }))
" 2>/dev/null) || exit 0

COMMAND=$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin)['command'])" 2>/dev/null || echo "")
IS_FAILURE=$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin)['is_failure'])" 2>/dev/null || echo "False")
ERROR_MSG=$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin)['error'])" 2>/dev/null || echo "")
OUTPUT=$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin)['output'])" 2>/dev/null || echo "")

# --- 排除噪声命令 ---
case "$COMMAND" in
    git\ status*|git\ diff*|git\ log*|git\ branch*) exit 0 ;;
    ls\ *|ls|cat\ *|head\ *|tail\ *|wc\ *) exit 0 ;;
    echo\ *|pwd*|which\ *|test\ *|date*|hostname*) exit 0 ;;
    df\ *|du\ *|free\ *|nvidia-smi*|pip\ list*|pip\ show*) exit 0 ;;
    \[\ *) exit 0 ;; # [ -f ... ] test
    chmod\ *) exit 0 ;;
    mkdir\ *) exit 0 ;;
esac

# --- 判定是否为需要记录的错误 ---
IS_ERROR=false
ERROR_SIGNAL=""

if [[ "$IS_FAILURE" == "True" ]]; then
    # PostToolUseFailure: 命令确实失败了
    IS_ERROR=true
    ERROR_SIGNAL="command_failed"
else
    # PostToolUse: 命令成功但检测隐性错误模式 (OOM, Traceback in subprocess 等)
    if echo "$OUTPUT" | grep -qiE "OOMKilled|CUDA out of memory|Segmentation fault|killed by signal|FATAL"; then
        IS_ERROR=true
        ERROR_SIGNAL="hidden_error_pattern"
    fi
fi

[[ "$IS_ERROR" != "true" ]] && exit 0

# --- 写入追踪文件 ---
mkdir -p "$PROJECT_DIR/logs"

SNIPPET="$ERROR_MSG"
if [[ -z "$SNIPPET" ]]; then
    SNIPPET=$(echo "$OUTPUT" | grep -iE 'Error|FAILED|Traceback|OOM|killed' | head -3 | head -c 300)
fi

python3 -c "
import json, datetime, sys

entry = {
    'ts': datetime.datetime.now().isoformat(),
    'command': sys.argv[1][:200],
    'signal': sys.argv[2],
    'snippet': sys.argv[3][:300],
    'recorded': False
}
with open(sys.argv[4], 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
" "$COMMAND" "$ERROR_SIGNAL" "$SNIPPET" "$TRACKER_FILE" 2>/dev/null

# --- 统计未记录数 ---
UNRECORDED=$(python3 -c "
import json
count = 0
try:
    with open('$TRACKER_FILE') as f:
        for line in f:
            if not line.strip(): continue
            e = json.loads(line)
            if not e.get('recorded', False): count += 1
except: pass
print(count)
" 2>/dev/null || echo "?")

# --- 即时提醒 ---
echo ""
echo "⚡ ERROR DETECTED — 立刻记录教训 (Karpathy 原则)"
echo "  命令: ${COMMAND:0:60}"
echo "  信号: $ERROR_SIGNAL"
if [[ -n "$SNIPPET" ]]; then
    echo "  摘要: ${SNIPPET:0:80}"
fi
echo "  本 session 累计 $UNRECORDED 个未记录错误"
echo "  → 写入 OMEGA_LESSONS.md (C-XXX) + /lesson-to-rule"

exit 0
