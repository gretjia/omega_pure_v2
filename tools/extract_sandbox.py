import os
import datetime
from glob import glob
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import gc

# The stocks
target_symbols = ['603228.SH', '688141.SH', '002008.SZ', '688521.SH']

base_dir = "/omega_pool/parquet_data/latest_base_l1_sorted"
if not os.path.exists(base_dir):
    print("Sorted dir not found. Using raw dir.")
    base_dir = "/omega_pool/parquet_data/latest_base_l1"

print(f"Scanning directory: {base_dir}")

files = []
for root, dirs, f_names in os.walk(base_dir):
    for f in f_names:
        if f.endswith('.parquet'):
            files.append(os.path.join(root, f))

files.sort(key=lambda x: os.path.basename(x)[:8])
print(f"Found {len(files)} parquet files.")

dates_files = []
for f in files:
    basename = os.path.basename(f)
    date_str = basename[:8]
    if date_str.isdigit():
        dt = datetime.datetime.strptime(date_str, "%Y%m%d")
        dates_files.append((dt, f))

selected_files = []
for i in range(len(dates_files) - 4):
    dt, f = dates_files[i]
    if dt.weekday() == 0: # Monday
        selected_files = [x[1] for x in dates_files[i:i+5]]
        print(f"Found week starting: {dt.strftime('%Y-%m-%d')} (Monday)")
        for sf in selected_files:
            print("  ", os.path.basename(sf))
        break

if not selected_files:
    print("Could not find a sequence starting on a Monday.")
    exit(1)

# Inspect first file to get actual columns
schema = pq.read_schema(selected_files[0])
all_cols = schema.names

lob_cols = []
for lvl in range(1, 11):
    lob_cols.extend([f'bid_p{lvl}', f'bid_v{lvl}', f'ask_p{lvl}', f'ask_v{lvl}'])

core_cols = ['symbol', 'date', 'price', 'vol_tick']
if 'time' in all_cols:
    core_cols.append('time')
if 'timestamp' in all_cols:
    core_cols.append('timestamp')

columns_to_keep = [c for c in core_cols + lob_cols if c in all_cols]

print(f"Extracting {len(columns_to_keep)} columns: {columns_to_keep}")

# Combine datasets carefully to avoid OOM
all_tables = []
for sf in selected_files:
    print(f"Processing {os.path.basename(sf)}...")
    dataset = ds.dataset([sf], format="parquet")
    table = dataset.to_table(
        filter=ds.field('symbol').isin(target_symbols),
        columns=columns_to_keep
    )
    print(f"  Extracted {table.num_rows} rows.")
    if table.num_rows > 0:
        all_tables.append(table)
    gc.collect()

import pyarrow as pa
if all_tables:
    final_table = pa.concat_tables(all_tables)
    
    # Sort by symbol, then date/timestamp if available
    sort_keys = [('symbol', 'ascending')]
    if 'timestamp' in final_table.column_names:
        sort_keys.append(('timestamp', 'ascending'))
    elif 'time' in final_table.column_names:
        sort_keys.append(('date', 'ascending'))
        sort_keys.append(('time', 'ascending'))
    else:
         sort_keys.append(('date', 'ascending'))
        
    try:
        import pyarrow.compute as pc
        sorted_indices = pc.sort_indices(final_table, sort_keys=sort_keys)
        final_table = final_table.take(sorted_indices)
        print("Sorted table by symbol and time.")
    except Exception as e:
        print(f"Warning: could not sort table: {e}")

    out_path = "/home/zepher/sandbox_deduction_data_v2.parquet"
    print(f"Total rows: {final_table.num_rows}. Writing to {out_path} ...")
    pq.write_table(final_table, out_path)
    print("Done!")
else:
    print("No data extracted for the selected symbols.")

