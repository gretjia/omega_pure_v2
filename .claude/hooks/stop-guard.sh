#!/usr/bin/env bash
# stop-guard.sh — Stop hook (P0: auto-handover + uncommitted check)
# Advisory only, always exits 0. Never blocks session end.
#
# Two functions:
# 1. Original: warn about uncommitted math-critical files
# 2. NEW (P0): generate handover state reminder with key project state

cd /home/zephryj/projects/omega_pure_v2 2>/dev/null || exit 0

# Read stdin (required by hook protocol)
cat > /dev/null

# === Part 1: Uncommitted changes check (original) ===
CORE_FILES="omega_epiplexity_plus_core.py omega_axioms.py architect/current_spec.yaml train.py"
DIRTY_CORE=""

for f in $CORE_FILES; do
    if [ -f "$f" ] && ! git diff --quiet -- "$f" 2>/dev/null; then
        DIRTY_CORE="$DIRTY_CORE $f"
    fi
    if [ -f "$f" ] && ! git diff --cached --quiet -- "$f" 2>/dev/null; then
        DIRTY_CORE="$DIRTY_CORE $f (staged)"
    fi
done

for f in $(git diff --name-only 2>/dev/null | grep -E 'tools/.*(etl|forge)'); do
    DIRTY_CORE="$DIRTY_CORE $f"
done

# === Part 2: Handover state reminder (P0 upgrade) ===
echo ""
echo "=== SESSION END CHECKLIST ==="
echo ""

if [ -n "$DIRTY_CORE" ]; then
    echo "⚠ UNCOMMITTED math-critical files:"
    for f in $DIRTY_CORE; do
        echo "  - $f"
    done
    echo ""
fi

# Check if handover was updated this session
LATEST="handover/LATEST.md"
if [ -f "$LATEST" ]; then
    LAST_UPDATE=$(head -2 "$LATEST" | grep -oP '\d{4}-\d{2}-\d{2}' | head -1)
    TODAY=$(date +%Y-%m-%d)
    if [ "$LAST_UPDATE" != "$TODAY" ]; then
        echo "⚠ handover/LATEST.md last updated: $LAST_UPDATE (not today)"
        echo "  → Run /handover-update before ending session"
    else
        echo "✓ handover/LATEST.md updated today"
    fi
else
    echo "⚠ handover/LATEST.md not found!"
fi

# Quick state snapshot for the human
echo ""
echo "Quick state:"
echo "  Last 3 commits: $(git log --oneline -3 2>/dev/null | tr '\n' ' ')"
echo "  Uncommitted files: $(git diff --name-only 2>/dev/null | wc -l) modified, $(git ls-files --others --exclude-standard 2>/dev/null | wc -l) untracked"

# Check for running GCP jobs (lightweight)
if command -v gcloud &>/dev/null; then
    RUNNING_JOBS=$(gcloud ai custom-jobs list --region=us-central1 --filter="state=JOB_STATE_RUNNING" --format="value(name)" 2>/dev/null | wc -l)
    RUNNING_HPO=$(gcloud ai hp-tuning-jobs list --region=us-central1 --filter="state=JOB_STATE_RUNNING" --format="value(name)" 2>/dev/null | wc -l)
    if [ "$RUNNING_JOBS" -gt 0 ] || [ "$RUNNING_HPO" -gt 0 ]; then
        echo "  ☁ Running GCP jobs: ${RUNNING_JOBS} custom + ${RUNNING_HPO} HPO"
        echo "  → Record job IDs in handover before ending!"
    fi
fi

echo ""
echo "VIA NEGATIVA reminder: 接收指令 ≠ 授权执行 | 断点续传是强制要求"
echo "==========================="
echo ""

exit 0
