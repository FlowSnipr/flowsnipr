import pandas as pd
import joblib
import os
import re

# === CONFIGURATION ===
model_dir = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\5. Models"
data_path = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\2. Enhanced_Flow\flow_2025-07-10_final_ready_with_days_until_exp.csv"

# === Extract date from filename ===
match = re.search(r"flow_(\d{4}-\d{2}-\d{2})", os.path.basename(data_path))
if not match:
    raise ValueError("❌ Could not extract date from filename. Make sure the file follows 'flow_YYYY-MM-DD_*.csv' format.")
flow_date = match.group(1)

output_path_meta_top3 = os.path.join(
    r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\4. Predictions",
    f"meta_model_top3_predictions_{flow_date}.csv"
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

# === Meta Model Predictions ===
df["meta_prediction"] = meta_model.predict(X_meta)
df["meta_confidence"] = meta_model.predict_proba(X_meta)[:, 1]

# === Extract Top 3 Unique Ticker Predictions ===
top_preds = (
    df[df["meta_prediction"] == 1]
    .sort_values("meta_confidence", ascending=False)
    .drop_duplicates(subset="ticker")
    .head(3)
)

# === Save Output ===
top3 = top_preds[["date", "ticker", "premium", "underlying_price", "strike", "exp", "meta_confidence"]]
top3.to_csv(output_path_meta_top3, index=False)

print(f"\n✅ Top 3 Unique Ticker Predictions saved to:\n{output_path_meta_top3}")
print(top3)
