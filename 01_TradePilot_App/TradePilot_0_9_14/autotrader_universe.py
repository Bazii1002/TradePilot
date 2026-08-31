from __future__ import annotations

"""Small curated research universe for TradePilot 0.9.10.

The list is intentionally limited so a first local scan stays understandable and
reasonably quick. It can be expanded later to indices such as S&P 500/Nasdaq-100.
"""

CORE_30 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AVGO", "CRM", "ORCL", "ADBE",
    "JPM", "BAC", "WFC", "GS", "MS", "SCHW", "BLK",
    "XOM", "CVX", "COP", "SLB", "HAL", "BKR",
    "JNJ", "MRK", "LLY", "PFE", "KO", "COST", "WMT",
]


def universe_symbols(source: str, watchlist: dict[str, dict] | None = None) -> list[str]:
    source = str(source or "watchlist").lower()
    if source == "core30":
        return list(CORE_30)
    if source == "combined":
        merged = list((watchlist or {}).keys()) + CORE_30
        return sorted(set(str(x).upper() for x in merged if x))
    return sorted(set(str(x).upper() for x in (watchlist or {}).keys() if x))
