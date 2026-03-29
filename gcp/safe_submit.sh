#!/bin/bash
# safe_submit.sh — Ω1+Ω2+Ω3: Submit full job with manifest tracking
# Prevents: deploying without canary, version confusion, disk-too-small
#
# Usage: bash gcp/safe_submit.sh <phase> <version>
# Example: bash gcp/safe_submit.sh 7 14
#
# Prerequisites:
#   - gcp/manifest.jsonl has a PASS canary for this docker tag
#   - gcp/phase7_job_config.yaml exists

set -euo pipefail

# ── Constants ──────────────────────────────────────────────────────────
PROJECT="gen-lang-client-0250995579"
REGION="us-central1"
DATA_BUCKET="gs://omega-pure-data/wds_shards_v3_full/"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOB_CONFIG="${SCRIPT_DIR}/phase7_job_config.yaml"
MANIFEST="${SCRIPT_DIR}/manifest.jsonl"
DISK_SAFETY_MULTIPLIER=2

# ── Args ───────────────────────────────────────────────────────────────
if [[ $# -ne 2 ]]; then
    echo "Usage: bash gcp/safe_submit.sh <phase> <version>"
    echo "Example: bash gcp/safe_submit.sh 7 14"
    exit 1
fi

PHASE="$1"
VERSION="$2"
DISPLAY_NAME="phase${PHASE}-inference-v${VERSION}"

echo "=== safe_submit.sh: ${DISPLAY_NAME} ==="
echo ""

# ── Helper: JSON parsing (jq with python3 fallback) ───────────────────
json_get() {
    # Usage: json_get '<json_string>' '.field'
    local json="$1"
    local field="$2"
    if command -v jq &>/dev/null; then
        echo "$json" | jq -r "$field"
    else
        echo "$json" | python3 -c "import sys,json; print(json.loads(sys.stdin.read())${field})"
    fi
}

json_get_py_bracket() {
    # python3 fallback uses bracket notation: ['field']
    # jq uses dot notation: .field
    # This wrapper handles both
    local json="$1"
    local jq_field="$2"
    local py_field="$3"
    if command -v jq &>/dev/null; then
        echo "$json" | jq -r "$jq_field"
    else
        echo "$json" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d${py_field})"
    fi
}

# ── Step 1: Check canary passed (Ω3) ──────────────────────────────────
echo "[Step 1] Checking canary status..."

if [[ ! -f "$MANIFEST" ]] || [[ ! -s "$MANIFEST" ]]; then
    echo "ABORT: gcp/manifest.jsonl is empty or missing."
    echo "  Run safe_build_and_canary.sh first."
    exit 1
fi

LAST_LINE="$(tail -n 1 "$MANIFEST")"
LAST_TYPE="$(json_get_py_bracket "$LAST_LINE" '.type' "['type']")"
LAST_STATUS="$(json_get_py_bracket "$LAST_LINE" '.canary_status // empty' ".get('canary_status', '')")"
LAST_DOCKER_TAG="$(json_get_py_bracket "$LAST_LINE" '.docker_tag' "['docker_tag']")"

if [[ "$LAST_TYPE" != "canary" ]] || [[ "$LAST_STATUS" != "PASS" ]]; then
    echo "ABORT: Last manifest entry is not a passing canary."
    echo "  type=${LAST_TYPE}, canary_status=${LAST_STATUS}"
    echo "  Run safe_build_and_canary.sh first."
    exit 1
fi

DOCKER_TAG="$LAST_DOCKER_TAG"
echo "  Canary PASS confirmed for: ${DOCKER_TAG}"
echo ""

# ── Step 2: Calculate disk requirement (Ω2: 先量化后行动) ─────────────
echo "[Step 2] Checking disk requirements..."

DATA_SIZE_RAW="$(gsutil du -s "${DATA_BUCKET}" | awk '{print $1}')"
DATA_SIZE_GB=$(python3 -c "print(int(${DATA_SIZE_RAW} / (1024**3)) + 1)")
REQUIRED_DISK_GB=$((DATA_SIZE_GB * DISK_SAFETY_MULTIPLIER))

# Parse bootDiskSizeGb from config
CONFIG_DISK_GB="$(python3 -c "
import yaml, sys
with open('${JOB_CONFIG}') as f:
    cfg = yaml.safe_load(f)
print(cfg['workerPoolSpecs'][0]['diskSpec']['bootDiskSizeGb'])
")"

echo "  Data size: ~${DATA_SIZE_GB}GB"
echo "  Required disk (${DISK_SAFETY_MULTIPLIER}x safety): ${REQUIRED_DISK_GB}GB"
echo "  Config bootDiskSizeGb: ${CONFIG_DISK_GB}GB"

if [[ "$CONFIG_DISK_GB" -lt "$REQUIRED_DISK_GB" ]]; then
    echo ""
    echo "  WARNING: Config disk (${CONFIG_DISK_GB}GB) < required (${REQUIRED_DISK_GB}GB)!"
    echo "  The job may fail due to insufficient disk space."
    echo "  Consider increasing bootDiskSizeGb in ${JOB_CONFIG}"
    echo ""
    read -r -p "  Continue anyway? [y/N] " confirm
    if [[ "${confirm,,}" != "y" ]]; then
        echo "Aborted by user."
        exit 1
    fi
else
    echo "  Disk OK."
fi
echo ""

# ── Step 3: Submit job ─────────────────────────────────────────────────
echo "[Step 3] Updating imageUri and submitting job..."

# Update imageUri in config to match canary docker tag
python3 -c "
import yaml
with open('${JOB_CONFIG}') as f:
    cfg = yaml.safe_load(f)
cfg['workerPoolSpecs'][0]['containerSpec']['imageUri'] = '${DOCKER_TAG}'
with open('${JOB_CONFIG}', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
print('  imageUri updated to: ${DOCKER_TAG}')
"

# Submit
echo "  Submitting to Vertex AI..."
JOB_OUTPUT="$(gcloud ai custom-jobs create \
    --project="${PROJECT}" \
    --region="${REGION}" \
    --display-name="${DISPLAY_NAME}" \
    --config="${JOB_CONFIG}" \
    2>&1)"

echo "$JOB_OUTPUT"

# Extract job ID (format: projects/.../locations/.../customJobs/NNNN)
JOB_ID="$(echo "$JOB_OUTPUT" | grep -oP 'customJobs/\K[0-9]+' | head -1 || true)"
if [[ -z "$JOB_ID" ]]; then
    # Fallback: try to get from 'name:' field
    JOB_ID="$(echo "$JOB_OUTPUT" | grep -oP 'name:\s*.*customJobs/\K[0-9]+' | head -1 || true)"
fi

if [[ -z "$JOB_ID" ]]; then
    echo "WARNING: Could not parse job ID from output. Check gcloud output above."
    JOB_ID="UNKNOWN"
fi

echo "  Job ID: ${JOB_ID}"
echo ""

# ── Step 4: Update manifest ───────────────────────────────────────────
echo "[Step 4] Updating manifest..."

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if command -v jq &>/dev/null; then
    jq -n \
        --arg ts "$TS" \
        --arg type "full_job" \
        --arg job_id "$JOB_ID" \
        --arg docker_tag "$DOCKER_TAG" \
        --argjson disk_gb "$CONFIG_DISK_GB" \
        --argjson data_gb "$DATA_SIZE_GB" \
        --arg display_name "$DISPLAY_NAME" \
        '{ts: $ts, type: $type, job_id: $job_id, docker_tag: $docker_tag, disk_gb: $disk_gb, data_gb: $data_gb, display_name: $display_name}' \
        >> "$MANIFEST"
else
    python3 -c "
import json, sys
entry = {
    'ts': '${TS}',
    'type': 'full_job',
    'job_id': '${JOB_ID}',
    'docker_tag': '${DOCKER_TAG}',
    'disk_gb': ${CONFIG_DISK_GB},
    'data_gb': ${DATA_SIZE_GB},
    'display_name': '${DISPLAY_NAME}'
}
print(json.dumps(entry))
" >> "$MANIFEST"
fi

echo "  Appended to manifest.jsonl"
echo ""

# ── Step 5: Output summary ────────────────────────────────────────────
echo "=========================================="
echo "  Job submitted successfully"
echo "=========================================="
echo "  Display name : ${DISPLAY_NAME}"
echo "  Job ID       : ${JOB_ID}"
echo "  Docker tag   : ${DOCKER_TAG}"
echo "  Data size    : ~${DATA_SIZE_GB}GB"
echo "  Disk alloc   : ${CONFIG_DISK_GB}GB"
echo "=========================================="
echo ""
echo "Monitor with:"
echo "  gcloud ai custom-jobs describe ${JOB_ID} --project=${PROJECT} --region=${REGION}"
echo "  gcloud ai custom-jobs stream-logs ${JOB_ID} --project=${PROJECT} --region=${REGION}"
