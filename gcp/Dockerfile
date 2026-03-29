# Omega-TIB Phase 4 Training Image
# Pre-installs all dependencies to eliminate ~4 min init overhead on Spot VM restarts
#
# Base: Vertex AI PyTorch 2.2 GPU (CUDA + cuDNN + PyTorch pre-installed)
# Added: webdataset, cloudml-hypertune, training scripts
#
# Build: gcloud builds submit --tag us-central1-docker.pkg.dev/gen-lang-client-0250995579/omega-training/omega-tib:v4 gcp/
FROM us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2.py310:latest

# Pre-install dependencies (eliminates ~3 min pip install on every Spot restart)
RUN pip install --no-cache-dir webdataset cloudml-hypertune

# Copy training scripts (eliminates ~1 min gcloud storage cp on every restart)
COPY train.py backtest_5a.py phase7_inference.py omega_epiplexity_plus_core.py omega_webdataset_loader.py /app/
WORKDIR /app
