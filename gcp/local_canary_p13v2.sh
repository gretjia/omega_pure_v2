#!/bin/bash
# local_canary_p13v2.sh — Run Phase 13 canary on linux1 (替代 GCP L4 资源不足)
# 隔离目录: /home/zepher/canary_p13v2/  不碰现有文件
set -euo pipefail

REMOTE="linux1-back"
CANARY_DIR="/home/zepher/canary_p13v2"
SHARD_DIR="/home/zepher/omega_pure_v2/smoke_test_output"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================"
echo "  LOCAL CANARY — Phase 13 v2 (linux1 AMD APU)"
echo "  $(date)"
echo "================================================================"

# Step 1: Create isolated canary dir + push scripts
echo "=== Step 1: Push scripts to ${REMOTE}:${CANARY_DIR} ==="
ssh "${REMOTE}" "mkdir -p ${CANARY_DIR}"

scp "${REPO_ROOT}/gcp/train.py" \
    "${REPO_ROOT}/gcp/omega_epiplexity_plus_core.py" \
    "${REPO_ROOT}/gcp/omega_webdataset_loader.py" \
    "${REMOTE}:${CANARY_DIR}/"

echo "  Scripts pushed OK"

# Step 2: Run canary (mirror GCP crucible config exactly)
echo "=== Step 2: Running Crucible canary (2000 steps, 64 samples, IC Loss) ==="
ssh "${REMOTE}" "cd ${CANARY_DIR} && \
  HSA_OVERRIDE_GFX_VERSION=11.0.0 \
  PYTHONUNBUFFERED=1 \
  python3 train.py \
    --shard_dir=${SHARD_DIR} \
    --output_dir=${CANARY_DIR}/output \
    --hidden_dim=64 \
    --window_size_t=32 \
    --window_size_s=10 \
    --lr=1e-3 \
    --lambda_s=0 \
    --batch_size=64 \
    --coarse_graining_factor=1 \
    --epochs=1 \
    --steps_per_epoch=2000 \
    --num_workers=2 \
    --no_amp \
    --overfit \
    --mask_prob=0.0 \
    --max_val_steps=1 \
    --val_split=0.01 2>&1"

echo ""
echo "================================================================"
echo "  LOCAL CANARY COMPLETE"
echo "================================================================"
