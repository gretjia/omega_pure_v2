#!/usr/bin/env bash
# pre-deploy-gate.sh — PreToolUse hook (Bash)
# Axiom Ω3: 测试环境=生产环境. No canary PASS → no full job submission.
#
# Triggers on: gcloud ai custom-jobs create
# Checks: gcp/manifest.jsonl last canary entry is PASS
# Exit 0 = allow, Exit 2 = block

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || echo "")

# Only gate full job submissions (not canary jobs themselves)
if ! echo "$COMMAND" | grep -q 'gcloud ai custom-jobs create'; then
    exit 0
fi

# Allow canary jobs through (they contain "canary" in display name)
if echo "$COMMAND" | grep -qi 'canary'; then
    exit 0
fi

# Allow if using safe_submit.sh (it does its own canary check)
if echo "$COMMAND" | grep -q 'safe_submit'; then
    exit 0
fi

# Check manifest for canary PASS
MANIFEST="/home/zephryj/projects/omega_pure_v2/gcp/manifest.jsonl"

if [ ! -f "$MANIFEST" ] || [ ! -s "$MANIFEST" ]; then
    echo "BLOCKED: No manifest found. Run safe_build_and_canary.sh first." >&2
    echo "  Axiom Ω3: No canary PASS → no production deploy." >&2
    exit 2
fi

# Check last canary entry
LAST_CANARY=$(grep '"type".*"canary"' "$MANIFEST" 2>/dev/null | tail -1)

if [ -z "$LAST_CANARY" ]; then
    echo "BLOCKED: No canary entry in manifest. Run safe_build_and_canary.sh first." >&2
    exit 2
fi

STATUS=$(echo "$LAST_CANARY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('canary_status',''))" 2>/dev/null || echo "")

if [ "$STATUS" != "PASS" ]; then
    echo "BLOCKED: Last canary status is '$STATUS', not PASS." >&2
    echo "  Fix the canary failure first, then re-run safe_build_and_canary.sh." >&2
    exit 2
fi

echo "[pre-deploy-gate] Canary PASS verified in manifest. Allowing job submission."
exit 0
