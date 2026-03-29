#!/usr/bin/env bash
# post-upload-verify.sh — PostToolUse hook (Bash)
# Axiom Ω1: 只信实测，不信推断. Auto-verify uploads.
#
# Triggers on: Bash commands containing gsutil cp / gcloud storage cp / scp
# Action: Check for 0-byte files at destination. Report, don't just remind.
# Exit 0 = info only (PostToolUse cannot block), but output is shown to agent.

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || echo "")

# Only check upload commands
if ! echo "$COMMAND" | grep -qE 'gsutil\s+cp|gcloud\s+storage\s+cp|scp\s'; then
    exit 0
fi

# Extract GCS destination if present
GCS_DST=$(echo "$COMMAND" | grep -oE 'gs://[^ ]+' | tail -1 || echo "")

if [ -z "$GCS_DST" ]; then
    echo "[Ω1 post-upload] Upload detected but no GCS destination found."
    echo "[Ω1 post-upload] REMINDER: Verify file sizes > 0 at destination."
    exit 0
fi

# Try to check for 0-byte files (best-effort, 10s timeout)
echo "[Ω1 post-upload] Upload to $GCS_DST detected. Checking for 0-byte files..."

ZEROS=$(timeout 10 gcloud storage ls -l "$GCS_DST" 2>/dev/null | awk '$1 == 0 {count++} END {print count+0}') || ZEROS="check_failed"

if [[ "$ZEROS" == "check_failed" ]] || ! [[ "$ZEROS" =~ ^[0-9]+$ ]]; then
    echo "[Ω1 post-upload] WARNING: Could not auto-verify. Manually run:"
    echo "  gcloud storage ls -l $GCS_DST | awk '\$1 == 0'"
elif [[ "$ZEROS" -gt 0 ]]; then
    echo "[Ω1 post-upload] ALERT: Found $ZEROS zero-byte files at $GCS_DST"
    echo "[Ω1 post-upload] 'Repaired' ≠ 'Repaired correctly'. Verify each file."
else
    echo "[Ω1 post-upload] Verified: 0 zero-byte files at destination."
fi

exit 0
