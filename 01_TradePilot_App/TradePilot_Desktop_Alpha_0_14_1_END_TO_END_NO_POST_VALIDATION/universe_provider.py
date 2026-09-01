from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

IWB_URL = "https://www.ishares.com/us/products/239707/ishares-russell-1000-etf/latest-holdings.csv"
TARGET_UNIVERSE_SIZE = 1000

# iShares and Yahoo sometimes write share classes differently.
YAHOO_SYMBOL_MAP = {
    "BRKB": "BRK-B",
    "BRKA": "BRK-A",
    "BFB": "BF-B",
    "BFA": "BF-A",
}


def _clean_symbol(symbol: str) -> str:
    s = str(symbol or "").strip().upper()
    return YAHOO_SYMBOL_MAP.get(s, s)


class StockUniverseProvider:
    """Loads/caches a broad ~1000 US-stock universe without touching broker execution."""

    def __init__(self, app_dir: Path):
        self.app_dir = Path(app_dir)
        self.data_dir = self.app_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.data_dir / "stock_universe_1000.json"
        self.fallback_file = self.app_dir / "stock_universe.json"
        self.last_source = "not_loaded"
        self.last_error = ""

    def _load_json_list(self, path: Path) -> list[dict]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        out = []
        for item in raw if isinstance(raw, list) else []:
            if isinstance(item, str):
                sym = _clean_symbol(item)
                if sym:
                    out.append({"symbol": sym, "name": sym, "sector": "", "exchange": ""})
            elif isinstance(item, dict) and item.get("enabled", True) is not False:
                sym = _clean_symbol(item.get("yahoo_symbol") or item.get("symbol"))
                if sym:
                    out.append({
                        "symbol": sym,
                        "broker_symbol": str(item.get("symbol") or sym).upper(),
                        "name": str(item.get("name") or sym),
                        "sector": str(item.get("sector") or ""),
                        "exchange": str(item.get("exchange") or item.get("market") or ""),
                    })
        # stable dedupe
        seen, dedup = set(), []
        for row in out:
            if row["symbol"] not in seen:
                seen.add(row["symbol"]); dedup.append(row)
        return dedup

    def cached(self) -> list[dict]:
        rows = self._load_json_list(self.cache_file)
        if len(rows) >= 900:
            self.last_source = "cache"
            return rows[:TARGET_UNIVERSE_SIZE]
        return []

    def fallback(self) -> list[dict]:
        rows = self._load_json_list(self.fallback_file)
        self.last_source = "fallback_74"
        return rows

    def refresh(self, timeout: int = 25) -> list[dict]:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 TradePilot/0.13.3"}
        response = requests.get(IWB_URL, timeout=timeout, headers=headers)
        response.raise_for_status()
        text = response.text
        lines = text.splitlines()
        header_index = next((i for i, line in enumerate(lines) if line.startswith("Ticker,Name,Sector,Asset Class")), None)
        if header_index is None:
            raise RuntimeError("IWB Holdings CSV: Tabellenkopf nicht gefunden")
        reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])))
        rows = []
        for item in reader:
            if str(item.get("Asset Class") or "").strip().lower() != "equity":
                continue
            ticker_raw = str(item.get("Ticker") or "").strip().upper()
            if not ticker_raw or ticker_raw in {"-", "USD"}:
                continue
            symbol = _clean_symbol(ticker_raw)
            if not symbol:
                continue
            rows.append({
                "symbol": symbol,
                "broker_symbol": ticker_raw,
                "name": str(item.get("Name") or symbol).strip(),
                "sector": str(item.get("Sector") or "").strip(),
                "exchange": str(item.get("Exchange") or "").strip(),
                "location": str(item.get("Location") or "").strip(),
                "source": "iShares Russell 1000 ETF holdings",
            })
        seen, dedup = set(), []
        for row in rows:
            if row["symbol"] not in seen:
                seen.add(row["symbol"]); dedup.append(row)
        if len(dedup) < 900:
            raise RuntimeError(f"IWB Holdings lieferte nur {len(dedup)} Aktien")
        dedup = dedup[:TARGET_UNIVERSE_SIZE]
        payload = dedup
        tmp = self.cache_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.cache_file)
        self.last_source = "iwb_live"
        self.last_error = ""
        return payload

    def load(self, allow_refresh: bool = True) -> list[dict]:
        rows = self.cached()
        if rows:
            return rows
        if allow_refresh:
            try:
                return self.refresh()
            except Exception as exc:
                self.last_error = str(exc)[:240]
        return self.fallback()

    def status(self, rows: list[dict]) -> dict:
        return {
            "count": len(rows),
            "source": self.last_source,
            "error": self.last_error,
            "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
