#!/bin/bash
# rule-engine.sh — Meta-Harness V3: 数据驱动的规则引擎
# 替代 lesson-enforcer.sh 的硬编码规则
# 读取 rules/active/*.yaml 动态执行检查
#
# 设计原则 (Meta-Harness 论文):
#   - 规则定义与执行引擎分离
#   - 新教训 → 新 YAML → 自动生效 (无需修改此脚本)
#   - 每条规则可独立追踪效果 (stats)
#
# Hook 类型: PreToolUse (Edit|Write)
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

# ── 读取 hook 输入 ──
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")
CONTENT=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('tool_input',{})
print(d.get('content','') + d.get('new_string',''))
" 2>/dev/null || echo "")

# ── 无内容或无路径 → 放行 ──
if [[ -z "$FILE_PATH" ]] || [[ -z "$CONTENT" ]]; then
    exit 0
fi

# ── 文档/记忆/日志免检 ──
case "$FILE_PATH" in
    *.md|*/memory/*|*/OMEGA_LESSONS*|*/handover/*|*/directives/*|*/insights/*|*.log|*/incidents/*|*/rules/*|*/tests/test_harness_v3.py)
        exit 0 ;;
esac

# ── 项目根目录 ──
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RULES_DIR="$PROJECT_ROOT/rules/active"
LOG_FILE="$PROJECT_ROOT/rules/enforcement.log"

# 如果规则目录不存在，回退到旧 enforcer 逻辑
if [[ ! -d "$RULES_DIR" ]]; then
    exit 0
fi

ERRORS=()
WARNINGS=()

# ── 遍历所有活跃规则 ──
for rule_file in "$RULES_DIR"/*.yaml; do
    [[ -f "$rule_file" ]] || continue

    # 提取规则字段 (轻量 python 解析, 避免依赖 pyyaml)
    RULE_ID=$(python3 -c "
import sys
for line in open('$rule_file'):
    line = line.strip()
    if line.startswith('id:'):
        print(line.split(':', 1)[1].strip().strip('\"'))
        break
" 2>/dev/null || echo "unknown")

    ENFORCEMENT=$(python3 -c "
import sys
for line in open('$rule_file'):
    line = line.strip()
    if line.startswith('enforcement:'):
        print(line.split(':', 1)[1].strip().strip('\"'))
        break
" 2>/dev/null || echo "log")

    FILE_GLOB=$(python3 -c "
import sys
for line in open('$rule_file'):
    line = line.strip()
    if line.startswith('file_glob:'):
        val = line.split(':', 1)[1].strip().strip('\"')
        if val != 'null' and val != '\"*\"':
            print(val)
        break
" 2>/dev/null || echo "")

    PATTERN=$(RULE_FILE="$rule_file" PROJ_ROOT="$PROJECT_ROOT" python3 -c "
import os
rf = os.environ['RULE_FILE']
pr = os.environ['PROJ_ROOT']
for line in open(rf):
    line = line.strip()
    if line.startswith('pattern:') and 'pattern_ref' not in line:
        val = line.split(':', 1)[1].strip()
        if (val.startswith('\"') and val.endswith('\"')) or (val.startswith(chr(39)) and val.endswith(chr(39))):
            val = val[1:-1]
        val = val.replace(chr(92)+chr(92), chr(92))  # unescape \\\\→\\
        if val: print(val)
        break
    if line.startswith('pattern_ref:'):
        ref = line.split(':', 1)[1].strip()
        if (ref.startswith('\"') and ref.endswith('\"')) or (ref.startswith(chr(39)) and ref.endswith(chr(39))):
            ref = ref[1:-1]
        ref_path = os.path.join(pr, ref)
        if os.path.exists(ref_path):
            print(open(ref_path).read().strip())
        break
" 2>/dev/null || echo "")

    CHECK_TYPE=$(python3 -c "
import sys
for line in open('$rule_file'):
    line = line.strip()
    if line.startswith('type:') and 'check' not in line:
        val = line.split(':', 1)[1].strip().strip('\"')
        if val in ('grep', 'grep_inverse', 'compound'):
            print(val)
            break
" 2>/dev/null || echo "grep")

    MESSAGE=$(python3 -c "
import sys
capture = False
lines = []
for line in open('$rule_file'):
    if line.strip().startswith('message:'):
        rest = line.strip()[8:].strip()
        if rest == '|':
            capture = True
            continue
        elif rest:
            print(rest.strip('\"'))
            break
    elif capture:
        if line.startswith('  ') or line.startswith('\t'):
            lines.append(line.rstrip())
        else:
            break
if lines:
    print('\n'.join(lines))
" 2>/dev/null || echo "$RULE_ID violation")

    # ── 文件 glob 匹配检查 ──
    if [[ -n "$FILE_GLOB" ]]; then
        MATCH=false
        IFS='|' read -ra GLOBS <<< "$FILE_GLOB"
        for glob in "${GLOBS[@]}"; do
            # 简单通配符匹配
            if [[ "$FILE_PATH" == *${glob#\*}* ]] || [[ "$FILE_PATH" == $glob ]]; then
                MATCH=true
                break
            fi
        done
        if [[ "$MATCH" == "false" ]]; then
            continue
        fi
    fi

    # ── 跳过无 pattern 的规则 (compound 规则例外 — 从 steps 提取) ──
    if [[ -z "$PATTERN" ]] && [[ "$CHECK_TYPE" != "compound" ]]; then
        continue
    fi

    # ── 执行检查 ──
    VIOLATED=false

    if [[ "$CHECK_TYPE" == "grep" ]]; then
        if echo "$CONTENT" | grep -qP "$PATTERN" 2>/dev/null; then
            VIOLATED=true
        fi
    elif [[ "$CHECK_TYPE" == "grep_inverse" ]]; then
        if ! echo "$CONTENT" | grep -qP "$PATTERN" 2>/dev/null; then
            VIOLATED=true
        fi
    elif [[ "$CHECK_TYPE" == "compound" ]]; then
        # compound 规则: 提取 steps 中的 grep + grep_inverse
        # 所有 grep 条件匹配 AND 所有 grep_inverse 条件不匹配 → 违规
        COMPOUND_RESULT=$(RULE_FILE="$rule_file" python3 -c "
import os
lines = open(os.environ['RULE_FILE']).readlines()
greps = []
inv_greps = []
for line in lines:
    s = line.strip()
    if '- grep:' in s and 'grep_inverse' not in s and 'grep_size' not in s:
        val = s.split(':', 1)[1].strip()
        if (val.startswith('\"') and val.endswith('\"')) or (val.startswith(chr(39)) and val.endswith(chr(39))):
            val = val[1:-1]
        val = val.replace(chr(92)+chr(92), chr(92))  # unescape
        if val: greps.append(val)
    elif '- grep_inverse:' in s:
        val = s.split(':', 1)[1].strip()
        if (val.startswith('\"') and val.endswith('\"')) or (val.startswith(chr(39)) and val.endswith(chr(39))):
            val = val[1:-1]
        val = val.replace(chr(92)+chr(92), chr(92))  # unescape
        if val: inv_greps.append(val)
# Output: GREPS<TAB>INV_GREPS
print(chr(9).join([';'.join(greps), ';'.join(inv_greps)]))
" 2>/dev/null || echo "|||")

        IFS=$'\t' read -r GREP_PATTERNS INV_PATTERNS <<< "$COMPOUND_RESULT"

        ALL_MATCH=true
        # Check all positive greps must match
        if [[ -n "$GREP_PATTERNS" ]]; then
            IFS=';' read -ra GP_ARR <<< "$GREP_PATTERNS"
            for gp in "${GP_ARR[@]}"; do
                [[ -z "$gp" ]] && continue
                if ! echo "$CONTENT" | grep -qP "$gp" 2>/dev/null; then
                    ALL_MATCH=false
                    break
                fi
            done
        else
            ALL_MATCH=false
        fi

        # Check all inverse greps must NOT match (if positive greps all matched)
        if [[ "$ALL_MATCH" == "true" ]] && [[ -n "$INV_PATTERNS" ]]; then
            IFS=';' read -ra IP_ARR <<< "$INV_PATTERNS"
            for ip in "${IP_ARR[@]}"; do
                [[ -z "$ip" ]] && continue
                if echo "$CONTENT" | grep -qP "$ip" 2>/dev/null; then
                    ALL_MATCH=false
                    break
                fi
            done
        fi

        if [[ "$ALL_MATCH" == "true" ]]; then
            VIOLATED=true
        fi
    fi

    # ── 违规处理 ──
    if [[ "$VIOLATED" == "true" ]]; then
        # 记录到日志
        echo "$(date -Iseconds) | $RULE_ID | $ENFORCEMENT | $FILE_PATH" >> "$LOG_FILE" 2>/dev/null || true

        # 更新 stats.times_triggered (best-effort, 不阻塞)
        python3 -c "
import re, sys
path = '$rule_file'
with open(path, 'r') as f:
    content = f.read()
m = re.search(r'times_triggered:\s*(\d+)', content)
if m:
    old = int(m.group(1))
    content = content.replace(f'times_triggered: {old}', f'times_triggered: {old+1}')
    content = re.sub(r'last_triggered:.*', 'last_triggered: \"$(date +%Y-%m-%d)\"', content)
    with open(path, 'w') as f:
        f.write(content)
" 2>/dev/null &

        if [[ "$ENFORCEMENT" == "block" ]]; then
            ERRORS+=("$MESSAGE")
        elif [[ "$ENFORCEMENT" == "warn" ]]; then
            WARNINGS+=("$MESSAGE")
        fi
        # enforcement == "log" → 只记日志, 不输出
    fi
done

# ── 输出警告 (不阻止) ──
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    echo "" >&2
    echo "┌──────────────────────────────────────────────────────────┐" >&2
    echo "│  META-HARNESS V3 — RULE ENGINE WARNING                  │" >&2
    echo "└──────────────────────────────────────────────────────────┘" >&2
    for warn in "${WARNINGS[@]}"; do
        echo "  ⚠️  $warn" >&2
    done
    echo "" >&2
fi

# ── 输出错误 (阻止) ──
if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo "" >&2
    echo "╔══════════════════════════════════════════════════════════╗" >&2
    echo "║  META-HARNESS V3 — RULE ENGINE BLOCKED                 ║" >&2
    echo "╚══════════════════════════════════════════════════════════╝" >&2
    for err in "${ERRORS[@]}"; do
        echo "  ⛔ $err" >&2
    done
    echo "" >&2
    echo "  规则来源: rules/active/*.yaml | 教训来源: incidents/" >&2
    echo "" >&2
    exit 2
fi

exit 0
