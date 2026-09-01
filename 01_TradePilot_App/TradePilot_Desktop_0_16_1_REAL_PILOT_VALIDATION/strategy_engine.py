from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
import math

import pandas as pd


STRATEGIES = {
    1: {
        "name": "FAST", "scan_seconds": 60, "period": "5d", "interval": "5m",
        "fast": 9, "slow": 21, "rsi": 14, "momentum": 6, "atr": 14,
        "buy_score": 74.0, "watch_score": 62.0, "exit_score": 48.0,
        "min_bars": 45, "min_hold_cycles": 2, "stop_pct": -1.2, "take_pct": 2.0,
        "volatility_target": 0.9,
    },
    2: {
        "name": "DAY", "scan_seconds": 120, "period": "1mo", "interval": "15m",
        "fast": 12, "slow": 36, "rsi": 14, "momentum": 8, "atr": 14,
        "buy_score": 72.0, "watch_score": 60.0, "exit_score": 46.0,
        "min_bars": 55, "min_hold_cycles": 3, "stop_pct": -2.0, "take_pct": 4.0,
        "volatility_target": 1.5,
    },
    3: {
        "name": "WEEK", "scan_seconds": 300, "period": "3mo", "interval": "1h",
        "fast": 20, "slow": 50, "rsi": 14, "momentum": 12, "atr": 14,
        "buy_score": 70.0, "watch_score": 58.0, "exit_score": 44.0,
        "min_bars": 75, "min_hold_cycles": 3, "stop_pct": -5.0, "take_pct": 10.0,
        "volatility_target": 2.4,
    },
    4: {
        "name": "INVEST", "scan_seconds": 900, "period": "2y", "interval": "1d",
        "fast": 50, "slow": 200, "rsi": 14, "momentum": 20, "atr": 14,
        "buy_score": 68.0, "watch_score": 56.0, "exit_score": 42.0,
        "min_bars": 230, "min_hold_cycles": 2, "stop_pct": -12.0, "take_pct": 25.0,
        "volatility_target": 3.2,
    },
}

DEFAULT_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META",
    "AMD", "TSLA", "ORCL", "ADBE", "AVGO", "NFLX",
]


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, math.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.fillna(50.0)


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        (df["High"] - df["Low"]).abs(),
        (df["High"] - prev_close).abs(),
        (df["Low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    df = frame.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # Ticker.history normally is flat; this keeps download-style frames usable too.
        if len(df.columns.levels) >= 2:
            level0 = set(map(str, df.columns.get_level_values(0)))
            level1 = set(map(str, df.columns.get_level_values(1)))
            wanted = {"Open", "High", "Low", "Close", "Volume"}
            if wanted.issubset(level0):
                df.columns = df.columns.get_level_values(0)
            elif wanted.issubset(level1):
                df.columns = df.columns.get_level_values(1)
    rename = {str(c).lower(): c for c in df.columns}
    mapping = {}
    for name in ["Open", "High", "Low", "Close", "Volume"]:
        original = rename.get(name.lower())
        if original is not None:
            mapping[original] = name
    df = df.rename(columns=mapping)
    required = ["High", "Low", "Close", "Volume"]
    if any(c not in df.columns for c in required):
        return pd.DataFrame()
    df = df[required].copy()
    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["High", "Low", "Close"]).sort_index()


@dataclass
class AnalysisResult:
    symbol: str
    strategy: str
    score: float
    signal: str
    price: float | None
    reason: str
    rsi: float | None = None
    momentum_pct: float | None = None
    volume_ratio: float | None = None
    atr_pct: float | None = None
    timestamp: str = ""
    error: str = ""

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "strategy": self.strategy,
            "score": round(float(self.score), 1),
            "signal": self.signal,
            "price": None if self.price is None else round(float(self.price), 4),
            "reason": self.reason,
            "rsi": None if self.rsi is None else round(float(self.rsi), 1),
            "momentum_pct": None if self.momentum_pct is None else round(float(self.momentum_pct), 2),
            "volume_ratio": None if self.volume_ratio is None else round(float(self.volume_ratio), 2),
            "atr_pct": None if self.atr_pct is None else round(float(self.atr_pct), 2),
            "timestamp": self.timestamp,
            "error": self.error,
        }


class StrategyAnalyzer:
    """Deterministic technical signal engine. No random scores and no broker POSTs."""

    def analyze_frame(self, symbol: str, frame: pd.DataFrame, level: int) -> AnalysisResult:
        cfg = STRATEGIES[int(level)]
        name = cfg["name"]
        df = _normalize_frame(frame)
        if len(df) < int(cfg["min_bars"]):
            return AnalysisResult(symbol, name, 0.0, "NO_DATA", None,
                                  f"Zu wenig Kursdaten ({len(df)}/{cfg['min_bars']})", error="insufficient_bars")

        close = df["Close"]
        fast = close.rolling(int(cfg["fast"])).mean()
        slow = close.rolling(int(cfg["slow"])).mean()
        rsi = _rsi(close, int(cfg["rsi"]))
        momentum = close.pct_change(int(cfg["momentum"])) * 100.0
        atr = _atr(df, int(cfg["atr"]))
        volume_avg = df["Volume"].rolling(20).mean()

        price = float(close.iloc[-1])
        fast_v = float(fast.iloc[-1]) if pd.notna(fast.iloc[-1]) else price
        slow_v = float(slow.iloc[-1]) if pd.notna(slow.iloc[-1]) else price
        rsi_v = float(rsi.iloc[-1])
        mom_v = float(momentum.iloc[-1]) if pd.notna(momentum.iloc[-1]) else 0.0
        atr_v = float(atr.iloc[-1]) if pd.notna(atr.iloc[-1]) else 0.0
        atr_pct = (atr_v / price * 100.0) if price > 0 else 0.0
        vol_avg_v = float(volume_avg.iloc[-1]) if pd.notna(volume_avg.iloc[-1]) else 0.0
        vol_v = float(df["Volume"].iloc[-1]) if pd.notna(df["Volume"].iloc[-1]) else 0.0
        volume_ratio = (vol_v / vol_avg_v) if vol_avg_v > 0 else 1.0

        # Trend 0..100: strongest only when price > fast > slow.
        if price > fast_v > slow_v:
            trend_score = 100.0
        elif price > slow_v and fast_v > slow_v:
            trend_score = 82.0
        elif price > slow_v:
            trend_score = 65.0
        elif fast_v > slow_v:
            trend_score = 52.0
        elif price > fast_v:
            trend_score = 38.0
        else:
            trend_score = 18.0

        # Momentum maps roughly -5..+5% to 0..100, with strategy-independent clipping.
        momentum_score = _clip(50.0 + mom_v * 10.0)

        # RSI favours healthy positive momentum, penalises overbought/weak conditions.
        if 52 <= rsi_v <= 68:
            rsi_score = 100.0 - abs(60.0 - rsi_v) * 2.5
        elif 45 <= rsi_v < 52:
            rsi_score = 55.0 + (rsi_v - 45.0) * 4.0
        elif 68 < rsi_v <= 75:
            rsi_score = 80.0 - (rsi_v - 68.0) * 6.0
        elif rsi_v < 45:
            rsi_score = _clip(45.0 - (45.0 - rsi_v) * 2.0)
        else:
            rsi_score = _clip(38.0 - (rsi_v - 75.0) * 3.0)

        volume_score = _clip(35.0 + volume_ratio * 35.0)
        target = float(cfg["volatility_target"])
        if atr_pct <= target:
            volatility_score = 85.0 + 15.0 * (atr_pct / max(target, 0.01))
        else:
            volatility_score = _clip(100.0 - (atr_pct - target) * 18.0)

        score = (
            trend_score * 0.35 +
            momentum_score * 0.25 +
            rsi_score * 0.15 +
            volume_score * 0.15 +
            volatility_score * 0.10
        )
        score = _clip(score)

        trend_confirmed = price > fast_v > slow_v
        not_overbought = rsi_v < 75.0
        if score >= cfg["buy_score"] and trend_confirmed and not_overbought:
            signal = "BUY"
        elif score >= cfg["watch_score"]:
            signal = "WATCH"
        else:
            signal = "WAIT"

        trend_text = "Trend +" if trend_confirmed else ("Trend gemischt" if price > slow_v else "Trend -")
        reason = f"{trend_text} · RSI {rsi_v:.0f} · Mom {mom_v:+.1f}% · Vol {volume_ratio:.1f}x"
        return AnalysisResult(
            symbol=symbol, strategy=name, score=score, signal=signal, price=price,
            reason=reason, rsi=rsi_v, momentum_pct=mom_v, volume_ratio=volume_ratio,
            atr_pct=atr_pct, timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds")
        )


class YahooMarketDataProvider:
    def history(self, symbol: str, *, period: str, interval: str) -> pd.DataFrame:
        # Lazy import lets SELFTEST/offline tests run without network dependencies.
        import yfinance as yf
        return yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True, actions=False)


class ProductionStrategyEngine:
    def __init__(self, provider=None):
        self.provider = provider or YahooMarketDataProvider()
        self.analyzer = StrategyAnalyzer()

    def scan_universe(self, level: int, symbols: Iterable[str] = DEFAULT_UNIVERSE) -> list[dict]:
        cfg = STRATEGIES[int(level)]
        rows: list[dict] = []
        for raw_symbol in symbols:
            symbol = str(raw_symbol).upper().strip()
            if not symbol:
                continue
            try:
                frame = self.provider.history(symbol, period=cfg["period"], interval=cfg["interval"])
                result = self.analyzer.analyze_frame(symbol, frame, level)
            except Exception as exc:
                result = AnalysisResult(symbol, cfg["name"], 0.0, "NO_DATA", None,
                                        "Marktdaten nicht verfügbar", error=str(exc)[:180])
            rows.append(result.as_dict())
        rows.sort(key=lambda r: float(r.get("score") or 0.0), reverse=True)
        return rows

    @staticmethod
    def exit_decision(position: dict, row: dict | None) -> tuple[bool, str, float | None]:
        level = int(position.get("level", 2))
        cfg = STRATEGIES[level]
        if not row or row.get("price") in (None, 0):
            return False, "HOLD · keine frischen Kursdaten", None
        price = float(row["price"])
        entry = float(position.get("entry") or price)
        pnl_pct = ((price / entry) - 1.0) * 100.0 if entry > 0 else 0.0
        age = int(position.get("age", 0))
        if pnl_pct <= float(cfg["stop_pct"]):
            return True, f"STOP {pnl_pct:+.2f}%", pnl_pct
        if pnl_pct >= float(cfg["take_pct"]):
            return True, f"TAKE PROFIT {pnl_pct:+.2f}%", pnl_pct
        if age >= int(cfg["min_hold_cycles"]) and float(row.get("score") or 0.0) <= float(cfg["exit_score"]):
            return True, f"SIGNAL EXIT · Score {float(row.get('score') or 0.0):.1f}", pnl_pct
        return False, f"HOLD {pnl_pct:+.2f}%", pnl_pct
