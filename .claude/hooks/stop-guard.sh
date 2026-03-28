#!/usr/bin/env bash
# stop-guard.sh — Stop hook (advisory only, always exits 0)
# Reminds about uncommitted changes and handover.

cd /home/zephryj/projects/omega_pure_v2 2>/dev/null || exit 0
cat > /dev/null

# Check uncommitted math-critical files
if command -v git &>/dev/null && git rev-parse --git-dir &>/dev/null; then
    DIRTY=""
    for f in omega_epiplexity_plus_core.py omega_axioms.py architect/current_spec.yaml train.py; do
        if [ -f "$f" ] && ! git diff --quiet -- "$f" 2>/dev/null; then
            DIRTY="$DIRTY $f"
        fi
    done
    if [ -n "$DIRTY" ]; then
        echo "⚠ Uncommitted:$DIRTY"
    fi
fi

echo "→ Consider /handover-update if this was a significant session."
exit 0
