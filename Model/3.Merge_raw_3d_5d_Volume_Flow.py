import os
import re
import pandas as pd
from datetime import datetime

# === CONFIGURATION ===
daily_flow_folder = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\1. Daily_Flow"
enhanced_folder = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow"

# === DETECT LATEST FLOW FILE ===
flow_files = [f for f in os.listdir(daily_flow_folder) if re.match(r"flow_\d{4}-\d{2}-\d{2}\.csv", f)]
dates = [datetime.strptime(re.search(r"\d{4}-\d{2}-\d{2}", f).group(), "%Y-%m-%d") for f in flow_files]
latest_date = max(dates)
latest_date_str = latest_date.strftime("%Y-%m-%d")

# === CONSTRUCT FILE PATHS ===
daily_flow_file = os.path.join(daily_flow_folder, f"flow_{latest_date_str}.csv")
volume_data_file = os.path.join(enhanced_folder, f"volume_raw_avg_3d_5d_{latest_date_str}.csv")
output_file = os.path.join(enhanced_folder, f"flow_{latest_date_str}_with_volume.csv")

# === LOAD FILES ===
flow_df = pd.read_csv(daily_flow_file)
volume_df = pd.read_csv(volume_data_file)

# === MERGE ON TICKER ===
merged_df = pd.merge(flow_df, volume_df, on="ticker", how="left")

# === SAVE RESULT ===
merged_df.to_csv(output_file, index=False)
print(f"✅ Merged file saved to:\n{output_file}")
