# api/providers/yfinance_provider.py
from __future__ import annotations
from typing import Dict, List
from datetime import datetime, timezone

import yfinance as yf
import pandas as pd

from .base import Provider, Quote, Bar, Interval, Range

# Map our contract intervals/ranges to yfinance
_YF_INTERVAL = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "60m", "1d": "1d"}
_YF_RANGE    = {"1d":"1d","5d":"5d","1m":"1mo","3m":"3mo","6m":"6mo","1y":"1y","2y":"2y","5y":"5y","max":"max"}

_EXPECTED = {"open", "high", "low", "close", "volume"}


# ---------- helpers ----------

def _pick_level_with_ohlc(mi_cols: pd.MultiIndex) -> int | None:
    """Return the level index whose values include open/high/low/close/volume."""
    for lvl in range(mi_cols.nlevels):
        values = {str(v).strip().lower() for v in mi_cols.get_level_values(lvl)}
        if _EXPECTED & values:
            return lvl
    return None


def _dedupe_keep_preferred(df: pd.DataFrame) -> pd.DataFrame:
    """
    If duplicate column names exist after normalization (e.g., two 'Close'),
    keep the last occurrence. This makes row['Close'] a scalar.
    """
    if not isinstance(df.columns, pd.Index):
        return df
    dup_mask = df.columns.duplicated(keep="last")
    if dup_mask.any():
        df = df.loc[:, ~dup_mask]
    return df


def _flatten_and_normalize(df: pd.DataFrame | None) -> pd.DataFrame:
    """
    Normalize into exactly ['Open','High','Low','Close'] (+ optional 'Volume').
    Handles MultiIndex rows & columns, duplicate names, 'Adj ' prefixes, etc.
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()

    # If row index is MultiIndex, keep inner-most level
    if isinstance(df.index, pd.MultiIndex):
        try:
            df = df.droplevel(list(range(df.index.nlevels - 1)), axis=0)
        except Exception:
            pass

    # Columns: resolve MultiIndex to a single level that actually holds OHLCV words
    if isinstance(df.columns, pd.MultiIndex):
        lvl = _pick_level_with_ohlc(df.columns)
        if lvl is not None:
            df.columns = [str(t[lvl]) for t in df.columns]
        else:
            # Fallback: take the last element of each tuple
            df.columns = [str(t[-1]) for t in df.columns]
    else:
        # Ensure string column names
        df.columns = [str(c) for c in df.columns]

    # Normalize names (tolerate 'Adj Open', weird spaces/casing)
    rename_map: dict = {}
    for c in df.columns:
        raw = str(c).strip()
        low = raw.lower()
        if low.startswith("adj "):
            low = low[4:]
        if low in _EXPECTED:
            rename_map[c] = low.capitalize()
    if rename_map:
        df = df.rename(columns=rename_map)

    # Drop duplicate columns after rename (keep last wins)
    df = _dedupe_keep_preferred(df)

    needed = ("Open", "High", "Low", "Close")
    if not all(n in df.columns for n in needed):
        return pd.DataFrame()

    # Coerce to numeric and drop rows missing any OHLC
    num_cols = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=list(needed))

    return df


def _bars_from_df(df: pd.DataFrame) -> List[Bar]:
    bars: List[Bar] = []
    for idx, row in df.iterrows():
        ts = pd.Timestamp(idx)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        # By now row['Close'] etc. are scalars (we deduped columns)
        bars.append(
            Bar(
                t=ts.isoformat(),
                o=round(float(row["Open"]),  4),
                h=round(float(row["High"]),  4),
                l=round(float(row["Low"]),   4),
                c=round(float(row["Close"]), 4),
                v=int(row["Volume"]) if "Volume" in df.columns and not pd.isna(row.get("Volume")) else None,
            )
        )
    bars.sort(key=lambda b: b["t"])  # oldest → newest
    return bars


def _safe_download(symbol: str, interval: str, period: str, group_by: str) -> pd.DataFrame:
    """Try yf.download with given group_by ('column' or 'ticker'), normalize or return empty."""
    try:
        df = yf.download(
            tickers=symbol,
            interval=interval,
            period=period,
            auto_adjust=False,
            prepost=False,
            progress=False,
            threads=False,     # more predictable on Windows
            group_by=group_by, # "column" or "ticker"
        )
    except Exception:
        df = None
    return _flatten_and_normalize(df)


def _safe_history(symbol: str, interval: str, period: str) -> pd.DataFrame:
    """
    Fallback to Ticker.history; if SciPy is required internally and missing,
    yfinance throws — we swallow and return empty.
    """
    try:
        tkr = yf.Ticker(symbol)
        df = tkr.history(
            period=period,
            interval=interval,
            auto_adjust=False,
            actions=False,
            prepost=False,
            repair=True,
        )
    except Exception:
        df = None
    return _flatten_and_normalize(df)


def _fallback_periods(interval: str, requested: str) -> List[str]:
    """Prioritized period candidates honoring Yahoo limits (e.g., 1m <= ~7d).”
    """
    if interval == "1m":
        order = [requested, "7d", "5d", "1d"]
    elif interval in ("5m", "15m", "60m"):
        order = [requested, "5d", "1mo", "3mo"]
    elif interval == "1d":
        order = [requested, "2y", "5y", "max", "6mo", "3mo", "1mo"]
    else:
        order = [requested, "1y", "5y", "max"]
    seen, out = set(), []
    for p in order:
        if p not in seen:
            out.append(p); seen.add(p)
    return out


# ---------- provider ----------

class YFinanceProvider(Provider):
    name = "YFinance"

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        if not symbols:
            return {}

        tickers = yf.Tickers(" ".join(symbols))
        now_iso = datetime.now(timezone.utc).isoformat()
        out: Dict[str, Quote] = {}

        for sym in symbols:
            try:
                info = tickers.tickers.get(sym)
            except Exception:
                info = None

            last_price = None
            prev_close = None
            try:
                hist = info.history(period="2d", interval="1d")
                if isinstance(hist, pd.DataFrame) and len(hist) > 0:
                    last_price = float(hist["Close"].iloc[-1])
                    if len(hist) > 1:
                        prev_close = float(hist["Close"].iloc[-2])
            except Exception:
                pass

            if last_price is None:
                continue

            if prev_close is None or prev_close == 0:
                change = 0.0
                change_pct = 0.0
            else:
                change = round(last_price - prev_close, 4)
                change_pct = round((change / prev_close) * 100.0, 4)

            out[sym] = Quote(
                symbol=sym,
                price=round(last_price, 4),
                change=round(change, 4),
                changePct=round(change_pct, 4),
                ts=now_iso,
            )

        return out

    def get_ohlc(self, symbol: str, interval: Interval, range_: Range) -> List[Bar]:
        yf_interval  = _YF_INTERVAL[interval]
        yf_requested = _YF_RANGE[range_]

        # Try requested, then fallbacks
        for period in _fallback_periods(yf_interval, yf_requested):
            # 1) column-grouped (ideal shape)
            df = _safe_download(symbol, yf_interval, period, group_by="column")
            if len(df) > 0:
                return _bars_from_df(df)

            # 2) ticker-grouped (the “Price / Ticker / Date” shape you saw)
            df = _safe_download(symbol, yf_interval, period, group_by="ticker")
            if len(df) > 0:
                return _bars_from_df(df)

            # 3) per-ticker history (ok to be empty if SciPy is missing)
            df = _safe_history(symbol, yf_interval, period)
            if len(df) > 0:
                return _bars_from_df(df)

        # Nothing worked -> router will fall back to Mock
        return []
