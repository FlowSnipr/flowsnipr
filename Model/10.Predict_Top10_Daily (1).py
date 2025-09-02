import pandas as pd
import joblib
import os
import re
import glob
from datetime import datetime

# === CONFIGURATION ===
model_dir = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\5. Models"
enhanced_flow_dir = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow"
predictions_dir = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\4. Predictions"

# === Find Most Recent CSV File ===
file_pattern = os.path.join(enhanced_flow_dir, "flow_????-??-??_final_ready_with_days_until_exp.csv")
all_files = glob.glob(file_pattern)

if not all_files:
    raise FileNotFoundError("❌ No flow files found in Enhanced_Flow directory.")

def extract_date(file_path):
    match = re.search(r"flow_(\d{4}-\d{2}-\d{2})", os.path.basename(file_path))
    return datetime.strptime(match.group(1), "%Y-%m-%d") if match else None

dated_files = [(f, extract_date(f)) for f in all_files]
dated_files = [pair for pair in dated_files if pair[1] is not None]
most_recent_file, most_recent_date = max(dated_files, key=lambda x: x[1])
flow_date = most_recent_date.strftime("%Y-%m-%d")
data_path = most_recent_file

# === Output Path ===
output_path_meta_top10 = os.path.join(
    predictions_dir,
    f"meta_model_top10_predictions_{flow_date}.csv"
)

# === Load Models ===
rf_model = joblib.load(os.path.join(model_dir, "rf_classifier_model.pkl"))
xgb_model = joblib.load(os.path.join(model_dir, "xgb_classifier_model.pkl"))
meta_model = joblib.load(os.path.join(model_dir, "stacked_meta_model_retrained_regularizedv2.pkl"))

# === Load Daily Data ===
df = pd.read_csv(data_path)

# === Features Used for Base Models ===
features = [
    "premium", "days_since_last_flow", "hits_past_7_days", "rolling_premium_3d", "rolling_premium_7d",
    "rsi_14", "ema_9", "ema_21", "macd_line", "macd_signal", "bb_percent_b", "ADX", "Volume_ZScore",
    "MA_50", "Price_vs_50MA", "Close_shift_5d", "score", "uniqueness_score_1_to_10", "flow_type_binary",
    "underlying_price", "moneyness_zscore", "volume_raw", "volume_avg_3d", "volume_avg_5d",
    "volume_spike_flag", "days_until_exp"
]
X = df[features].copy()

# === Base Model Predictions ===
df["rf_prediction"] = rf_model.predict(X)
df["rf_probability"] = rf_model.predict_proba(X)[:, 1]
df["xgb_prediction"] = xgb_model.predict(X)
df["xgb_probability"] = xgb_model.predict_proba(X)[:, 1]

# === Meta Model Input Features ===
meta_features = [
    "rf_prediction", "rf_probability", "xgb_prediction", "xgb_probability", "score",
    "rsi_14", "ema_9", "ema_21", "macd_line", "macd_signal", "bb_percent_b", "ADX",
    "Volume_ZScore", "MA_50", "Price_vs_50MA", "Close_shift_5d", "volume_raw", "days_until_exp"
]
X_meta = df[meta_features].copy()

# === Handle NaNs ===
X_meta = X_meta.dropna()
df = df.loc[X_meta.index]

# === Meta Model Predictions ===
df["meta_prediction"] = meta_model.predict(X_meta)
df["meta_confidence"] = meta_model.predict_proba(X_meta)[:, 1]

# === Extract Top 10 Unique Ticker Predictions ===
top_preds = (
    df[df["meta_prediction"] == 1]
    .sort_values("meta_confidence", ascending=False)
    .drop_duplicates(subset="ticker")
    .head(10)
)

# === Save Output ===
top10 = top_preds[["date", "ticker", "premium", "underlying_price", "strike", "exp", "meta_confidence"]]
top10.to_csv(output_path_meta_top10, index=False)

print(f"\n✅ Top 10 Unique Ticker Predictions saved to:\n{output_path_meta_top10}")
print(top10)
