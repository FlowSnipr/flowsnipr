import os
import re
import pandas as pd
from datetime import datetime

# === CONFIGURATION ===
enhanced_folder = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow"

# === FIND LATEST FINAL ENRICHED FILE ===
pattern = r"flow_(\d{4}-\d{2}-\d{2})_final_enriched\.csv"
flow_files = [f for f in os.listdir(enhanced_folder) if re.match(pattern, f)]

if not flow_files:
    raise FileNotFoundError("❌ No 'flow_YYYY-MM-DD_final_enriched.csv' files found.")

latest_file = max(flow_files, key=lambda f: datetime.strptime(re.search(pattern, f).group(1), "%Y-%m-%d"))
latest_date = re.search(pattern, latest_file).group(1)
input_path = os.path.join(enhanced_folder, latest_file)
output_path = os.path.join(enhanced_folder, f"flow_{latest_date}_final_ready.csv")

# === LOAD FILE ===
df = pd.read_csv(input_path)

# === CHECK REQUIRED COLUMNS ===
required_cols = ["volume_raw", "volume_avg_5d"]
missing = [col for col in required_cols if col not in df.columns]
if missing:
    raise ValueError(f"❌ Missing required columns: {missing}")

# === ADD VOLUME SPIKE FLAG ===
df["volume_spike_flag"] = (df["volume_raw"] >= 1.5 * df["volume_avg_5d"]).astype(int)

# === SAVE OUTPUT ===
df.to_csv(output_path, index=False)
print(f"✅ Volume spike flag added and file saved to:\n{output_path}")
