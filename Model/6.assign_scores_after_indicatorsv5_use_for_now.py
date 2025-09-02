import os
import re
import pandas as pd
import numpy as np
from datetime import datetime

# === CONFIGURATION ===
enhanced_dir = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow"
master_dir = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\0. Master_Flow"

# === Auto-detect latest enriched master flow (with underlying prices) ===
master_files = [f for f in os.listdir(master_dir) if re.match(r"Master_Flow_Up_to_\d{4}-\d{2}-\d{2}_with_prices\.csv", f)]
if not master_files:
    raise FileNotFoundError("❌ No enriched master flow files found in directory:\n" + master_dir)

master_dates = [re.search(r"\d{4}-\d{2}-\d{2}", f).group() for f in master_files]
latest_master_date = max(master_dates)
master_path = os.path.join(master_dir, f"Master_Flow_Up_to_{latest_master_date}_with_prices.csv")

# === Auto-detect latest TA + Rolling file ===
ta_files = [f for f in os.listdir(enhanced_dir) if re.match(r"flow_\d{4}-\d{2}-\d{2}_with_TA_and_rolling\.csv", f)]
if not ta_files:
    raise FileNotFoundError("❌ No 'flow_YYYY-MM-DD_with_TA_and_rolling.csv' files found in directory:\n" + enhanced_dir)

ta_dates = [re.search(r"\d{4}-\d{2}-\d{2}", f).group() for f in ta_files]
latest_ta_date = max(ta_dates)
input_path = os.path.join(enhanced_dir, f"flow_{latest_ta_date}_with_TA_and_rolling.csv")
output_path = os.path.join(enhanced_dir, f"flow_{latest_ta_date}_final_enriched.csv")

# === Load datasets ===
master_df = pd.read_csv(master_path)
today_df = pd.read_csv(input_path)
master_df["source"] = "master"
today_df["source"] = "today"

# === Combine for historical context ===
df = pd.concat([master_df, today_df], ignore_index=True)

# === Ensure numeric conversion ===
for col in ["premium", "rolling_premium_3d", "hits_past_7_days", "underlying_price", "strike"]:
    if col not in df.columns:
        print(f"❌ Required column '{col}' not found in dataset. Filling with NaN.")
        df[col] = np.nan
    df[col] = pd.to_numeric(df[col], errors="coerce")

# === Drop invalid rows ===
invalid_mask = df["strike"].isna() | df["underlying_price"].isna() | (df["underlying_price"] == 0)
if invalid_mask.sum() > 0:
    print(f"⚠️ Dropping {invalid_mask.sum()} rows with invalid strike/underlying_price.")
    df = df[~invalid_mask]

# === Calculate Score (Option A) ===
df["score"] = (
    df["premium"] *
    (df["rolling_premium_3d"] + 1) *
    np.sqrt(df["hits_past_7_days"] + 1)
).round(2)

# === Calculate Uniqueness Score per ticker ===
df["uniqueness_percentile"] = df.groupby("ticker")["score"].rank(pct=True)
df["uniqueness_score_1_to_10"] = (df["uniqueness_percentile"] * 10).round(2)
df.drop(columns=["uniqueness_percentile"], inplace=True)

# === Calculate Moneyness Z-Score per ticker ===
df["raw_moneyness"] = (df["strike"] - df["underlying_price"]) / df["underlying_price"]
df["moneyness_zscore"] = df.groupby("ticker")["raw_moneyness"].transform(
    lambda x: (x - x.mean()) / x.std(ddof=0) if x.std(ddof=0) != 0 else 0
).round(4)
df.drop(columns=["raw_moneyness"], inplace=True)

# === Filter back to today's flow only ===
final_today = df[df["source"] == "today"].drop(columns=["source"])
final_today.to_csv(output_path, index=False)

print(f"✅ Final enriched file with training-aligned scores saved to:\n{output_path}")
