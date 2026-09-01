from __future__ import annotations

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from strategy_engine import STRATEGIES, StrategyAnalyzer, _normalize_frame

FAST_BATCH_SIZE = 25
FAST_WORKERS = 8
FAST_CANDIDATES = 50
DEEP_BATCH_SIZE = 25

FULL_SCAN_TTL = {
    1: 300,   # FAST: broad universe max every 5 min
    2: 600,   # DAY: every 10 min
    3: 1800,  # WEEK: every 30 min
    4: 3600,  # INVEST: every hour
}


def _chunks(seq: list[str], size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _extract_symbol_frame(downloaded: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if downloaded is None or downloaded.empty:
        return pd.DataFrame()
    df = downloaded
    if isinstance(df.columns, pd.MultiIndex):
        l0 = list(map(str, df.columns.get_level_values(0)))
        l1 = list(map(str, df.columns.get_level_values(1)))
        try:
            if symbol in l0:
                return _normalize_frame(df[symbol])
            if symbol in l1:
                return _normalize_frame(df.xs(symbol, axis=1, level=1))
        except Exception:
            return pd.DataFrame()
    return _normalize_frame(df)


def fast_score_frame(frame: pd.DataFrame, level: int) -> dict | None:
    df = _normalize_frame(frame)
    if len(df) < 25:
        return None
    close = df["Close"]
    vol = df["Volume"].fillna(0.0)
    price = float(close.iloc[-1])
    if not math.isfinite(price) or price <= 0:
        return None
    ma5 = float(close.tail(5).mean())
    ma20 = float(close.tail(20).mean())
    mom5 = (price / float(close.iloc[-6]) - 1.0) * 100.0 if len(close) >= 6 and float(close.iloc[-6]) else 0.0
    mom20 = (price / float(close.iloc[-21]) - 1.0) * 100.0 if len(close) >= 21 and float(close.iloc[-21]) else 0.0
    avg_vol = float(vol.tail(20).mean())
    vr = float(vol.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0
    dollar_vol = price * avg_vol

    trend = 100.0 if price > ma5 > ma20 else (78.0 if price > ma20 else (52.0 if ma5 > ma20 else 20.0))
    momentum = max(0.0, min(100.0, 50.0 + mom5 * 8.0 + mom20 * 2.0))
    volume = max(0.0, min(100.0, 30.0 + vr * 35.0))
    # $1m -> ~50, $10m -> ~70, $100m -> ~90; filters illiquid tails without a hard cliff.
    liquidity = max(0.0, min(100.0, 30.0 + max(0.0, math.log10(max(dollar_vol, 1.0)) - 5.0) * 20.0))

    weights = {
        1: (0.20, 0.35, 0.25, 0.20),
        2: (0.30, 0.25, 0.25, 0.20),
        3: (0.40, 0.30, 0.15, 0.15),
        4: (0.55, 0.25, 0.05, 0.15),
    }[int(level)]
    score = trend * weights[0] + momentum * weights[1] + volume * weights[2] + liquidity * weights[3]
    return {
        "score": round(score, 2), "price": price, "trend": round(trend, 1),
        "momentum": round(momentum, 1), "volume": round(volume, 1),
        "liquidity": round(liquidity, 1), "mom5": round(mom5, 2), "mom20": round(mom20, 2),
        "volume_ratio": round(vr, 2), "dollar_volume": round(dollar_vol, 2),
    }


class ThousandStockFastScanner:
    def __init__(self, app_dir: Path, analyzer: StrategyAnalyzer | None = None):
        self.app_dir = Path(app_dir)
        self.cache_dir = self.app_dir / "data" / "scanner_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.analyzer = analyzer or StrategyAnalyzer()
        self.last_metrics = {
            "universe": 0, "scanned": 0, "candidates": 0, "deep": 0,
            "signals": 0, "duration": 0.0, "cache": "MISS", "errors": 0,
        }

    def _cache_file(self, level: int) -> Path:
        return self.cache_dir / f"fast_candidates_level_{int(level)}.json"

    def _load_candidate_cache(self, level: int) -> list[dict] | None:
        p = self._cache_file(level)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            age = time.time() - float(data.get("saved_ts", 0))
            if age <= FULL_SCAN_TTL[int(level)] and isinstance(data.get("rows"), list):
                return data["rows"]
        except Exception:
            pass
        return None

    def _save_candidate_cache(self, level: int, rows: list[dict]):
        p = self._cache_file(level)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps({"saved_ts": time.time(), "rows": rows}, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)

    def _download_batch(self, symbols: list[str], period: str, interval: str) -> dict[str, pd.DataFrame]:
        import yfinance as yf
        if not symbols:
            return {}
        data = yf.download(
            tickers=symbols, period=period, interval=interval, group_by="ticker",
            auto_adjust=True, actions=False, progress=False, threads=True,
        )
        return {s: _extract_symbol_frame(data, s) for s in symbols}

    def _download_many(self, symbols: list[str], period: str, interval: str, batch_size: int, workers: int) -> tuple[dict[str, pd.DataFrame], int]:
        frames: dict[str, pd.DataFrame] = {}
        errors = 0
        batches = list(_chunks(symbols, batch_size))
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futs = {pool.submit(self._download_batch, batch, period, interval): batch for batch in batches}
            for fut in as_completed(futs):
                batch = futs[fut]
                try:
                    result = fut.result()
                    for sym in batch:
                        frame = result.get(sym, pd.DataFrame())
                        if frame is None or frame.empty:
                            errors += 1
                        else:
                            frames[sym] = frame
                except Exception:
                    errors += len(batch)
        return frames, errors

    def rank_frames(self, level: int, symbols: Iterable[str], frames: dict[str, pd.DataFrame], limit: int = FAST_CANDIDATES) -> list[dict]:
        rows = []
        for sym in symbols:
            frame = frames.get(sym)
            if frame is None or frame.empty:
                continue
            ranked = fast_score_frame(frame, level)
            if ranked:
                rows.append({"symbol": sym, **ranked})
        rows.sort(key=lambda r: float(r["score"]), reverse=True)
        return rows[:limit]

    def broad_scan(self, level: int, symbols: list[str], force: bool = False) -> tuple[list[dict], dict]:
        started = time.perf_counter()
        cached = None if force else self._load_candidate_cache(level)
        if cached:
            metrics = {
                "universe": len(symbols), "scanned": len(symbols), "candidates": len(cached),
                "deep": 0, "signals": 0, "duration": round(time.perf_counter()-started, 2),
                "cache": "HIT", "errors": 0,
            }
            return cached, metrics
        frames, errors = self._download_many(symbols, "3mo", "1d", FAST_BATCH_SIZE, FAST_WORKERS)
        ranked = self.rank_frames(level, symbols, frames, FAST_CANDIDATES)
        self._save_candidate_cache(level, ranked)
        metrics = {
            "universe": len(symbols), "scanned": len(frames), "candidates": len(ranked),
            "deep": 0, "signals": 0, "duration": round(time.perf_counter()-started, 2),
            "cache": "MISS", "errors": errors,
        }
        return ranked, metrics

    def deep_scan(self, level: int, symbols: list[str]) -> tuple[list[dict], int]:
        cfg = STRATEGIES[int(level)]
        frames, errors = self._download_many(symbols, cfg["period"], cfg["interval"], DEEP_BATCH_SIZE, 4)
        rows = []
        for sym in symbols:
            frame = frames.get(sym)
            if frame is None or frame.empty:
                continue
            try:
                rows.append(self.analyzer.analyze_frame(sym, frame, level).as_dict())
            except Exception:
                errors += 1
        rows.sort(key=lambda r: float(r.get("score") or 0.0), reverse=True)
        return rows, errors

    def scan(self, level: int, symbols: list[str], held_symbols: Iterable[str] = (), force_full: bool = False) -> tuple[list[dict], dict]:
        started = time.perf_counter()
        candidates, metrics = self.broad_scan(level, symbols, force=force_full)
        deep_symbols = []
        seen = set()
        for sym in [r["symbol"] for r in candidates] + [str(s).upper() for s in held_symbols]:
            if sym and sym not in seen:
                seen.add(sym); deep_symbols.append(sym)
        rows, deep_errors = self.deep_scan(level, deep_symbols)
        metrics["deep"] = len(rows)
        metrics["signals"] = sum(1 for r in rows if r.get("signal") == "BUY")
        metrics["errors"] = int(metrics.get("errors", 0)) + int(deep_errors)
        metrics["duration"] = round(time.perf_counter() - started, 2)
        self.last_metrics = metrics
        return rows, metrics
