#!/bin/bash
# Upload shards from linux1 to GCS via SSH pipe
# Usage: bash gcp/upload_shards.sh [PARALLEL_JOBS]
# Default: 8 parallel uploads

set -e

PARALLEL=${1:-8}
SRC_HOST="linux1-lx"
SRC_DIR="/omega_pool/wds_shards_v3_full"
DST_BUCKET="gs://omega-pure-data/wds_shards_v3_full"

echo "=== Shard Upload: linux1 → GCS ==="
echo "Parallel jobs: ${PARALLEL}"
echo "Source: ${SRC_HOST}:${SRC_DIR}"
echo "Destination: ${DST_BUCKET}"

# Get list of shards on linux1
SHARD_LIST=$(ssh ${SRC_HOST} "ls ${SRC_DIR}/omega_shard_*.tar" 2>/dev/null)
TOTAL=$(echo "${SHARD_LIST}" | wc -l)
echo "Total shards: ${TOTAL}"

# Get already uploaded shards
UPLOADED=$(gsutil ls "${DST_BUCKET}/omega_shard_*.tar" 2>/dev/null | xargs -I{} basename {} | sort)
UPLOADED_COUNT=$(echo "${UPLOADED}" | grep -c "omega_shard" 2>/dev/null || echo 0)
echo "Already uploaded: ${UPLOADED_COUNT}"

# Upload function
upload_one() {
    local shard_path="$1"
    local shard_name=$(basename "${shard_path}")
    local dst="${DST_BUCKET}/${shard_name}"

    # Skip if already uploaded
    if echo "${UPLOADED}" | grep -q "${shard_name}"; then
        return 0
    fi

    ssh ${SRC_HOST} "cat ${shard_path}" | gsutil -q cp - "${dst}" 2>/dev/null
    echo "  [OK] ${shard_name}"
}

export -f upload_one
export SRC_HOST DST_BUCKET UPLOADED

# Run parallel uploads
echo ""
echo "Starting parallel upload (${PARALLEL} jobs)..."
echo "${SHARD_LIST}" | xargs -P ${PARALLEL} -I{} bash -c 'upload_one "$@"' _ {}

echo ""
echo "Upload complete."
gsutil ls "${DST_BUCKET}/" | wc -l
echo "shards in GCS."
