import os
import re
import pandas as pd
from datetime import datetime

# === CONFIGURATION ===
flow_folder = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow"

# === Auto-detect latest enriched daily flow with _final_ready ===
flow_files = [f for f in os.listdir(flow_folder) if re.match(r"flow_\d{4}-\d{2}-\d{2}_final_ready\.csv", f)]
if not flow_files:
    raise FileNotFoundError("❌ No 'flow_YYYY-MM-DD_final_ready.csv' files found.")

# === Extract latest date from filename ===
flow_dates = [re.search(r"\d{4}-\d{2}-\d{2}", f).group() for f in flow_files]
latest_date = max(flow_dates)
input_path = os.path.join(flow_folder, f"flow_{latest_date}_final_ready.csv")
output_path = input_path.replace(".csv", "_with_days_until_exp.csv")

# === Load dataset ===
df = pd.read_csv(input_path)

# === Convert date columns ===
df["date"] = pd.to_datetime(df["date"])
df["exp"] = pd.to_datetime(df["exp"])

# === Calculate days until expiration ===
df["days_until_exp"] = (df["exp"] - df["date"]).dt.days

# === Save result ===
df.to_csv(output_path, index=False)
print(f"✅ 'days_until_exp' added and saved to:\n{output_path}")
