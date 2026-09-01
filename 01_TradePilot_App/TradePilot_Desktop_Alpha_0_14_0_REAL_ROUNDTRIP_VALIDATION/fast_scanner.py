from __future__ import annotations

import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

import pandas as pd

from strategy_engine import STRATEGIES, StrategyAnalyzer, _normalize_frame
from quality_gate import apply_quality_gate, MAX_ACTIONABLE_SIGNALS

# 0.13.5 scanner constants. The broad scan sees the full universe, but expensive
# strategy analysis is limited to the strongest candidates.
FAST_BATCH_SIZE = 25
FAST_WORKERS = 8
FAST_CANDIDATES = 50
DEEP_BATCH_SIZE = 25
DEEP_WORKERS = 4
FINALIST_LIMIT = 12
RETRY_BATCH_SIZE = 5
RETRY_WORKERS = 4
FAILS_BEFORE_QUARANTINE = 3
QUARANTINE_SECONDS = 7 * 24 * 3600

FULL_SCAN_TTL = {
    1: 300,   # FAST: broad universe max every 5 min
    2: 600,   # DAY: every 10 min
    3: 1800,  # WEEK: every 30 min
    4: 3600,  # INVEST: every hour
}

# yfinance can be extremely noisy for delisted/unavailable symbols. We still
# count every final failure in metrics and persist it in invalid_symbols.json.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


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


class ScannerFailureRegistry:
    """Persistent failure/quarantine registry.

    A symbol is NOT blacklisted after one network hiccup. Only repeated broad-scan
    failures trigger a temporary seven-day quarantine, after which it is tested again.
    """
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = {"symbols": {}}
        self._load()

    def _load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("symbols"), dict):
                self.data = raw
        except Exception:
            pass

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def is_quarantined(self, symbol: str, now: float | None = None) -> bool:
        now = time.time() if now is None else float(now)
        row = self.data.get("symbols", {}).get(str(symbol).upper(), {})
        until = float(row.get("quarantined_until", 0) or 0)
        if until > now:
            return True
        if until:
            # Quarantine expired: give the symbol a fresh chance instead of a permanent ban.
            row["quarantined_until"] = 0
            row["fail_count"] = max(0, int(row.get("fail_count", 0)) - 1)
            self._save()
        return False

    def record_success(self, symbol: str):
        key = str(symbol).upper()
        if key in self.data.get("symbols", {}):
            self.data["symbols"].pop(key, None)
            self._save()

    def record_failure(self, symbol: str, reason: str = "no_price_data"):
        key = str(symbol).upper()
        rows = self.data.setdefault("symbols", {})
        row = rows.setdefault(key, {})
        count = int(row.get("fail_count", 0)) + 1
        row.update({"fail_count": count, "last_failure": time.time(), "reason": str(reason)[:160]})
        if count >= FAILS_BEFORE_QUARANTINE:
            row["quarantined_until"] = time.time() + QUARANTINE_SECONDS
        self._save()

    def quarantined_count(self) -> int:
        return sum(1 for s in self.data.get("symbols", {}) if self.is_quarantined(s))


class ThousandStockFastScanner:
    def __init__(self, app_dir: Path, analyzer: StrategyAnalyzer | None = None):
        self.app_dir = Path(app_dir)
        self.cache_dir = self.app_dir / "data" / "scanner_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.failure_registry = ScannerFailureRegistry(self.app_dir / "data" / "invalid_symbols.json")
        self.analyzer = analyzer or StrategyAnalyzer()
        self.last_metrics = {
            "universe": 0, "scanned": 0, "candidates": 0, "deep": 0,
            "finalists": 0, "signals": 0, "raw_signals": 0, "actionable": 0,
            "duration": 0.0, "cache": "MISS", "errors": 0,
            "retried": 0, "quarantined": 0,
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

    def _download_batch(self, symbols: list[str], period: str, interval: str, timeout: int = 10) -> dict[str, pd.DataFrame]:
        import yfinance as yf
        if not symbols:
            return {}
        data = yf.download(
            tickers=symbols, period=period, interval=interval, group_by="ticker",
            auto_adjust=True, actions=False, progress=False, threads=True, timeout=timeout,
        )
        return {s: _extract_symbol_frame(data, s) for s in symbols}

    def _download_batches(self, symbols: list[str], period: str, interval: str, batch_size: int, workers: int, timeout: int = 10) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        batches = list(_chunks(symbols, batch_size))
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futs = {pool.submit(self._download_batch, batch, period, interval, timeout): batch for batch in batches}
            for fut in as_completed(futs):
                batch = futs[fut]
                try:
                    result = fut.result()
                except Exception:
                    result = {}
                for sym in batch:
                    frame = result.get(sym, pd.DataFrame())
                    if frame is not None and not frame.empty:
                        frames[sym] = frame
        return frames

    def _download_many(self, symbols: list[str], period: str, interval: str, batch_size: int, workers: int, *, broad: bool = False) -> tuple[dict[str, pd.DataFrame], list[str], int, int]:
        # Repeatedly invalid symbols are skipped temporarily; transient errors are retried once.
        skipped = [s for s in symbols if broad and self.failure_registry.is_quarantined(s)]
        eligible = [s for s in symbols if s not in set(skipped)]
        frames = self._download_batches(eligible, period, interval, batch_size, workers, timeout=10)
        missing = [s for s in eligible if s not in frames]
        retried = len(missing)
        if missing:
            retry_frames = self._download_batches(missing, period, interval, RETRY_BATCH_SIZE, RETRY_WORKERS, timeout=7)
            frames.update(retry_frames)
        final_missing = [s for s in eligible if s not in frames]
        if broad:
            for s in frames:
                self.failure_registry.record_success(s)
            for s in final_missing:
                self.failure_registry.record_failure(s)
        return frames, final_missing, retried, len(skipped)

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
                "deep": 0, "finalists": 0, "signals": 0, "raw_signals": 0, "actionable": 0,
                "duration": round(time.perf_counter()-started, 2), "cache": "HIT", "errors": 0,
                "retried": 0, "quarantined": self.failure_registry.quarantined_count(),
            }
            return cached, metrics
        frames, missing, retried, skipped = self._download_many(
            symbols, "3mo", "1d", FAST_BATCH_SIZE, FAST_WORKERS, broad=True
        )
        ranked = self.rank_frames(level, symbols, frames, FAST_CANDIDATES)
        self._save_candidate_cache(level, ranked)
        metrics = {
            "universe": len(symbols), "scanned": len(frames), "candidates": len(ranked),
            "deep": 0, "finalists": 0, "signals": 0, "raw_signals": 0, "actionable": 0,
            "duration": round(time.perf_counter()-started, 2), "cache": "MISS", "errors": len(missing),
            "retried": retried, "quarantined": skipped,
        }
        return ranked, metrics

    def deep_scan(self, level: int, symbols: list[str]) -> tuple[list[dict], int]:
        cfg = STRATEGIES[int(level)]
        frames, missing, _retried, _skipped = self._download_many(
            symbols, cfg["period"], cfg["interval"], DEEP_BATCH_SIZE, DEEP_WORKERS, broad=False
        )
        rows = []
        errors = len(missing)
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

    @staticmethod
    def mark_finalists(rows: list[dict], held_symbols: Iterable[str] = (), limit: int = FINALIST_LIMIT) -> tuple[list[dict], int]:
        held = {str(s).upper() for s in held_symbols if s}
        nonheld = [r for r in rows if str(r.get("symbol", "")).upper() not in held and r.get("signal") != "NO_DATA"]
        finalist_symbols = {r["symbol"] for r in nonheld[:max(0, int(limit))]}
        marked = []
        for r in rows:
            item = dict(r)
            item["is_finalist"] = item.get("symbol") in finalist_symbols
            item["is_held"] = str(item.get("symbol", "")).upper() in held
            marked.append(item)
        return marked, len(finalist_symbols)

    def scan(self, level: int, symbols: list[str], held_symbols: Iterable[str] = (), force_full: bool = False) -> tuple[list[dict], dict]:
        started = time.perf_counter()
        held_symbols = [str(s).upper() for s in held_symbols if s]
        candidates, metrics = self.broad_scan(level, symbols, force=force_full)
        deep_symbols = []
        seen = set()
        for sym in [r["symbol"] for r in candidates] + held_symbols:
            if sym and sym not in seen:
                seen.add(sym)
                deep_symbols.append(sym)
        rows, deep_errors = self.deep_scan(level, deep_symbols)
        rows, finalist_count = self.mark_finalists(rows, held_symbols, FINALIST_LIMIT)
        rows, actionable_count = apply_quality_gate(rows, level, held_symbols, MAX_ACTIONABLE_SIGNALS)
        finalist_rows = [r for r in rows if r.get("is_finalist")]
        metrics["deep"] = len(rows)
        metrics["finalists"] = finalist_count
        metrics["raw_signals"] = sum(1 for r in rows if r.get("signal") == "BUY" and not r.get("is_held"))
        metrics["signals"] = sum(1 for r in finalist_rows if r.get("signal") == "BUY")
        metrics["actionable"] = actionable_count
        metrics["errors"] = int(metrics.get("errors", 0)) + int(deep_errors)
        metrics["duration"] = round(time.perf_counter() - started, 2)
        self.last_metrics = metrics
        return rows, metrics
