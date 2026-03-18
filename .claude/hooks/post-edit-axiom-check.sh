#!/usr/bin/env bash
# post-edit-axiom-check.sh — PostToolUse hook
# After Edit/Write on math-critical files, auto-run omega_axioms.py
# Exit 0 = pass (message on stdout as info), Exit 1 = axiom violation

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || echo "")

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Only check math-critical files
CRITICAL_PATTERN="omega_epiplexity_plus_core\.py|omega_axioms\.py|architect/current_spec\.yaml|tools/.*etl.*\.py|tools/.*forge.*\.py"

if ! echo "$FILE_PATH" | grep -qE "$CRITICAL_PATTERN"; then
    exit 0
fi

# Run axiom check
cd /home/zephryj/projects/omega_pure_v2

echo "[PostToolUse] Math-critical file modified: $(basename "$FILE_PATH")"
echo "[PostToolUse] Running automatic axiom check..."

if python3 omega_axioms.py --verbose 2>&1; then
    echo "[PostToolUse] Axiom check PASSED"
    exit 0
else
    echo "[PostToolUse] AXIOM CHECK FAILED — Review violations above before continuing" >&2
    exit 1
fi
