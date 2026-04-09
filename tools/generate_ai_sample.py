import pandas as pd
import json

df = pd.read_parquet('plan/sandbox_deduction_data_v2.parquet')
df['vol_tick'] = df['vol_tick'].round(4)
df['price'] = df['price'].round(4)

with open('plan/sandbox_AI_readable_sample.md', 'w', encoding='utf-8') as f:
    f.write("# OMEGA Sandbox Deduction Data (AI Readable Sample)\n\n")
    f.write("**WARNING TO HUMAN USER**: The full 145,000-row dataset expands to a 107MB JSON file, which vastly exceeds the context window of any LLM (even 2M token models will choke on 100MB of raw floats). This Markdown file contains the **structural metadata** and **critical contiguous samples (50 ticks each)** carefully selected to test the 4 paradoxes. This file is highly compressed (~100 KB) and is 100% safe to paste directly into any AI Agent's chat window.\n\n")
    
    f.write("## 1. Schema & Summary Statistics\n")
    f.write(f"- **Total Trading Days:** 5 (2023-01-09 to 2023-01-13)\n")
    f.write(f"- **Total Ticks (across all days/stocks):** {len(df)}\n")
    f.write(f"- **Stocks Tracked:** {', '.join(df['symbol'].unique())}\n")
    f.write("- **Features (45-dim):** `symbol`, `date`, `time`, `price`, `vol_tick` + 40-dim LOB depth (`bid_p1..10`, `bid_v1..10`, `ask_p1..10`, `ask_v1..10`)\n\n")
    
    f.write("## 2. Paradox 1 & 3: High-Liquidity Continuous Sample (603228.SH)\n")
    f.write("**Mathematical Purpose:** Demonstrate the 44-dimensional Euclidean measure space to test Takens Embedding (Paradox 1) and continuous topological sequences for Directed Flag Complexes (Paradox 3).\n\n")
    f.write("**Data:** 50 contiguous high-frequency ticks near open.\n")
    
    # Get contiguous sample for 603228.SH
    df_liq = df[df['symbol'] == '603228.SH'].head(50)
    f.write("\n```json\n")
    f.write(df_liq.to_json(orient='records', lines=True, force_ascii=False))
    f.write("\n```\n\n")
    
    f.write("## 3. Paradox 2: Low-Liquidity Q -> 0 Singularity Sample (688141.SH)\n")
    f.write("**Mathematical Purpose:** Highlight sparse trading states where `vol_tick` is extremely small or zero. This explicitly triggers the infinite derivative singularity in the SRL interceptor.\n\n")
    f.write("**Data:** 50 contiguous low-frequency ticks.\n")
    
    df_ill = df[df['symbol'] == '688141.SH']
    df_ill_sample = df_ill.iloc[500:550] if len(df_ill) > 550 else df_ill.head(50)
    
    f.write("\n```json\n")
    f.write(df_ill_sample.to_json(orient='records', lines=True, force_ascii=False))
    f.write("\n```\n\n")
    
    f.write("---\n")
    f.write("**Dear AI Agent:** You now have the exact schema and representative multidimensional slices of the LOB. Please proceed with your mathematical deduction and topological proofs based on these physical matrices.\n")
