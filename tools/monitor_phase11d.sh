#!/bin/bash
# Phase 11d Training Monitor — 双轨复苏监控
# Usage: bash tools/monitor_phase11d.sh
set -uo pipefail

JOBS=("Config_A(ls=1e-4)|projects/269018079180/locations/us-central1/customJobs/1109662714260619264|gs://omega-pure-data/checkpoints/phase11d_A_v1/train.log"
      "Config_B(ls=1e-5)|projects/269018079180/locations/us-central1/customJobs/1053367718918488064|gs://omega-pure-data/checkpoints/phase11d_B_v1/train.log")

echo "=== Phase 11d Monitor @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

ALL_DONE=true

for ENTRY in "${JOBS[@]}"; do
    IFS='|' read -r LABEL JOB LOG <<< "$ENTRY"

    STATE=$(gcloud ai custom-jobs describe "$JOB" --region=us-central1 \
        --format="value(state)" 2>/dev/null || echo "UNKNOWN")
    echo ""
    echo "--- $LABEL: $STATE ---"

    if [[ "$STATE" == "JOB_STATE_RUNNING" || "$STATE" == "JOB_STATE_PENDING" ]]; then
        ALL_DONE=false
    fi

    if [[ "$STATE" == "JOB_STATE_RUNNING" || "$STATE" == "JOB_STATE_SUCCEEDED" ]]; then
        TMP="/tmp/phase11d_monitor_$(echo $LABEL | tr '()=' '_').log"
        gsutil -q cp "$LOG" "$TMP" 2>/dev/null || { echo "  (no train.log yet)"; continue; }

        # Latest epoch summary
        LAST_EPOCH=$(grep "DONE" "$TMP" | tail -1)
        if [[ -n "$LAST_EPOCH" ]]; then
            echo "  $LAST_EPOCH"
            # Extract pred_std
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
done

echo ""
if $ALL_DONE; then
    echo "=== BOTH JOBS FINISHED ==="
fi
