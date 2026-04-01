#!/bin/bash
# safe_build_and_canary.sh — Ω3+Ω4+Ω5: Build + target-env canary
# Prevents: 13-Docker-rebuild disasters, local-smoke-passes-but-GPU-fails
#
# Usage: bash gcp/safe_build_and_canary.sh <phase> <version>
# Example: bash gcp/safe_build_and_canary.sh 7 14
#
# Prerequisites:
#   - tests/test_known_bugs.py exists and passes
#   - gcloud auth configured
#   - Vertex AI API enabled

set -euo pipefail

# ── Args ─────────────────────────────────────────────────────────────
PHASE="${1:?Usage: bash gcp/safe_build_and_canary.sh <phase> <version>}"
VERSION="${2:?Usage: bash gcp/safe_build_and_canary.sh <phase> <version>}"

# ── Constants ────────────────────────────────────────────────────────
PROJECT="gen-lang-client-0250995579"
REGION="us-central1"
REGISTRY="us-central1-docker.pkg.dev/${PROJECT}/omega-training"
IMAGE_TAG="${REGISTRY}/omega-tib:phase${PHASE}-v${VERSION}"
SHARD_BUCKET="gs://omega-pure-data/wds_shards_v3_full"
CANARY_SHARD="omega_shard_00001.tar"
CANARY_TIMEOUT=900  # 15 minutes
POLL_INTERVAL=30
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${SCRIPT_DIR}/manifest.jsonl"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "================================================================"
echo "  SAFE BUILD + CANARY — Phase ${PHASE} v${VERSION}"
echo "  Image: ${IMAGE_TAG}"
echo "  $(date)"
echo "================================================================"
echo ""

# ── Step 1: Local pre-checks ────────────────────────────────────────
echo "=== STEP 1/5: Local pre-checks (先量化后行动) ==="

echo "[1a] Syntax-checking all .py files in gcp/..."
COMPILE_FAILED=0
for py_file in "${SCRIPT_DIR}"/*.py; do
  if ! python3 -m py_compile "$py_file" 2>&1; then
    echo "FAIL: py_compile ${py_file}"
    COMPILE_FAILED=1
  fi
done
if [[ $COMPILE_FAILED -ne 0 ]]; then
  echo "ABORT: Python syntax errors found. Fix before building."
  exit 1
fi
echo "  All .py files compile OK"

echo "[1b] Running regression tests..."
if [[ -f "tests/test_known_bugs.py" ]]; then
  if ! python3 -m pytest tests/test_known_bugs.py -v 2>&1; then
    echo "ABORT: Regression tests failed. Fix before building."
    exit 1
  fi
  echo "  Regression tests PASSED"
else
  echo "  WARNING: tests/test_known_bugs.py not found — skipping"
fi

echo ""

# ── Step 2: Docker build + push ─────────────────────────────────────
echo "=== STEP 2/5: Docker build + push via Cloud Build ==="
echo "  Tag: ${IMAGE_TAG}"

BUILD_LOG=$(mktemp)
if ! gcloud builds submit \
  --project="${PROJECT}" \
  --tag="${IMAGE_TAG}" \
  "${SCRIPT_DIR}/" 2>&1 | tee "${BUILD_LOG}"; then
  echo "ABORT: Cloud Build failed. Check logs above."
  rm -f "${BUILD_LOG}"
  exit 1
fi

# Extract build ID from log
BUILD_ID=$(grep -oP 'build/\K[a-f0-9-]+' "${BUILD_LOG}" | head -1 || echo "unknown")
rm -f "${BUILD_LOG}"
echo "  Build ID: ${BUILD_ID}"
echo "  Image pushed: ${IMAGE_TAG}"
echo ""

# ── Step 3: 1-shard canary on Vertex AI ─────────────────────────────
echo "=== STEP 3/5: 1-shard canary on Vertex AI (测试环境=生产环境) ==="

CANARY_NAME="omega-canary-p${PHASE}v${VERSION}-$(date +%H%M%S)"
echo "  Job name: ${CANARY_NAME}"
echo "  Shard: ${CANARY_SHARD}"
echo "  Machine: g2-standard-8 + L4 GPU (same as production)"
echo ""

gcloud ai custom-jobs create \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --display-name="${CANARY_NAME}" \
  --config=- <<YAML
workerPoolSpecs:
  - machineSpec:
      machineType: g2-standard-8
      acceleratorType: NVIDIA_L4
      acceleratorCount: 1
    replicaCount: 1
    diskSpec:
      bootDiskType: pd-ssd
      bootDiskSizeGb: 100
    containerSpec:
      imageUri: ${IMAGE_TAG}
      command:
        - bash
        - -c
      args:
        - |
          set -e
          echo "=== CANARY: Staging 1 shard to local SSD ==="
          mkdir -p /local_shards
          t0=\$(date +%s)
          gcloud storage cp '${SHARD_BUCKET}/${CANARY_SHARD}' /local_shards/
          t1=\$(date +%s)
          echo "Staged 1 shard in \$((t1-t0))s"

          echo "=== CANARY: Running phase7_inference.py ==="
          python3 /app/phase7_inference.py \
            --checkpoint=/gcs/omega-pure-data/checkpoints/phase6_icloss/trial_29/best.pt \
            --shard_dir=/local_shards \
            --date_map=/gcs/omega-pure-data/phase7/shard_date_map.json \
            --output=/tmp/canary_output.parquet \
            --hidden_dim=64 --window_size_t=32 --batch_size=512 \
            --checkpoint_interval=0

          echo "=== CANARY: Verifying output ==="
          ROW_COUNT=\$(python3 -c "
          import pyarrow.parquet as pq
          t = pq.read_table('/tmp/canary_output.parquet')
          print(len(t))
          ")
          echo "Output rows: \${ROW_COUNT}"
          if [[ \${ROW_COUNT} -gt 0 ]]; then
            echo "CANARY_PASS"
          else
            echo "CANARY_FAIL: 0 output rows"
            exit 1
          fi
YAML

echo ""

# Get the canary job ID
JOB_ID=$(gcloud ai custom-jobs list \
  --project="${PROJECT}" \
  --region="${REGION}" \
  --filter="displayName=${CANARY_NAME}" \
  --format="value(name)" \
  --sort-by="~createTime" \
  --limit=1)

echo "  Canary job ID: ${JOB_ID}"
echo "  Polling every ${POLL_INTERVAL}s (timeout ${CANARY_TIMEOUT}s)..."
echo ""

ELAPSED=0
while true; do
  STATE=$(gcloud ai custom-jobs describe "${JOB_ID}" \
    --project="${PROJECT}" \
    --region="${REGION}" \
    --format="value(state)")

  case $STATE in
    JOB_STATE_SUCCEEDED)
      echo "  Canary state: ${STATE}"
      break
      ;;
    JOB_STATE_FAILED|JOB_STATE_CANCELLED)
      echo ""
      echo "================================================================"
      echo "  CANARY FAILED — state: ${STATE}"
      echo "================================================================"
      echo ""
      echo "Fetching logs..."
      gcloud ai custom-jobs describe "${JOB_ID}" \
        --project="${PROJECT}" \
        --region="${REGION}" \
        --format="yaml(error)" 2>/dev/null || true
      echo ""
      echo "Full logs:"
      echo "  gcloud ai custom-jobs stream-logs ${JOB_ID} --project=${PROJECT} --region=${REGION}"
      exit 1
      ;;
    *)
      ELAPSED=$((ELAPSED + POLL_INTERVAL))
      if [[ $ELAPSED -ge $CANARY_TIMEOUT ]]; then
        echo "ABORT: Canary timed out after ${CANARY_TIMEOUT}s (state: ${STATE})"
        echo "Cancel with: gcloud ai custom-jobs cancel ${JOB_ID} --project=${PROJECT} --region=${REGION}"
        exit 1
      fi
      printf "  [%3ds] state: %s\r" "$ELAPSED" "$STATE"
      sleep $POLL_INTERVAL
      ;;
  esac
done

echo "  Canary PASSED"
echo ""

# ── Step 4: Write manifest entry ────────────────────────────────────
echo "=== STEP 4/5: Writing manifest entry ==="

MANIFEST_ENTRY=$(python3 -c "
import json, sys
entry = {
    'ts': '${TS}',
    'type': 'canary',
    'phase': ${PHASE},
    'version': ${VERSION},
    'docker_tag': '${IMAGE_TAG}',
    'canary_job_id': '${JOB_ID}',
    'canary_status': 'PASS',
    'build_id': '${BUILD_ID}'
}
print(json.dumps(entry, ensure_ascii=False))
")

echo "${MANIFEST_ENTRY}" >> "${MANIFEST}"
echo "  Appended to ${MANIFEST}"
echo ""

# ── Step 5: Final output ────────────────────────────────────────────
echo "================================================================"
echo "  CANARY PASSED — Phase ${PHASE} v${VERSION}"
echo "  Image: ${IMAGE_TAG}"
echo "  Canary job: ${JOB_ID}"
echo "================================================================"
echo ""
echo "Safe to submit full job with:"
echo "  bash gcp/safe_submit.sh"
echo ""
