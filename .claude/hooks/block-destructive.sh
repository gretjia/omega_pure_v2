#!/usr/bin/env bash
# block-destructive.sh — PreToolUse hook
# Reads tool input JSON from stdin, blocks dangerous Bash commands.
# Exit 0 = allow, Exit 2 = block (with reason on stderr)

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || echo "")

if [ -z "$COMMAND" ]; then
    exit 0
fi

# Pattern 1: rm -rf with dangerous targets
if echo "$COMMAND" | grep -qE 'rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|--force\s+)*(\/|~|\.\.|\/home|\/root|\*|\.claude)'; then
    echo "BLOCKED: Destructive rm command detected: $COMMAND" >&2
    exit 2
fi

# Pattern 2: git push --force (to any branch)
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force|git\s+push\s+-f'; then
    echo "BLOCKED: Force push detected. Use regular git push instead: $COMMAND" >&2
    exit 2
fi

# Pattern 3: git reset --hard
if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
    echo "BLOCKED: git reset --hard can destroy uncommitted work: $COMMAND" >&2
    exit 2
fi

# Pattern 4: Modifying physical constants via sed/awk
if echo "$COMMAND" | grep -qE "(sed|awk).*(DELTA|C_TSE|c_constant|power_constant|0\.842|0\.5)"; then
    echo "BLOCKED: Attempt to modify physical constants (Layer 1 axioms are immutable): $COMMAND" >&2
    exit 2
fi

# Pattern 5: Dropping database / destroying data stores
if echo "$COMMAND" | grep -qiE 'drop\s+table|drop\s+database|truncate\s+table'; then
    echo "BLOCKED: Destructive database operation detected: $COMMAND" >&2
    exit 2
fi

exit 0
