#!/usr/bin/env bash
# stop-guard.sh — Stop hook
# Reminds about uncommitted changes to math-critical files.
# Always exits 0 (advisory only, never blocks).

cd /home/zephryj/projects/omega_pure_v2 2>/dev/null || exit 0

# Read stdin (required by hook protocol) but don't need it
cat > /dev/null

CORE_FILES="omega_epiplexity_plus_core.py omega_axioms.py architect/current_spec.yaml"
DIRTY_CORE=""

for f in $CORE_FILES; do
    if [ -f "$f" ] && ! git diff --quiet -- "$f" 2>/dev/null; then
        DIRTY_CORE="$DIRTY_CORE $f"
    fi
    if [ -f "$f" ] && ! git diff --cached --quiet -- "$f" 2>/dev/null; then
        DIRTY_CORE="$DIRTY_CORE $f (staged)"
    fi
done

# Also check tools/ ETL files
for f in $(git diff --name-only 2>/dev/null | grep -E 'tools/.*(etl|forge)'); do
    DIRTY_CORE="$DIRTY_CORE $f"
done

if [ -n "$DIRTY_CORE" ]; then
    echo ""
    echo "WARNING: Uncommitted changes in math-critical files:"
    for f in $DIRTY_CORE; do
        echo "  - $f"
    done
    echo "Consider committing these changes before ending the session."
    echo ""
fi

exit 0
