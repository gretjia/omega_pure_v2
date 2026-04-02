#!/bin/bash
# Phase 11d Training Monitor — 双轨复苏监控 + 自动重提交
# Usage: bash tools/monitor_phase11d.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MAX_RESUBMIT=3

# Config → YAML 映射
declare -A CONFIG_YAML
CONFIG_YAML["Config_A"]="$PROJECT_DIR/gcp/phase11d_config_A.yaml"
CONFIG_YAML["Config_B"]="$PROJECT_DIR/gcp/phase11d_config_B.yaml"

# Job tracking 文件（持久化 job ID + resubmit count）
JOB_TRACK="/tmp/phase11d_job_ids.txt"
JOB_TRACK_NEW="/tmp/phase11d_job_ids.txt.new"

if [[ ! -f "$JOB_TRACK" ]]; then
    cat > "$JOB_TRACK" << 'EOF'
Config_A(ls=1e-4)|projects/269018079180/locations/us-central1/customJobs/4552691017664430080|gs://omega-pure-data/checkpoints/phase11d_A_v1/train.log|1
Config_B(ls=1e-5)|projects/269018079180/locations/us-central1/customJobs/3599968590243037184|gs://omega-pure-data/checkpoints/phase11d_B_v1/train.log|1
EOF
fi

echo "=== Phase 11d Monitor @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

ALL_DONE=true
# 写入新的 tracking 文件（原子替换）
> "$JOB_TRACK_NEW"

while IFS='|' read -r LABEL JOB LOG RESUBMIT_COUNT; do
    STATE=$(gcloud ai custom-jobs describe "$JOB" --region=us-central1 \
        --format="value(state)" 2>/dev/null || echo "UNKNOWN")
    echo ""
    echo "--- $LABEL: $STATE (resubmits: $RESUBMIT_COUNT/$MAX_RESUBMIT) ---"

    CURRENT_JOB="$JOB"
    CURRENT_COUNT="$RESUBMIT_COUNT"

    # === 自动重提交逻辑 ===
    if [[ "$STATE" == "JOB_STATE_FAILED" && "$RESUBMIT_COUNT" -lt "$MAX_RESUBMIT" ]]; then
        CONFIG_KEY="${LABEL%%(*}"  # Config_A 或 Config_B
        YAML="${CONFIG_YAML[$CONFIG_KEY]}"
        if [[ -f "$YAML" ]]; then
            NEW_COUNT=$((RESUBMIT_COUNT+1))
            echo "  ⚡ FAILED — 自动重提交 (attempt $NEW_COUNT/$MAX_RESUBMIT)"
            # 提取新 job 的 full resource name
            CREATE_OUTPUT=$(gcloud ai custom-jobs create \
                --region=us-central1 \
                --display-name="phase11d-${CONFIG_KEY,,}-auto-resume-${NEW_COUNT}" \
                --config="$YAML" 2>&1)
            # 从输出中提取 job resource name
            NEW_JOB=$(echo "$CREATE_OUTPUT" | grep -oP 'projects/[^\]]+/customJobs/\d+' | head -1)
            if [[ -n "$NEW_JOB" ]]; then
                echo "  ✅ 新 Job: $NEW_JOB"
                CURRENT_JOB="$NEW_JOB"
                CURRENT_COUNT="$NEW_COUNT"
                STATE="JOB_STATE_PENDING"
            else
                echo "  ❌ 重提交失败: $CREATE_OUTPUT"
            fi
        fi
    fi

    # 更新 tracking（无论是否重提交，都写入当前状态）
    echo "${LABEL}|${CURRENT_JOB}|${LOG}|${CURRENT_COUNT}" >> "$JOB_TRACK_NEW"

    if [[ "$STATE" == "JOB_STATE_RUNNING" || "$STATE" == "JOB_STATE_PENDING" ]]; then
        ALL_DONE=false
    fi

    if [[ "$STATE" == "JOB_STATE_RUNNING" || "$STATE" == "JOB_STATE_SUCCEEDED" ]]; then
        TMP="/tmp/phase11d_monitor_$(echo $LABEL | tr '()=' '_').log"
        gsutil -q cp "$LOG" "$TMP" 2>/dev/null || { echo "  (no train.log yet)"; continue; }

        LAST_EPOCH=$(grep "DONE" "$TMP" | tail -1)
        if [[ -n "$LAST_EPOCH" ]]; then
            echo "  $LAST_EPOCH"
            PRED_STD=$(echo "$LAST_EPOCH" | grep -oP 'Std_yhat=\K[0-9.]+' || echo "")
            if [[ -n "$PRED_STD" ]]; then
                # 用 awk 代替 bc（omega-vm 无 bc）
                VERDICT=$(echo "$PRED_STD" | awk '{if ($1 < 10.0) print "COLLAPSE"; else if ($1 < 30.0) print "LOW"; else print "HEALTHY"}')
                case "$VERDICT" in
                    COLLAPSE) echo "  VARIANCE COLLAPSE: pred_std=${PRED_STD} BP < 10.0" ;;
                    LOW)      echo "  LOW VARIANCE: pred_std=${PRED_STD} BP" ;;
                    HEALTHY)  echo "  HEALTHY: pred_std=${PRED_STD} BP" ;;
                esac
            fi
        else
            echo "  (staging or epoch 0 in progress)"
            tail -3 "$TMP" 2>/dev/null
        fi
    fi
done < "$JOB_TRACK"

# 原子替换 tracking 文件
mv "$JOB_TRACK_NEW" "$JOB_TRACK"

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
