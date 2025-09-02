import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os

# === CONFIGURATION ===
ACCESS_CODE = "TacoTuesday47"
LOGIN_URL = "https://flow.tradingedge.club/Login.aspx?ReturnUrl=%2f&AspxAutoDetectCookieSupport=1"
DATA_URL_TEMPLATE = "https://flow.tradingedge.club/default.aspx?Date={}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# === SESSION SETUP ===
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

def is_weekend(date):
    return date.weekday() >= 5

def parse_table(tbody, date_str, flow_type):
    rows = []
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 4:
            rows.append({
                "date": date_str,
                "flow_type": flow_type,
                "ticker": cells[0].text.strip().upper(),
                "strike": cells[1].text.strip(),
                "exp": cells[2].text.strip(),
                "premium": cells[3].text.strip()
            })
    return rows

def scrape_for_date(date_str):
    url = DATA_URL_TEMPLATE.format(date_str)
    resp = session.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")
    print(f"[{date_str}] Page title: {soup.title.string if soup.title else 'No title'}")

    all_rows = []
    table_headers = soup.find_all("th", class_="table-light")

    for th in table_headers:
        title_attr = th.get("title", "").strip().lower()
        if title_attr in ["bullish", "bearish"]:
            flow_type = "Bullish" if title_attr == "bullish" else "Bearish"
            table = th.find_parent("table")
            if table:
                tbody = table.find("tbody", class_="table-group-divider")
                if tbody:
                    parsed_rows = parse_table(tbody, date_str, flow_type)
                    print(f"[{date_str}] {flow_type} table: {len(parsed_rows)} rows")
                    all_rows.extend(parsed_rows)

    if not all_rows:
        print(f"[{date_str}] No directional flow tables found.")
    return all_rows

def clean_premium(val):
    val = val.replace(",", "").replace("$", "").strip().upper()
    if val.endswith("M"):
        return float(val[:-1]) * 1_000_000
    elif val.endswith("K"):
        return float(val[:-1]) * 1_000
    else:
        return float(val)

def clean_strike(val):
    try:
        return float(val.strip().split()[0])
    except:
        return None

# === MAIN EXECUTION ===
if not login_to_site():
    print("❌ Login failed. Check your access code.")
    exit()

start_date = datetime.strptime("2025-03-11", "%Y-%m-%d")
end_date = datetime.today()

current_date = start_date
all_data = []

while current_date <= end_date:
    if not is_weekend(current_date):
        date_str = current_date.strftime("%Y-%m-%d")
        day_data = scrape_for_date(date_str)
        all_data.extend(day_data)
    current_date += timedelta(days=1)

# === Convert to DataFrame ===
df = pd.DataFrame(all_data)

# === Clean & Enrich ===
df["date"] = pd.to_datetime(df["date"])
df["strike"] = df["strike"].apply(clean_strike)
df["exp"] = pd.to_datetime(df["exp"], errors="coerce")
df["premium"] = df["premium"].apply(clean_premium)

df.sort_values(by=["ticker", "date"], inplace=True)

# === Feature engineering ===
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

# === Flow Type Binary ===
df["flow_type_binary"] = df["flow_type"].str.lower().map({"bullish": 1, "bearish": 0}).fillna(0).astype(int)

# === Save ===
if not df.empty:
    most_recent_flow_date = df["date"].max().strftime("%Y-%m-%d")
    output_path = rf"C:\Users\Steve\OneDrive\Desktop\Trading Edge Flow\0. Master_Flow\Master_Flow_Up_to_{most_recent_flow_date}.csv"
    df.to_csv(output_path, index=False)
    print(f"\n✅ Done. Scraped {len(df)} rows and saved to '{output_path}' with enriched features.")
else:
    print("\n⚠️ No flow data found. File not saved.")
