# api/providers/mock_provider.py
from __future__ import annotations
from typing import Dict, List
from datetime import datetime, timezone, timedelta
import math as _math
import random

from .base import Provider, Quote, Bar, Interval, Range

class MockProvider(Provider):
    name = "MockProvider"

    def __init__(self) -> None:
        pass

    def _rng(self, seed_text: str) -> random.Random:
        return random.Random(hash(seed_text) & 0xFFFFFFFF)

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        now = datetime.now(timezone.utc).isoformat()
        out: Dict[str, Quote] = {}
        for sym in symbols:
            r = self._rng(f"quote:{sym}")
            base = 50 + (abs(hash(sym)) % 400) * 0.5   # 50 .. ~250
            drift = (r.random() - 0.5) * 2.0           # -1..+1
            price = round(base * (1 + drift * 0.01), 2)
            changePct = round(drift, 2)                # pretend drift is %
            change = round(price * changePct / 100.0, 2)
            out[sym] = Quote(
                symbol=sym,
                price=price,
                change=change,
                changePct=changePct,
                ts=now,
            )
        return out

    def get_ohlc(self, symbol: str, interval: Interval, range_: Range) -> List[Bar]:
        step_min = {"1m":1, "5m":5, "15m":15, "1h":60, "1d":1440}[interval]
        range_days = {
            "1d":1, "5d":5, "1m":30, "3m":90, "6m":180,
            "1y":365, "2y":730, "5y":1825, "max":365
        }[range_]
        max_bars = min((range_days*1440)//step_min, 1200)

        r = self._rng(f"ohlc:{symbol}")
        base = 50 + (abs(hash(symbol)) % 400) * 0.5

        bars: List[Bar] = []
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        start = now - timedelta(minutes=step_min * max_bars)
        price = base
        for i in range(max_bars):
            t = start + timedelta(minutes=i*step_min)
            angle = (i / max(10, max_bars)) * 2 * _math.pi
            drift = _math.sin(angle) * 0.015 * base
            noise = (r.random() - 0.5) * 0.004 * base
            close = max(1.0, base + drift + noise)
            high = close * (1 + abs(r.random()) * 0.002)
            low  = close * (1 - abs(r.random()) * 0.002)
            open_ = (close + price) / 2
            vol = int(1_000 + r.random() * 9_000)
            price = close
            bars.append(Bar(
                t=t.isoformat(),
                o=round(open_, 2),
                h=round(high, 2),
                l=round(low, 2),
                c=round(close, 2),
                v=vol,
            ))
        return bars
