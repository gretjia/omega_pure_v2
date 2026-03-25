#!/bin/bash
# =========================================================
# Omega-TIB Phase 4: MANDATORY Smoke Test (SPOT VM)
# =========================================================
# VIA_NEGATIVA: "CPU smoke test ≠ GPU training" (v1-v9 all failed)
#
# Runs a SINGLE trial on the ACTUAL target environment with
# middle-ground hyperparameters. Also tests SPOT VM scheduling.
#
# Verifies:
#   1. No NaN/Inf in loss
#   2. Loss decreases over steps
#   3. hypertune metric reporting works (or gracefully skipped)
#   4. Checkpoint saves to GCS
#   5. coarse_graining_factor=4 works (non-trivial time pooling)
#   6. SPOT VM scheduling accepted by Vertex AI
#
# Usage: bash gcp/phase4_smoke_test.sh

set -e

PROJECT="gen-lang-client-0250995579"
REGION="us-central1"
BUCKET="gs://omega-pure-data"
JOB_NAME="omega-phase4-smoke-$(date +%Y%m%d-%H%M%S)"

echo "=== Phase 4 Smoke Test (SPOT VM, target environment) ==="
echo "Job: ${JOB_NAME}"
echo "Config: 2 epochs × 200 steps, hidden=256, cg=4, window_t=16"
echo "Expected: ~5 min, ~\$0.05 cost (SPOT pricing)"
echo ""

# Upload latest scripts
echo "[1/2] Uploading scripts..."
gsutil cp train.py "${BUCKET}/scripts/v4/train.py"
gsutil cp omega_epiplexity_plus_core.py "${BUCKET}/scripts/v4/omega_epiplexity_plus_core.py"
gsutil cp omega_webdataset_loader.py "${BUCKET}/scripts/v4/omega_webdataset_loader.py"

# Submit smoke test as custom job (with SPOT scheduling)
echo "[2/2] Submitting SPOT VM smoke test..."

gcloud ai custom-jobs create \
  --region="${REGION}" \
  --display-name="${JOB_NAME}" \
  --config=- <<'YAML'
workerPoolSpecs:
  - machineSpec:
      machineType: g2-standard-8
      acceleratorType: NVIDIA_L4
      acceleratorCount: 1
    replicaCount: 1
    containerSpec:
      imageUri: us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2.py310:latest
      command:
        - bash
        - -c
      args:
        - |
          pip install webdataset cloudml-hypertune &&
          gcloud storage cp gs://omega-pure-data/scripts/v4/*.py . &&
          python3 train.py \
            --shard_dir=/gcs/omega-pure-data/wds_shards_v3_full \
            --output_dir=/gcs/omega-pure-data/checkpoints/phase4_smoke \
            --epochs=2 \
            --steps_per_epoch=200 \
            --batch_size=128 \
            --lr=0.0005 \
            --lambda_s=0.00001 \
            --warmup_epochs=1 \
            --hidden_dim=256 \
            --window_size_t=16 \
            --window_size_s=10 \
            --coarse_graining_factor=4 \
            --mask_prob=0.0 \
            --grad_clip=1.0 \
            --macro_window=160 \
            --early_stop_fvu=0 \
            --early_stop_patience=3 \
            --num_workers=0
scheduling:
  strategy: SPOT
  restartJobOnWorkerRestart: true
YAML

echo ""
echo "=== Smoke Test Submitted: ${JOB_NAME} ==="
echo ""
echo "Monitor:"
echo "  gcloud ai custom-jobs list --region=${REGION} --filter='displayName:${JOB_NAME}'"
echo ""
echo "Verify after SUCCEEDED:"
echo "  [ ] No NaN in logs"
echo "  [ ] Loss decreased over 200 steps"
echo "  [ ] 2 epochs completed"
echo "  [ ] SPOT scheduling accepted (not rejected by quota)"
echo "  [ ] Checkpoint at gs://omega-pure-data/checkpoints/phase4_smoke/"
echo ""
echo "If ALL pass → bash gcp/submit_phase4_hpo.sh"
