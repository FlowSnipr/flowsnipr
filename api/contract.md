# Flow Snipr Data Contract (v0)

All providers normalize to the following JSON shapes.

---

## Quote

```json
{
  "symbol": "AAPL",
  "price": 223.15,
  "change": 1.52,
  "changePct": 0.69,
  "ts": "2025-09-01T09:00:00Z"
}
```

- `changePct` is a percentage (e.g., 0.69 = +0.69%).
- `ts` in ISO-8601 UTC.

---

## OHLC Bar

```json
{
  "t": "2025-08-29T14:30:00Z",
  "o": 221.1,
  "h": 222.3,
  "l": 220.8,
  "c": 221.9,
  "v": 123456
}
```

- Bars ordered oldest → newest.
- `t` is bar start, ISO-8601 UTC.

---

## Provider Interface

```python
class Provider(Protocol):
    name: str
    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]: ...
    def get_ohlc(self, symbol: str, interval: str, range: str) -> list[Bar]: ...
```

---

## Notes

- Deterministic mock data is used in dev for repeatability.
- Real providers (e.g., YFinance, AlphaVantage) must return the same shapes.
