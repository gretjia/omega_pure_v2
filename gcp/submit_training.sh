#!/bin/bash
# Omega-TIB Phase 3: Vertex AI Training Job Submission
# Usage: bash gcp/submit_training.sh
#
# Prerequisites:
#   1. Training data uploaded to gs://omega-pure-data/wds_shards_v3_full/
#   2. Training scripts uploaded to gs://omega-pure-data/scripts/v3/
#   3. gcloud auth configured

set -e

PROJECT="gen-lang-client-0250995579"
REGION="us-central1"
BUCKET="gs://omega-pure-data"
JOB_NAME="omega-tib-phase3-$(date +%Y%m%d-%H%M%S)"

# Training config
EPOCHS=10
STEPS_PER_EPOCH=10000
BATCH_SIZE=256
LR="1e-4"
HIDDEN_DIM=64

echo "=== Omega-TIB Phase 3 Training ==="
echo "Job: ${JOB_NAME}"
echo "GPU: 1x NVIDIA L4 (g2-standard-4)"
echo "Data: ${BUCKET}/wds_shards_v3_full/ (164GB, 1992 shards)"
echo "Config: epochs=${EPOCHS}, steps=${STEPS_PER_EPOCH}, batch=${BATCH_SIZE}"
echo ""

# Upload training scripts to GCS
echo "[1/2] Uploading training scripts to GCS..."
gsutil cp train.py "${BUCKET}/scripts/v3/train.py"
gsutil cp omega_epiplexity_plus_core.py "${BUCKET}/scripts/v3/omega_epiplexity_plus_core.py"
gsutil cp omega_webdataset_loader.py "${BUCKET}/scripts/v3/omega_webdataset_loader.py"

echo "[2/2] Submitting Vertex AI CustomJob..."

gcloud ai custom-jobs create \
  --region="${REGION}" \
  --display-name="${JOB_NAME}" \
  --worker-pool-spec="\
machine-type=g2-standard-4,\
accelerator-type=NVIDIA_L4,\
accelerator-count=1,\
replica-count=1,\
container-image-uri=us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4:latest" \
  --command='bash' \
  --args='-c,pip install webdataset && \
    gcloud storage cp gs://omega-pure-data/scripts/v3/*.py . && \
    python3 train.py \
      --shard_dir=/gcs/omega-pure-data/wds_shards_v3_full \
      --output_dir=/gcs/omega-pure-data/checkpoints/'"${JOB_NAME}"' \
      --epochs='"${EPOCHS}"' \
      --steps_per_epoch='"${STEPS_PER_EPOCH}"' \
      --batch_size='"${BATCH_SIZE}"' \
      --lr='"${LR}"' \
      --hidden_dim='"${HIDDEN_DIM}"' \
      --num_workers=4'

echo ""
echo "Job submitted: ${JOB_NAME}"
echo "Monitor: gcloud ai custom-jobs list --region=${REGION} --filter='displayName:${JOB_NAME}'"
echo "Logs: gcloud ai custom-jobs stream-logs <JOB_ID> --region=${REGION}"
