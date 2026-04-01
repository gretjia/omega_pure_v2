#!/bin/bash
# lesson-enforcer.sh — Ω4: 将 OMEGA_LESSONS 教训变成可执行的拦截器
# PreToolUse hook: 在 Write/Edit 执行前检查文件内容是否违反已知教训
# 违规时 exit 2 + stderr 消息 → Claude 看到并被阻止
#
# 泛化原则: 每条可机械检查的 C-XXX 教训都应在此注册为规则

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

# 获取文件内容 (Write用content, Edit用new_string)
CONTENT=$(echo "$INPUT" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('tool_input',{})
print(d.get('content','') + d.get('new_string',''))
" 2>/dev/null || echo "")

# 如果不是我们关注的文件类型，直接放行
if [[ -z "$FILE_PATH" ]] || [[ -z "$CONTENT" ]]; then
    exit 0
fi

# 文档/记忆/日志文件免检 — 只检查代码和配置
case "$FILE_PATH" in
    *.md|*/memory/*|*/OMEGA_LESSONS*|*/handover/*|*/directives/*|*/insights/*|*.log)
        exit 0 ;;
esac

ERRORS=()

# ================================================================
# 规则注册区 — 每条规则对应一个 C-XXX 教训
# 格式: 文件模式 + 内容检查 + 错误消息
# ================================================================

# --- C-028/C-040: Vertex AI 全量 job 不可用大容量 pd-ssd 做数据 staging ---
# 规则: bootDiskSizeGb > 500 且无 Local SSD/NVMe 引用 → 在用 pd-ssd 装数据 → BLOCK
# 允许: 小 boot disk (≤500GB) + Local SSD 组合; canary job
if [[ "$FILE_PATH" == *gcp/*.yaml ]] || [[ "$FILE_PATH" == *gcp/*.yml ]]; then
    if echo "$CONTENT" | grep -qi "bootDiskType.*pd-ssd\|bootDiskType.*pd-balanced\|bootDiskType.*pd-standard"; then
        DISK_SIZE=$(echo "$CONTENT" | grep -oP 'bootDiskSizeGb:\s*\K[0-9]+' | head -1)
        HAS_LOCAL_SSD=$(echo "$CONTENT" | grep -ci "local.ssd\|nvme\|localssd\|/mnt/localssd\|/dev/nvme")
        IS_CANARY=$(echo "$CONTENT" | grep -ci "canary")
        if [[ "${DISK_SIZE:-0}" -gt 500 ]] && [[ "${HAS_LOCAL_SSD:-0}" -eq 0 ]] && [[ "${IS_CANARY:-0}" -eq 0 ]]; then
            ERRORS+=("C-028/C-040: bootDiskSizeGb=${DISK_SIZE} > 500 且无 Local SSD 引用 → 在用 pd-ssd 装数据。必须用 n1/n2 + Local SSD 或减小 boot disk。")
        fi
    fi
fi

# --- C-032: checkpoint_interval 不可为 0 (除零崩溃) ---
if echo "$CONTENT" | grep -qP "checkpoint_interval\s*[=:]\s*0\b"; then
    ERRORS+=("C-032: checkpoint_interval=0 导致除零崩溃。必须 > 0。")
fi

# --- C-037: window_size_s 必须与 checkpoint 匹配 ---
# (此规则需要人工判断, 仅提醒)

# --- C-039: device 不可硬编码为 cpu ---
if echo "$CONTENT" | grep -q 'torch.device("cpu")\|torch.device(.cpu.)'; then
    if ! echo "$CONTENT" | grep -q "cuda.is_available\|auto.detect"; then
        ERRORS+=("C-039: device 不可硬编码为 cpu, 必须 auto-detect torch.cuda.is_available()。")
    fi
fi

# --- 物理公理: delta 不可修改 ---
if echo "$CONTENT" | grep -qP "delta\s*=\s*(?!0\.5)[\d.]+" 2>/dev/null; then
    if [[ "$FILE_PATH" == *core*.py ]] || [[ "$FILE_PATH" == *axiom*.py ]]; then
        ERRORS+=("AXIOM VIOLATION: delta 必须 = 0.5 (Layer 1 物理常数, 不可修改)")
    fi
fi

# --- C-017: bash -c 必须以 \"$@\" 结尾 ---
if echo "$CONTENT" | grep -q 'bash -c'; then
    if ! echo "$CONTENT" | grep -q '"$@"'; then
        # 只对 gcp 脚本检查
        if [[ "$FILE_PATH" == *gcp/*.sh ]]; then
            ERRORS+=("C-017: bash -c 命令末尾必须加 \"\\\$@\" + _, 否则 HPO 超参被吞。")
        fi
    fi
fi

# ================================================================
# 输出判定
# ================================================================

if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo "" >&2
    echo "╔══════════════════════════════════════════════════════════╗" >&2
    echo "║  OMEGA LESSONS ENFORCER — WRITE BLOCKED                ║" >&2
    echo "╚══════════════════════════════════════════════════════════╝" >&2
    echo "" >&2
    for err in "${ERRORS[@]}"; do
        echo "  ⛔ $err" >&2
    done
    echo "" >&2
    echo "  修复后重试。规则来源: OMEGA_LESSONS.md" >&2
    echo "" >&2
    exit 2
fi

exit 0
