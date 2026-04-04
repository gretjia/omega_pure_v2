# C-071 Root Cause: Docker Tag + Dependency Sync

## Causal Chain
1. Mandate A replaced MSE with IC Loss → train.py validate() now imports scipy.stats.spearmanr
2. gcp/Dockerfile only had `pip install webdataset cloudml-hypertune` — scipy missing
3. gcp/phase13_crucible_config.yaml still pointed to `phase13-v1` (Mandate B only, no IC Loss)
4. External audit (Codex + manual review) caught both issues before deployment

## WHY: Two independent sync failures
- **Dependency**: New import added to Python code, Dockerfile not updated → runtime ImportError
- **Image tag**: Code committed and gcp/ synced, but YAML config still referenced old tag → old code runs

## Fix
1. Added `scipy` to Dockerfile pip install
2. Updated imageUri from phase13-v1 → phase13-v2
