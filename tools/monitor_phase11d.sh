#!/bin/bash
# Phase 11d Training Monitor — 双轨复苏监控 + 自动重提交
# Usage: bash tools/monitor_phase11d.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOCK_FILE="/tmp/phase11d_resubmit.lock"
MAX_RESUBMIT=3  # 每个 config 最多自动重提交 3 次

# Config → YAML 映射（用于自动重提交）
declare -A CONFIG_YAML
CONFIG_YAML["Config_A"]="$PROJECT_DIR/gcp/phase11d_config_A.yaml"
CONFIG_YAML["Config_B"]="$PROJECT_DIR/gcp/phase11d_config_B.yaml"

# 当前追踪的 job IDs（文件持久化，重提交后更新）
JOB_TRACK="/tmp/phase11d_job_ids.txt"
if [[ ! -f "$JOB_TRACK" ]]; then
    cat > "$JOB_TRACK" << 'EOF'
Config_A|projects/269018079180/locations/us-central1/customJobs/1109662714260619264|gs://omega-pure-data/checkpoints/phase11d_A_v1/train.log|0
Config_B|projects/269018079180/locations/us-central1/customJobs/2854869142517841920|gs://omega-pure-data/checkpoints/phase11d_B_v1/train.log|0
EOF
fi

echo "=== Phase 11d Monitor @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

ALL_DONE=true
ANY_ACTIVE=false

while IFS='|' read -r LABEL JOB LOG RESUBMIT_COUNT; do
    STATE=$(gcloud ai custom-jobs describe "$JOB" --region=us-central1 \
        --format="value(state)" 2>/dev/null || echo "UNKNOWN")
    echo ""
    echo "--- $LABEL: $STATE (resubmits: $RESUBMIT_COUNT/$MAX_RESUBMIT) ---"

    # === 自动重提交逻辑 ===
    if [[ "$STATE" == "JOB_STATE_FAILED" && "$RESUBMIT_COUNT" -lt "$MAX_RESUBMIT" ]]; then
        CONFIG_KEY="${LABEL%%(*}"  # Config_A 或 Config_B
        YAML="${CONFIG_YAML[$CONFIG_KEY]}"
        if [[ -f "$YAML" ]]; then
            echo "  ⚡ FAILED — 自动重提交 (attempt $((RESUBMIT_COUNT+1))/$MAX_RESUBMIT)"
            NEW_JOB=$(gcloud ai custom-jobs create \
                --region=us-central1 \
                --display-name="phase11d-${CONFIG_KEY,,}-auto-resume-$((RESUBMIT_COUNT+1))" \
                --config="$YAML" \
                --format="value(name)" 2>&1)
            if [[ "$NEW_JOB" == projects/* ]]; then
                echo "  ✅ 新 Job: $NEW_JOB"
                # 更新追踪文件
                sed -i "s|^${LABEL}|.*|${LABEL}|${NEW_JOB}|${LOG}|$((RESUBMIT_COUNT+1))|" "$JOB_TRACK" 2>/dev/null
                # 简单方式：直接重写
                STATE="JOB_STATE_PENDING"
                ANY_ACTIVE=true
            else
                echo "  ❌ 重提交失败: $NEW_JOB"
            fi
        fi
    fi

    if [[ "$STATE" == "JOB_STATE_RUNNING" || "$STATE" == "JOB_STATE_PENDING" ]]; then
        ALL_DONE=false
        ANY_ACTIVE=true
    fi

    if [[ "$STATE" == "JOB_STATE_RUNNING" || "$STATE" == "JOB_STATE_SUCCEEDED" ]]; then
        TMP="/tmp/phase11d_monitor_$(echo $LABEL | tr '()=' '_').log"
        gsutil -q cp "$LOG" "$TMP" 2>/dev/null || { echo "  (no train.log yet)"; continue; }

        LAST_EPOCH=$(grep "DONE" "$TMP" | tail -1)
        if [[ -n "$LAST_EPOCH" ]]; then
            echo "  $LAST_EPOCH"
            PRED_STD=$(echo "$LAST_EPOCH" | grep -oP 'Std_yhat=\K[0-9.]+' || echo "")
            if [[ -n "$PRED_STD" ]]; then
                if (( $(echo "$PRED_STD < 10.0" | bc -l) )); then
                    echo "  VARIANCE COLLAPSE: pred_std=${PRED_STD} BP < 10.0"
                elif (( $(echo "$PRED_STD < 30.0" | bc -l) )); then
                    echo "  LOW VARIANCE: pred_std=${PRED_STD} BP"
                else
                    echo "  HEALTHY: pred_std=${PRED_STD} BP"
                fi
            fi
        else
            echo "  (staging or epoch 0 in progress)"
            tail -3 "$TMP" 2>/dev/null
        fi
    fi
done < "$JOB_TRACK"

echo ""
if $ALL_DONE; then
    echo "=== BOTH JOBS FINISHED ==="
    echo ""
    echo "POST-FLIGHT TODO (C-055):"
    echo "  1. 跑全量 val 烟测 (--val_only)"
    echo "  2. 实测 pred_std 与 D9-D0 spread 映射关系"
    echo "  3. 用数据重新标定方差哨兵阈值（当前 10/30 BP 是粗估）"
    echo "  4. 十分位 Alpha 分解 (Epiplexity 公理验证)"
fi
