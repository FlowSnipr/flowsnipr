import os
import re
import pandas as pd
import yfinance as yf
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands
from tqdm import tqdm

# === CONFIGURATION ===
enhanced_folder = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow"

# === IDENTIFY MOST RECENT FILE ===
files = [f for f in os.listdir(enhanced_folder) if re.match(r"flow_\d{4}-\d{2}-\d{2}_with_volume\.csv", f)]
dates = [datetime.strptime(re.search(r"\d{4}-\d{2}-\d{2}", f).group(), "%Y-%m-%d") for f in files]
latest_date = max(dates)
latest_date_str = latest_date.strftime("%Y-%m-%d")

# === INPUT/OUTPUT PATHS ===
input_path = os.path.join(enhanced_folder, f"flow_{latest_date_str}_with_volume.csv")
output_path = os.path.join(enhanced_folder, f"flow_{latest_date_str}_with_TA.csv")

# === LOAD FLOW DATA ===
df = pd.read_csv(input_path)
df["ticker"] = df["ticker"].str.strip().str.upper()

# === Prepare to Store TA Results ===
ta_data = []

tickers = df["ticker"].unique()

for ticker in tqdm(tickers, desc="Pulling TA for tickers"):
    try:
        hist = yf.download(ticker, start="2023-10-01", end=latest_date_str, progress=False)

        if isinstance(hist.columns, pd.MultiIndex):
            hist.columns = hist.columns.get_level_values(0)

        if hist.empty or not all(col in hist.columns for col in ["High", "Low", "Close", "Volume"]):
            continue

        hist = hist[["High", "Low", "Close", "Volume"]].dropna()

        # === Add TA Indicators ===
        hist["rsi_14"] = RSIIndicator(close=hist["Close"]).rsi()
        hist["ema_9"] = EMAIndicator(close=hist["Close"], window=9).ema_indicator()
        hist["ema_21"] = EMAIndicator(close=hist["Close"], window=21).ema_indicator()
        macd = MACD(close=hist["Close"])
        hist["macd_line"] = macd.macd()
        hist["macd_signal"] = macd.macd_signal()
        bb = BollingerBands(close=hist["Close"])
        hist["bb_percent_b"] = bb.bollinger_pband()
        hist["ADX"] = ADXIndicator(high=hist["High"], low=hist["Low"], close=hist["Close"]).adx()
        hist["Volume_ZScore"] = (hist["Volume"] - hist["Volume"].rolling(20).mean()) / hist["Volume"].rolling(20).std()
        hist["MA_50"] = hist["Close"].rolling(50).mean()
        hist["Price_vs_50MA"] = hist["Close"] / hist["MA_50"]
        hist["Close_shift_5d"] = hist["Close"].shift(5)
        hist["underlying_price"] = hist["Close"]

        # === Extract TA Values for Latest Day Only ===
        latest_indicators = hist.iloc[-1][[
            "rsi_14", "ema_9", "ema_21", "macd_line", "macd_signal", "bb_percent_b",
            "ADX", "Volume_ZScore", "MA_50", "Price_vs_50MA", "Close_shift_5d", "underlying_price"
        ]].to_dict()

        latest_indicators["ticker"] = ticker
        ta_data.append(latest_indicators)

    except Exception as e:
        print(f"❌ Error processing {ticker}: {e}")

# === Merge TA Data Back into Original Flow ===
ta_df = pd.DataFrame(ta_data)
merged_df = pd.merge(df, ta_df, on="ticker", how="left")

# === SAVE OUTPUT ===
merged_df.to_csv(output_path, index=False)
print(f"✅ TA indicators added and saved to: {output_path}")
