import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import re
import os

# === CONFIGURATION ===
ACCESS_CODE = "TacoTuesday47"
LOGIN_URL = "https://flow.tradingedge.club/Login.aspx?ReturnUrl=%2f&AspxAutoDetectCookieSupport=1"
DATA_URL_TEMPLATE = "https://flow.tradingedge.club/default.aspx?Date={}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

DAILY_OUTPUT_DIR = r"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\1. Daily_Flow"

session = requests.Session()
session.headers.update(HEADERS)

def login_to_site():
    resp = session.get(LOGIN_URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    tokens = {
        "__VIEWSTATE": soup.find("input", {"name": "__VIEWSTATE"})["value"],
        "__VIEWSTATEGENERATOR": soup.find("input", {"name": "__VIEWSTATEGENERATOR"})["value"],
        "__EVENTVALIDATION": soup.find("input", {"name": "__EVENTVALIDATION"})["value"]
    }
    payload = {
        "__VIEWSTATE": tokens["__VIEWSTATE"],
        "__VIEWSTATEGENERATOR": tokens["__VIEWSTATEGENERATOR"],
        "__EVENTVALIDATION": tokens["__EVENTVALIDATION"],
        "m_userName": ACCESS_CODE,
        "m_btnLogin": "Confirm Identity"
    }
    response = session.post(LOGIN_URL, data=payload)
    return "Unusual Options Flow" in response.text

def clean_strike(val):
    try:
        return float(re.split(r"[^\d.]+", str(val).strip())[0])
    except:
        return None

def convert_premium(p):
    if isinstance(p, str):
        p = p.strip().upper().replace(",", "")
        if p.endswith("M"):
            return float(p[:-1]) * 1_000_000
        elif p.endswith("K"):
            return float(p[:-1]) * 1_000
        else:
            try:
                return float(p)
            except:
                return None
    return None

def scrape_most_recent_day_with_data():
    today = datetime.today()
    one_day = timedelta(days=1)
    current_day = today

    while True:
        if current_day.weekday() >= 5:
            current_day -= one_day
            continue

        scrape_date = current_day.strftime("%Y-%m-%d")
        url = DATA_URL_TEMPLATE.format(scrape_date)
        resp = session.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = []
        table_headers = soup.find_all("th", class_="table-light")

        for th in table_headers:
            title_attr = th.get("title", "").strip().lower()
            if title_attr in ["bullish", "bearish"]:
                flow_type = "Bullish" if title_attr == "bullish" else "Bearish"
                table = th.find_parent("table")
                if table:
                    tbody = table.find("tbody", class_="table-group-divider")
                    if tbody:
                        for row in tbody.find_all("tr"):
                            cells = row.find_all("td")
                            if len(cells) >= 4:
                                rows.append({
                                    "date": scrape_date,
                                    "flow_type": flow_type,
                                    "ticker": cells[0].text.strip().upper(),
                                    "strike": clean_strike(cells[1].text.strip()),
                                    "exp": cells[2].text.strip(),  # ✅ FIXED LINE
                                    "premium": convert_premium(cells[3].text.strip())
                                })

        if rows:
            df = pd.DataFrame(rows)

            # === Clean & Format Columns ===
            df["date"] = pd.to_datetime(df["date"])
            df["exp"] = pd.to_datetime(df["exp"], errors="coerce")

            df.sort_values(by=["ticker", "date"], inplace=True)

            # === Feature Engineering for ML ===
            df["days_since_last_flow"] = df.groupby("ticker")["date"].diff().dt.days.fillna(-1)

            df["hits_past_7_days"] = 0
            for ticker, group in df.groupby("ticker"):
                dates = group["date"].values
                counts = []
                for i in range(len(dates)):
                    window_start = dates[i] - np.timedelta64(7, 'D')
                    count = np.sum((dates >= window_start) & (dates <= dates[i]))
                    counts.append(count)
                df.loc[group.index, "hits_past_7_days"] = counts

            df["rolling_premium_3d"] = df.groupby("ticker")["premium"].transform(
                lambda x: x.rolling(window=3, min_periods=1).mean())
            df["rolling_premium_7d"] = df.groupby("ticker")["premium"].transform(
                lambda x: x.rolling(window=7, min_periods=1).mean())
            df["premium_spike"] = (df["premium"] > (3 * df["rolling_premium_3d"])).astype(int)
            df["flow_type_binary"] = df["flow_type"].str.lower().map({"bullish": 1, "bearish": 0}).fillna(0).astype(int)

            # === Output ===
            filename = f"flow_{scrape_date}.csv"
            full_path = os.path.join(DAILY_OUTPUT_DIR, filename)
            df.to_csv(full_path, index=False)
            print(f"✅ Found data! Scraped and saved {len(df)} rows to: {filename}")
            break
        else:
            print(f"⏳ No data for {scrape_date}, checking previous day...")
            current_day -= one_day

# === RUN ===
if __name__ == "__main__":
    if login_to_site():
        scrape_most_recent_day_with_data()
    else:
        print("❌ Login failed — check access code or site layout.")
pyth