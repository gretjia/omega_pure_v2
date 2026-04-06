"""
ETL v5 Pipeline Runner — Sort + ETL concurrent on Windows/Linux.
Starts sort in background thread, waits for head start, then launches ETL.

Usage (via Scheduled Task on Windows):
  C:\Python314\python.exe -u D:\work\omega_pure_v2\run_etl_v5_pipeline.py
"""
import sys
import os
import time
import threading
import logging

if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()

    # ========== CONFIGURATION ==========
    if sys.platform == 'win32':
        RAW_DIR = r'D:\Omega_frames\latest_base_l1'
        SORTED_DIR = r'D:\Omega_frames\latest_base_l1_sorted'
        SHARD_DIR = r'D:\Omega_frames\wds_shards_v4'
        C_REGISTRY = r'D:\work\omega_pure_v2\a_share_c_registry.json'
        CODE_DIR = r'D:\work\omega_pure_v2'
        WORKERS = 16
    else:
        RAW_DIR = '/omega_pool/parquet_data/latest_base_l1'
        SORTED_DIR = '/omega_pool/parquet_data/latest_base_l1_sorted'
        SHARD_DIR = '/omega_pool/wds_shards_v4'
        C_REGISTRY = '/home/zepher/omega_pure_v2/a_share_c_registry.json'
        CODE_DIR = '/home/zepher/omega_pure_v2'
        WORKERS = 8

    HEAD_START_FILES = 50  # Wait for this many sorted files before starting ETL

    os.environ['PYTHONUNBUFFERED'] = '1'
    sys.path.insert(0, CODE_DIR)

    LOG_PATH = os.path.join(SHARD_DIR, 'pipeline_v5.log')
    os.makedirs(SHARD_DIR, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_PATH, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stderr),
        ]
    )

    # ========== DISCOVER ALL RAW FILES ==========
    raw_files = []
    for root, dirs, files in os.walk(RAW_DIR):
        for f in files:
            if f.endswith('.parquet'):
                raw_files.append(os.path.join(root, f))
    raw_files.sort(key=lambda p: os.path.basename(p)[:8])  # chronological

    # Build corresponding sorted file paths (same relative structure)
    sorted_files = []
    for fpath in raw_files:
        rel = os.path.relpath(fpath, RAW_DIR)
        sorted_files.append(os.path.join(SORTED_DIR, rel))

    logging.info(f'[PIPELINE] {len(raw_files)} raw files → {SORTED_DIR}')
    logging.info(f'[PIPELINE] Workers: {WORKERS}, Head start: {HEAD_START_FILES} files')

    # ========== WRITE FILE LIST FOR ETL ==========
    file_list_path = os.path.join(SHARD_DIR, '_sorted_file_list.txt')
    with open(file_list_path, 'w') as f:
        for p in sorted_files:
            f.write(p + '\n')

    # ========== START SORT IN BACKGROUND THREAD ==========
    sort_error = [None]

    def sort_worker():
        try:
            from tools.sort_parquet_by_symbol import sort_single_file
            for i, (raw, sorted_path) in enumerate(zip(raw_files, sorted_files)):
                if os.path.exists(sorted_path) and os.path.getsize(sorted_path) > 0:
                    if i < 3 or i % 50 == 0:
                        logging.info(f'[SORT] Skip (exists): {os.path.basename(raw)}')
                    continue
                stats = sort_single_file(raw, sorted_path)
                if (i + 1) % 10 == 0 or i == 0:
                    done = sum(1 for p in sorted_files if os.path.exists(p))
                    logging.info(
                        f'[SORT] {i+1}/{len(raw_files)} | {os.path.basename(raw)} | '
                        f'{stats["rows"]/1e6:.1f}M rows | {stats["seconds"]:.1f}s | '
                        f'{done} files ready'
                    )
            logging.info(f'[SORT] Complete: all {len(raw_files)} files sorted')
        except Exception as e:
            sort_error[0] = e
            logging.error(f'[SORT] FAILED: {e}', exc_info=True)

    sort_thread = threading.Thread(target=sort_worker, name='sort-worker', daemon=True)
    sort_thread.start()
    logging.info('[PIPELINE] Sort thread started')

    # ========== WAIT FOR HEAD START ==========
    logging.info(f'[PIPELINE] Waiting for {HEAD_START_FILES} sorted files...')
    while True:
        if sort_error[0]:
            logging.error(f'[PIPELINE] Sort failed, aborting: {sort_error[0]}')
            sys.exit(1)
        ready = sum(1 for p in sorted_files if os.path.exists(p))
        if ready >= HEAD_START_FILES or ready >= len(sorted_files):
            break
        time.sleep(10)
    logging.info(f'[PIPELINE] {ready} files ready, launching ETL')

    # ========== START ETL (with wait_for_files) ==========
    from tools.omega_etl_v3_topo_forge import topo_forge_pipeline

    try:
        topo_forge_pipeline(
            raw_parquet_dir=SORTED_DIR,
            output_tar_dir=SHARD_DIR,
            c_registry_path=C_REGISTRY,
            batch_size=100000,
            file_list_path=file_list_path,
            workers=WORKERS,
            checkpoint_interval=50,
            wait_for_files=True,
        )
        rc = 0
    except Exception as e:
        logging.error(f'[PIPELINE] ETL FAILED: {e}', exc_info=True)
        rc = 1

    # Wait for sort to finish (should be done by now)
    sort_thread.join(timeout=60)

    flag_path = os.path.join(SHARD_DIR, 'pipeline_v5_done.flag')
    with open(flag_path, 'w') as f:
        f.write(str(rc))
    logging.info(f'[PIPELINE] Done. Exit code: {rc}')
    sys.exit(rc)
