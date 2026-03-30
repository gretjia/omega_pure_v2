#!/bin/bash
set -euo pipefail

HK_SSH=(ssh hk-wg)

LINUX1_CTRL_PORT="2226"
LINUX1_DATA_PORT="2296"
LINUX1_USER="zepher"
LINUX1_KEY="/home/ubuntu/.ssh/id_ed25519_omega_workers"
SRC_DIR="/omega_pool/wds_shards_v3_full"
GCS_BUCKET="gs://omega-pure-data/wds_shards_v3_full"
GCS_BUCKET_NAME="omega-pure-data"
GCS_PREFIX="wds_shards_v3_full"
HK_STAGING_DIR="/tmp/omega_safe_upload"
GCS_CREDS="/tmp/gcs_creds.json"
PROJECT_ID="gen-lang-client-0250995579"
FAILURE_LOG="/tmp/safe_upload_failures.txt"
RSYNC_SSH="ssh -o StrictHostKeyChecking=accept-new -i ${LINUX1_KEY} -p ${LINUX1_DATA_PORT}"

if [[ $# -ne 1 ]]; then
  echo "Usage: bash gcp/safe_upload.sh <shard_list_file>"
  exit 1
fi
SHARD_LIST="$1"
[[ -f "$SHARD_LIST" ]] || { echo "ERROR: shard list file not found: $SHARD_LIST"; exit 1; }

mapfile -t shards < "$SHARD_LIST"
filtered=()
for s in "${shards[@]}"; do
  s=$(echo "$s" | xargs)
  [[ -z "$s" || "$s" == \#* ]] && continue
  filtered+=("$s")
done
shards=("${filtered[@]}")
TOTAL=${#shards[@]}
[[ $TOTAL -gt 0 ]] || { echo "ERROR: shard list is empty"; exit 1; }

success=0
failed=0
> "$FAILURE_LOG"

"${HK_SSH[@]}" "mkdir -p '$HK_STAGING_DIR'"

echo "=== Safe Upload: linux1 -> HK(data tunnel) -> GCS ==="
echo "Total: $TOTAL shards"
echo "HK relay: hk-wg (10.88.0.2)"
echo "Control port: $LINUX1_CTRL_PORT"
echo "Data port: $LINUX1_DATA_PORT"
echo ""

for i in "${!shards[@]}"; do
  shard="${shards[$i]}"
  idx=$((i + 1))
  printf "[%d/%d] %s ... " "$idx" "$TOTAL" "$shard"

  src_size=$("${HK_SSH[@]}" "ssh -n -o StrictHostKeyChecking=accept-new -i '$LINUX1_KEY' -p '$LINUX1_CTRL_PORT' '${LINUX1_USER}@localhost' 'stat -c %s "$SRC_DIR/$shard"'" 2>/dev/null || true)
  if [[ ! "$src_size" =~ ^[0-9]+$ ]]; then
    echo "STAT FAIL"
    echo "$shard: stat failed" >> "$FAILURE_LOG"
    ((failed++)) || true
    continue
  fi

  transfer_ok=false
  for attempt in 1 2 3; do
    if "${HK_SSH[@]}" "rsync --partial --append-verify --inplace --timeout=60 -e '$RSYNC_SSH' '${LINUX1_USER}@localhost:$SRC_DIR/$shard' '$HK_STAGING_DIR/$shard'" >/dev/null 2>&1; then
      staged_size=$("${HK_SSH[@]}" "stat -c %s '$HK_STAGING_DIR/$shard'" 2>/dev/null || true)
      if [[ "$staged_size" == "$src_size" ]]; then
        transfer_ok=true
        break
      fi
    fi
    sleep 2
  done
  if [[ "$transfer_ok" != true ]]; then
    echo "PULL FAIL"
    echo "$shard: hk pull failed" >> "$FAILURE_LOG"
    ((failed++)) || true
    continue
  fi
  printf "PULL OK ... "

  if ! "${HK_SSH[@]}" "GOOGLE_APPLICATION_CREDENTIALS='$GCS_CREDS' python3 - <<'PY'
import os
from google.cloud import storage
client = storage.Client(project='$PROJECT_ID')
bucket = client.bucket('$GCS_BUCKET_NAME')
blob = bucket.blob('$GCS_PREFIX/$shard')
blob.upload_from_filename('$HK_STAGING_DIR/$shard')
print('UPLOAD_OK')
PY" >/dev/null 2>&1; then
    echo "GCS FAIL"
    echo "$shard: GCS upload failed" >> "$FAILURE_LOG"
    ((failed++)) || true
    continue
  fi
  printf "GCS OK ... "

  gcs_size=$(gcloud storage ls -l "$GCS_BUCKET/$shard" 2>/dev/null | awk 'NR==1 {print $1}')
  if [[ "$gcs_size" != "$src_size" ]]; then
    echo "VERIFY FAIL"
    echo "$shard: verify failed src=$src_size gcs=${gcs_size:-unknown}" >> "$FAILURE_LOG"
    ((failed++)) || true
    continue
  fi
  printf "VERIFY OK (%s MB)\n" "$(awk "BEGIN {printf \"%.1f\", $src_size/1048576}")"
  "${HK_SSH[@]}" "rm -f '$HK_STAGING_DIR/$shard'" >/dev/null 2>&1 || true
  ((success++)) || true
done

echo ""
echo "=== Summary ==="
echo "Success: $success/$TOTAL"
if [[ $failed -gt 0 ]]; then
  echo "Failed: $failed (logged to $FAILURE_LOG)"
  cat "$FAILURE_LOG"
  exit 1
fi
rm -f "$FAILURE_LOG"
echo "Failed: 0"
