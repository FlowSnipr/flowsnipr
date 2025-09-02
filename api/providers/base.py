# api/providers/base.py
from __future__ import annotations
from typing import TypedDict, Protocol, List, Dict, Literal

class Quote(TypedDict):
    symbol: str
    price: float
    change: float        # absolute change
    changePct: float     # % change (e.g., 1.23 for +1.23%)
    ts: str              # ISO-8601 UTC timestamp

class Bar(TypedDict):
    t: str               # ISO-8601 UTC timestamp (bar start)
    o: float
    h: float
    l: float
    c: float
    v: int | None        # optional volume

Interval = Literal["1m", "5m", "15m", "1h", "1d"]
Range = Literal["1d", "5d", "1m", "3m", "6m", "1y", "2y", "5y", "max"]

class Provider(Protocol):
    name: str

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Return a dict keyed by symbol with normalized Quote."""
        ...

    def get_ohlc(self, symbol: str, interval: Interval, range_: Range) -> List[Bar]:
        """Return a list of normalized OHLC bars, oldest -> newest."""
        ...
