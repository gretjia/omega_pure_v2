#!/bin/bash
# safe_upload.sh — Ω4: 可执行安全路径，替代 upload_shards.sh
# Encodes: VIA_NEGATIVA SSH pipe ban + HK direct path + per-file verification
#
# Usage: bash gcp/safe_upload.sh <shard_list_file>
#   shard_list_file: one shard basename per line (e.g., omega_shard_00322.tar)
#
# Prerequisites:
#   1. HK node has GCS credentials at /tmp/gcs_creds.json
#   2. HK can SSH to linux1 via localhost:2226 with id_ed25519_omega_workers
#
# Exit: 0 if all uploaded+verified, 1 if any failures (prints summary)

# ---------------------------------------------------------------------------
# Strict mode — but we handle per-shard errors explicitly so set -e won't
# abort the whole batch on a single failure.
# ---------------------------------------------------------------------------
set -euo pipefail

# ---------------------------------------------------------------------------
# Constants — network topology
# ---------------------------------------------------------------------------
HK_HOST="43.161.252.57"
HK_SSH_KEY="$HOME/.ssh/id_ed25519_omega_workers"
HK_SSH="ssh -o StrictHostKeyChecking=accept-new -i ${HK_SSH_KEY} root@${HK_HOST}"

# linux1 is reachable from HK via reverse tunnel on localhost:2226
LINUX1_VIA_HK="ssh -n -o StrictHostKeyChecking=accept-new -i /root/.ssh/id_ed25519_omega_workers -p 2226 zephryj@localhost"

SRC_DIR="/omega_pool/wds_shards_v3_full"
GCS_BUCKET="gs://omega-pure-data/wds_shards_v3_full"
GCS_BUCKET_NAME="omega-pure-data"
GCS_PREFIX="wds_shards_v3_full"
HK_STAGING="/tmp"
FAILURE_LOG="/tmp/safe_upload_failures.txt"

# GCS credentials path on HK node
GCS_CREDS="/tmp/gcs_creds.json"

# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------
if [[ $# -ne 1 ]]; then
    echo "Usage: bash gcp/safe_upload.sh <shard_list_file>"
    echo "  shard_list_file: one shard basename per line (e.g., omega_shard_00322.tar)"
    exit 1
fi

SHARD_LIST="$1"

if [[ ! -f "${SHARD_LIST}" ]]; then
    echo "ERROR: shard list file not found: ${SHARD_LIST}"
    exit 1
fi

# ---------------------------------------------------------------------------
# Read shard list using mapfile (NOT while read — VIA_NEGATIVA: ssh steals stdin)
# ---------------------------------------------------------------------------
mapfile -t shards < "${SHARD_LIST}"

# Filter out empty lines and comments
filtered_shards=()
for s in "${shards[@]}"; do
    s=$(echo "$s" | xargs)  # trim whitespace
    [[ -z "$s" || "$s" == \#* ]] && continue
    filtered_shards+=("$s")
done
shards=("${filtered_shards[@]}")

TOTAL=${#shards[@]}
if [[ ${TOTAL} -eq 0 ]]; then
    echo "ERROR: shard list is empty"
    exit 1
fi

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
success=0
failed=0
> "${FAILURE_LOG}"  # clear failure log

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo "=== Safe Upload: linux1 → HK → GCS ==="
echo "Total: ${TOTAL} shards"
echo "HK relay: ${HK_HOST}"
echo "Source: linux1:${SRC_DIR}"
echo "Destination: ${GCS_BUCKET}"
echo ""

# ---------------------------------------------------------------------------
# Per-shard upload loop (sequential — VIA_NEGATIVA: no parallel > 4)
# ---------------------------------------------------------------------------
for i in "${!shards[@]}"; do
    shard="${shards[$i]}"
    idx=$((i + 1))
    printf "[%d/%d] %s ... " "${idx}" "${TOTAL}" "${shard}"

    # Track per-shard success; set -e won't kill the loop because we
    # wrap each step in an if-chain.
    shard_ok=true

    # Step 1: SCP from linux1 to HK (via reverse tunnel)
    # HK pulls the file from linux1 through the reverse tunnel
    if ! ${HK_SSH} "${LINUX1_VIA_HK} 'cat ${SRC_DIR}/${shard}' > ${HK_STAGING}/${shard}" 2>/dev/null; then
        printf "SCP FAIL\n"
        echo "${shard}: SCP failed" >> "${FAILURE_LOG}"
        ((failed++)) || true
        continue
    fi
    printf "SCP OK ... "

    # Step 2: Upload from HK to GCS using python3 + GCS SDK
    # Using python3 instead of gsutil for reliability — avoids gsutil's
    # tendency to create 0-byte files on connection drops.
    upload_cmd="GOOGLE_APPLICATION_CREDENTIALS=${GCS_CREDS} python3 -c \"
from google.cloud import storage
client = storage.Client()
bucket = client.bucket('${GCS_BUCKET_NAME}')
blob = bucket.blob('${GCS_PREFIX}/${shard}')
blob.upload_from_filename('${HK_STAGING}/${shard}')
print('UPLOAD_OK')
\""
    upload_result=$(${HK_SSH} "${upload_cmd}" 2>/dev/null) || true
    if [[ "${upload_result}" != *"UPLOAD_OK"* ]]; then
        printf "GCS upload FAIL\n"
        echo "${shard}: GCS upload failed" >> "${FAILURE_LOG}"
        # Cleanup HK staging even on failure
        ${HK_SSH} "rm -f ${HK_STAGING}/${shard}" 2>/dev/null || true
        ((failed++)) || true
        continue
    fi
    printf "GCS upload OK ... "

    # Step 3: Verify GCS file size directly from omega-vm (via gsutil)
    # This is an independent verification — not trusting HK's word
    gcs_size=$(gsutil ls -l "${GCS_BUCKET}/${shard}" 2>/dev/null | head -1 | awk '{print $1}')
    if [[ -z "${gcs_size}" || "${gcs_size}" == "0" ]]; then
        printf "verify FAIL (0 bytes) <- LOGGED\n"
        echo "${shard}: verify failed (size=${gcs_size:-unknown})" >> "${FAILURE_LOG}"
        # Cleanup HK staging
        ${HK_SSH} "rm -f ${HK_STAGING}/${shard}" 2>/dev/null || true
        ((failed++)) || true
        continue
    fi

    # Convert bytes to human-readable MB
    size_mb=$(awk "BEGIN {printf \"%.1f\", ${gcs_size}/1048576}")
    printf "verify OK (%s MB)\n" "${size_mb}"

    # Step 4: Cleanup HK staging copy
    ${HK_SSH} "rm -f ${HK_STAGING}/${shard}" 2>/dev/null || true

    ((success++)) || true
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Summary ==="
echo "Success: ${success}/${TOTAL}"
if [[ ${failed} -gt 0 ]]; then
    echo "Failed: ${failed} (logged to ${FAILURE_LOG})"
    echo ""
    echo "Failed shards:"
    cat "${FAILURE_LOG}"
    exit 1
else
    echo "Failed: 0"
    rm -f "${FAILURE_LOG}"
    exit 0
fi
