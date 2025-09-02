import os
import re
import pandas as pd
from datetime import datetime

# === CONFIGURATION ===
master_dir = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\0. Master_Flow"
enhanced_dir = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow"

# === Identify Latest Master Flow File ===
master_files = [f for f in os.listdir(master_dir) if re.match(r"Master_Flow_Up_to_\d{4}-\d{2}-\d{2}\.csv", f)]
master_dates = [re.search(r"\d{4}-\d{2}-\d{2}", f).group() for f in master_files]
latest_master_date = max(master_dates)
master_path = os.path.join(master_dir, f"Master_Flow_Up_to_{latest_master_date}.csv")

# === Identify Latest Daily TA-Enriched File ===
ta_files = [f for f in os.listdir(enhanced_dir) if re.match(r"flow_\d{4}-\d{2}-\d{2}_with_TA\.csv", f)]
ta_dates = [re.search(r"\d{4}-\d{2}-\d{2}", f).group() for f in ta_files]
latest_ta_date = max(ta_dates)
ta_path = os.path.join(enhanced_dir, f"flow_{latest_ta_date}_with_TA.csv")

# === Load Data ===
master_df = pd.read_csv(master_path)
today_df = pd.read_csv(ta_path)

# === Cleanup old rolling columns if they exist ===
for col in ["rolling_premium_3d", "rolling_premium_7d"]:
    if col in today_df.columns:
        today_df.drop(columns=col, inplace=True)

# === Ensure 'date' column is datetime format ===
master_df["date"] = pd.to_datetime(master_df["date"], errors="coerce")
today_df["date"] = pd.to_datetime(today_df["date"], errors="coerce")

# === Merge for calculation only ===
combined = pd.concat([master_df, today_df], ignore_index=True)
combined.drop_duplicates(subset=["date", "ticker", "strike", "premium"], inplace=True)
combined.sort_values(by=["ticker", "date"], inplace=True)

# === Ensure premium is numeric ===
combined["premium"] = pd.to_numeric(combined["premium"], errors="coerce").fillna(0)

# === Calculate Rolling Premiums ===
combined["rolling_premium_3d"] = combined.groupby("ticker")["premium"].transform(
    lambda x: x.rolling(window=3, min_periods=1).sum()
)
combined["rolling_premium_7d"] = combined.groupby("ticker")["premium"].transform(
    lambda x: x.rolling(window=7, min_periods=1).sum()
)

# === Merge the rolling values BACK into today's dataframe ===
today_key = today_df[["date", "ticker", "strike", "premium"]].copy()
today_key["date"] = pd.to_datetime(today_key["date"])
combined_latest = combined[["date", "ticker", "strike", "premium", "rolling_premium_3d", "rolling_premium_7d"]]

# === Merge by multiple keys to preserve row integrity ===
merged_today = pd.merge(
    today_df,
    combined_latest,
    on=["date", "ticker", "strike", "premium"],
    how="left"
)

# === Save Output ===
output_path = os.path.join(enhanced_dir, f"flow_{latest_ta_date}_with_TA_and_rolling.csv")
merged_today.to_csv(output_path, index=False)
print(f"✅ Final output saved without row duplication:\n{output_path}")
