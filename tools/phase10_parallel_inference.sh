#!/bin/bash
# Phase 10 Parallel Inference — 8 workers, threads=1 each
# Profiled: threads=1 gives 131 samples/s (3.5x faster than threads=16)
# Expected: 8 workers × 131 = 1048 samples/s → ~2.7h for 10M samples
#
# Usage: bash phase10_parallel_inference.sh
# Run on linux1 from /omega_pool/phase7/

set -e

CHECKPOINT="/omega_pool/phase7/best_phase10.pt"
SHARD_DIR="/omega_pool/wds_shards_v3_full/"
DATE_MAP="/omega_pool/phase7/shard_date_map.json"
OUTPUT_BASE="/omega_pool/phase7/phase10_predictions"
SCRIPT="/omega_pool/phase7/phase7_inference.py"
NUM_WORKERS=8
TOTAL_SHARDS=1992
HD=64
WT=32
WS=4
BS=256
THREADS=1

SHARDS_PER_WORKER=$(( (TOTAL_SHARDS + NUM_WORKERS - 1) / NUM_WORKERS ))

echo "=== Phase 10 Parallel Inference ==="
echo "Workers: $NUM_WORKERS, Shards/worker: $SHARDS_PER_WORKER, Threads: $THREADS"
echo "Checkpoint: $CHECKPOINT"
echo ""

PIDS=()
for w in $(seq 0 $((NUM_WORKERS - 1))); do
    START=$((w * SHARDS_PER_WORKER))
    END=$(( (w + 1) * SHARDS_PER_WORKER ))
    if [ $END -gt $TOTAL_SHARDS ]; then
        END=$TOTAL_SHARDS
    fi
    if [ $START -ge $TOTAL_SHARDS ]; then
        continue
    fi

    OUTPUT="${OUTPUT_BASE}_w${w}.parquet"
    LOG="${OUTPUT_BASE}_w${w}.log"

    echo "Worker $w: shards [$START:$END] → $OUTPUT"
    PYTHONUNBUFFERED=1 python3 "$SCRIPT" \
        --checkpoint "$CHECKPOINT" \
        --shard_dir "$SHARD_DIR" \
        --date_map "$DATE_MAP" \
        --output "$OUTPUT" \
        --hidden_dim $HD --window_size_t $WT --window_size_s $WS \
        --batch_size $BS --num_threads $THREADS \
        --shard_start $START --shard_end $END \
        --worker_id $w \
        --checkpoint_interval 25 \
        > "$LOG" 2>&1 &
    PIDS+=($!)
done

echo ""
echo "Launched ${#PIDS[@]} workers: ${PIDS[*]}"
echo "Monitor: tail -f ${OUTPUT_BASE}_w*.log"
echo ""

# Wait for all workers
FAILED=0
for i in "${!PIDS[@]}"; do
    wait "${PIDS[$i]}" || { echo "Worker $i (PID ${PIDS[$i]}) FAILED"; FAILED=1; }
done

if [ $FAILED -eq 1 ]; then
    echo "ERROR: Some workers failed. Check logs."
    exit 1
fi

echo ""
echo "All workers done. Merging..."

# Merge all worker outputs into single parquet
python3 -c "
import pyarrow.parquet as pq
import pyarrow as pa
import glob

files = sorted(glob.glob('${OUTPUT_BASE}_w*.parquet'))
print(f'Merging {len(files)} worker outputs...')
tables = [pq.read_table(f) for f in files]
merged = pa.concat_tables(tables)
pq.write_table(merged, '${OUTPUT_BASE}.parquet')
print(f'Done: {merged.num_rows:,} samples → ${OUTPUT_BASE}.parquet')
"

echo "=== INFERENCE COMPLETE ==="
