from __future__ import annotations

"""TradePilot 0.9.10 market-regime filter.

This module is deliberately separate from the frozen stock-analysis engine.
It provides additional context for the AutoTrader only.
"""

from datetime import datetime, timezone


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def get_market_regime(symbol: str = "SPY") -> dict:
    result = {
        "symbol": symbol,
        "regime": "UNKNOWN",
        "score": 50,
        "price": None,
        "ma50": None,
        "ma200": None,
        "momentum_3m_pct": None,
        "drawdown_pct": None,
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "error": None,
    }
    try:
        import yfinance as yf

        hist = yf.download(symbol, period="1y", interval="1d", auto_adjust=True,
                           progress=False, threads=False)
        if hist is None or hist.empty or "Close" not in hist:
            raise ValueError("NO_MARKET_DATA")
        close = hist["Close"].dropna()
        # yfinance can return a one-column DataFrame for some versions.
        if hasattr(close, "columns"):
            if len(close.columns) < 1:
                raise ValueError("NO_MARKET_DATA")
            close = close.iloc[:, 0]
        if len(close) < 60:
            raise ValueError("NOT_ENOUGH_MARKET_DATA")

        price = _f(close.iloc[-1])
        ma50 = _f(close.tail(50).mean())
        ma200 = _f(close.tail(200).mean()) if len(close) >= 200 else _f(close.mean())
        ref_3m = _f(close.iloc[-64]) if len(close) >= 64 else _f(close.iloc[0])
        mom3 = ((price / ref_3m) - 1.0) * 100.0 if ref_3m > 0 else 0.0
        high = _f(close.max())
        drawdown = ((price / high) - 1.0) * 100.0 if high > 0 else 0.0

        score = 50
        score += 18 if price >= ma200 else -22
        score += 12 if price >= ma50 else -12
        if mom3 >= 8:
            score += 12
        elif mom3 > 0:
            score += 6
        elif mom3 <= -12:
            score -= 14
        elif mom3 < 0:
            score -= 6
        if drawdown <= -20:
            score -= 12
        elif drawdown <= -10:
            score -= 6
        score = max(0, min(100, score))

        if score >= 68 and price >= ma200:
            regime = "BULLISH"
        elif score <= 38 or (price < ma200 and price < ma50 and mom3 < 0):
            regime = "BEARISH"
        else:
            regime = "NEUTRAL"

        result.update({
            "regime": regime,
            "score": round(score),
            "price": price,
            "ma50": ma50,
            "ma200": ma200,
            "momentum_3m_pct": mom3,
            "drawdown_pct": drawdown,
        })
    except Exception as exc:
        result["error"] = str(exc)
    return result


def market_profile_filter(regime: dict | None, profile: str, confidence: int = 0) -> dict:
    """Translate market regime into an AutoTrader guard.

    UNKNOWN never upgrades a trade. Defensive/balanced profiles wait when the
    market context is unavailable; offensive/speculative profiles get a warning.
    """
    r = (regime or {}).get("regime", "UNKNOWN")
    score = int((regime or {}).get("score", 50) or 50)
    confidence = int(confidence or 0)
    block = False
    downgrade = False
    warnings: list[str] = []

    if r == "UNKNOWN":
        warnings.append("MARKET_DATA_UNKNOWN")
        if profile in {"defensive", "balanced"}:
            downgrade = True
    elif r == "BEARISH":
        warnings.append("MARKET_BEARISH")
        if profile == "defensive":
            block = True
        elif profile == "balanced":
            downgrade = True
        elif profile == "offensive" and confidence < 85:
            downgrade = True
    elif r == "NEUTRAL":
        if profile == "defensive" and confidence < 85:
            downgrade = True
            warnings.append("MARKET_NEUTRAL_NEEDS_CONFIRMATION")
    return {"block": block, "downgrade": downgrade, "warnings": warnings, "regime": r, "score": score}
