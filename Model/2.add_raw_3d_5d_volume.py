import os
import re
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# === CONFIGURATION ===
daily_flow_folder = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\1. Daily_Flow"
output_folder = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow"

# === FIND LATEST FLOW FILE ===
flow_files = [f for f in os.listdir(daily_flow_folder) if re.match(r"flow_\d{4}-\d{2}-\d{2}\.csv", f)]
dates = [datetime.strptime(re.search(r"\d{4}-\d{2}-\d{2}", f).group(), "%Y-%m-%d") for f in flow_files]
latest_date = max(dates)
latest_date_str = latest_date.strftime("%Y-%m-%d")

# === LOAD FILE ===
input_file = os.path.join(daily_flow_folder, f"flow_{latest_date_str}.csv")
df = pd.read_csv(input_file)
df["date"] = pd.to_datetime(df["date"])
tickers = df["ticker"].dropna().unique()

# === SET RANGE FOR VOLUME LOOKBACK (10 calendar days to catch weekends) ===
start_date = (latest_date - timedelta(days=10)).strftime("%Y-%m-%d")
end_date = (latest_date + timedelta(days=1)).strftime("%Y-%m-%d")

results = []

# === FETCH VOLUME DATA ===
for ticker in tickers:
    print(f"📈 Fetching volume for {ticker}...")
    try:
        hist = yf.download(ticker, start=start_date, end=end_date, interval="1d", progress=False)
        if hist.empty:
            print(f"⚠️ No data for {ticker}")
            continue

        hist = hist[["Volume"]].reset_index()
        hist["Date"] = pd.to_datetime(hist["Date"]).dt.normalize()
        hist = hist.rename(columns={"Date": "date"})

        # Ensure dates match precisely
        flow_date = latest_date.replace(hour=0, minute=0, second=0, microsecond=0)
        row = hist[hist["date"] == flow_date]
        volume_raw = float(row["Volume"].iloc[0]) if not row.empty else None

        # Get averages of the previous 3 and 5 trading days
        prev_days = hist[hist["date"] < flow_date].sort_values("date", ascending=False)
        volume_avg_3d = float(prev_days["Volume"].head(3).mean()) if not prev_days.empty else None
        volume_avg_5d = float(prev_days["Volume"].head(5).mean()) if not prev_days.empty else None

        results.append({
            "ticker": ticker,
            "volume_raw": volume_raw,
            "volume_avg_3d": volume_avg_3d,
            "volume_avg_5d": volume_avg_5d
        })

    except Exception as e:
        print(f"❌ Error fetching {ticker}: {e}")
        results.append({
            "ticker": ticker,
            "volume_raw": None,
            "volume_avg_3d": None,
            "volume_avg_5d": None
        })

# === SAVE OUTPUT ===
out_df = pd.DataFrame(results)
output_file = os.path.join(output_folder, f"volume_raw_avg_3d_5d_{latest_date_str}.csv")
out_df.to_csv(output_file, index=False)
print(f"\n✅ Saved volume enrichment file:\n{output_file}")
