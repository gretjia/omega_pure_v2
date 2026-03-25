#!/bin/bash
# =========================================================
# Omega-TIB Phase 4: A-Share Swing Tracker HPO (SPOT VMs)
# =========================================================
# Usage: bash gcp/submit_phase4_hpo.sh
#
# PHASE 3 BITTER LESSONS APPLIED:
#   1. PyTorch image: 2-2.py310 (NOT 2-4)
#   2. num_workers=0 (gcsfuse limitation)
#   3. Financial Relativity Transform + Z-score already in train.py
#   4. batch_size=128 (OOM safety for hidden=256 + cg=1 combos)
#   5. SIGTERM handler for Spot preemption → emergency checkpoint
#   6. OOM handler → reports FVU=999.0 + clean exit
#   7. MDL-aware early stopping (warmup+1 before judging)
#   8. MUST run smoke test first!
#
# SPOT VM SAVINGS:
#   Regular L4:     ~$0.65/GPU/hr → 100 trials × 2h = $130
#   Preemptible L4: ~$0.20/GPU/hr → 100 trials × 2h = $40 (+ retries ≈ $60)
#   Quota: 200 preemptible L4 GPUs (approved 2026-03-24)
#
# Prerequisites:
#   1. Smoke test passed: bash gcp/phase4_smoke_test.sh
#   2. Data at gs://omega-pure-data/wds_shards_v3_full/

set -e

PROJECT="gen-lang-client-0250995579"
REGION="us-central1"
BUCKET="gs://omega-pure-data"

echo "=== Omega-TIB Phase 4: A-Share Swing HPO (SPOT VMs) ==="
echo "Trials: 100 (20 parallel) on SPOT L4 GPUs"
echo "Search: cg[1,4,16,64] × window_t[8,16,32] × lambda_s[1e-6,1e-4]"
echo "        × warmup[3,4,5] × hidden[128,256] × lr[1e-4,1e-3]"
echo "Budget: ~\$60-130 (SPOT pricing, with early stopping)"
echo ""
read -p "Proceed? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# [1/2] Upload training scripts to GCS (versioned: v4)
echo "[1/2] Uploading scripts to ${BUCKET}/scripts/v4/ ..."
gsutil cp train.py "${BUCKET}/scripts/v4/train.py"
gsutil cp omega_epiplexity_plus_core.py "${BUCKET}/scripts/v4/omega_epiplexity_plus_core.py"
gsutil cp omega_webdataset_loader.py "${BUCKET}/scripts/v4/omega_webdataset_loader.py"

# [2/2] Submit HP Tuning Job (full YAML config — required for SPOT scheduling)
echo "[2/2] Submitting HP Tuning Job with SPOT VMs..."

gcloud ai hp-tuning-jobs create \
  --region="${REGION}" \
  --config="gcp/phase4_hpo_config.yaml"

echo ""
echo "=== HPO Job Submitted ==="
echo ""
echo "Monitor:"
echo "  gcloud ai hp-tuning-jobs list --region=${REGION} --limit=5"
echo "  gcloud ai hp-tuning-jobs describe <JOB_ID> --region=${REGION}"
echo ""
echo "Cancel:"
echo "  gcloud ai hp-tuning-jobs cancel <JOB_ID> --region=${REGION}"
