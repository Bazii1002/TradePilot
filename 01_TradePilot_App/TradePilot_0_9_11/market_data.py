from __future__ import annotations

"""Lightweight market-price polling for TradePilot.

This module intentionally fetches only recent price data. It does not re-run the
fundamental analysis engine and it does not claim exchange-grade real-time data.
Yahoo Finance/yfinance can be delayed or temporarily unavailable.
"""

import math
from datetime import datetime, timezone

from exchange_status import is_exchange_open

import yfinance as yf


def _finite(value):
    try:
        out = float(value)
        return out if math.isfinite(out) and out > 0 else None
    except Exception:
        return None


def _timestamp_info(index_value) -> tuple[str | None, float | None]:
    try:
        dt = index_value.to_pydatetime() if hasattr(index_value, "to_pydatetime") else index_value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        age = max(0.0, (datetime.now(timezone.utc) - dt_utc).total_seconds())
        return dt_utc.isoformat(timespec="seconds"), age
    except Exception:
        return None, None


def us_regular_session_likely_open() -> bool:
    """Return TradePilot's local NYSE regular-session status.

    The exchange-status module includes weekends and major full-day holidays.
    Fresh provider timestamps remain a second, mandatory execution condition.
    """
    return is_exchange_open("NYSE")


def get_latest_quote(symbol: str) -> dict:
    """Return the latest usable quote for one ticker.

    Preference order:
      1. latest 1-minute close from the current/recent trading day
      2. latest daily close from the last 5 trading days

    ``fresh`` is deliberately conservative. Only a quote less than five minutes
    old is considered fresh enough for automated price-based exits.
    """
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        raise ValueError("EMPTY_SYMBOL")

    ticker = yf.Ticker(symbol)
    attempts = [
        ("1m", {"period": "1d", "interval": "1m", "auto_adjust": False, "prepost": False}),
        ("1d", {"period": "5d", "interval": "1d", "auto_adjust": False, "prepost": False}),
    ]

    errors: list[str] = []
    for source_interval, kwargs in attempts:
        try:
            hist = ticker.history(**kwargs)
            if hist is None or hist.empty or "Close" not in hist:
                errors.append(f"{source_interval}:empty")
                continue
            close = hist["Close"].dropna()
            if close.empty:
                errors.append(f"{source_interval}:no_close")
                continue
            price = _finite(close.iloc[-1])
            if price is None:
                errors.append(f"{source_interval}:invalid_price")
                continue
            quote_time, age_seconds = _timestamp_info(close.index[-1])
            fresh = bool(age_seconds is not None and age_seconds <= 300 and source_interval == "1m")
            return {
                "symbol": symbol,
                "price": price,
                "quote_time": quote_time,
                "age_seconds": age_seconds,
                "fresh": fresh,
                "session_open": us_regular_session_likely_open(),
                "interval": source_interval,
                "provider": "Yahoo Finance / yfinance",
            }
        except Exception as exc:
            errors.append(f"{source_interval}:{exc}")

    raise RuntimeError("; ".join(errors) if errors else "NO_QUOTE")
