from __future__ import annotations

"""Manual eToro REAL execution bridge for TradePilot UI Prototype 0.6.6.6.

Safety scope:
- Manual BUY only. AutoTrader is NOT connected to this module.
- Hard maximum EUR 10.00 per order; never auto-increase to broker minimums.
- Leverage fixed at 1; no shorting.
- At most one open REAL position during the manual live test phase.
- Exact ticker resolution to one eToro instrumentId before confirmation.
- Prepared order is immutable, single-use and expires after 120 seconds.
- Credentials remain local; central C:\\TradePilot\\.env is preferred as a safe version-independent fallback.
"""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import requests
import yfinance as yf

BASE_V1 = "https://public-api.etoro.com/api/v1"
LIVE_ORDER_URL = "https://public-api.etoro.com/api/v2/trading/execution/orders"
LIVE_PORTFOLIO_URL = f"{BASE_V1}/trading/info/portfolio"
MAX_LIVE_EUR = 10.00
PREPARED_TTL_SECONDS = 120
DEFAULT_WATCHLIST_ITEMS_URL = f"{BASE_V1}/watchlists/default-watchlists/items"
INSTRUMENTS_METADATA_URL = f"{BASE_V1}/market-data/instruments"
INSTRUMENT_CACHE_FILE = "instrument_cache.json"

class EtoroLiveError(RuntimeError):
    pass

def _load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k,v=line.split("=",1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        return {}
    return out

class EtoroManualLiveBroker:
    def __init__(self, app_dir: Path, timeout: float = 20.0):
        self.app_dir = Path(app_dir)
        self.env_path = self.app_dir / ".env"
        # Versions live below C:\TradePilot\01_TradePilot_App\<version>.
        # Keep secrets outside version folders so upgrades do not lose credentials.
        try:
            self.central_env_path = self.app_dir.parent.parent / ".env"
        except Exception:
            self.central_env_path = self.env_path
        self.timeout = float(timeout)
        self.session = requests.Session()
        self._used_tokens: set[str] = set()
        self.instrument_cache_path = self.app_dir / INSTRUMENT_CACHE_FILE

    def credentials(self) -> tuple[str, str]:
        # Priority: process environment -> local version .env -> central C:\\TradePilot\\.env.
        # Local .env remains supported for backward compatibility.
        local_env = _load_dotenv(self.env_path)
        central_env = _load_dotenv(self.central_env_path) if self.central_env_path != self.env_path else {}

        def pick(*names: str) -> str:
            for name in names:
                value = os.getenv(name, "").strip()
                if value:
                    return value
            for source in (local_env, central_env):
                for name in names:
                    value = source.get(name, "").strip()
                    if value:
                        return value
            return ""

        public_key = pick("ETORO_PUBLIC_KEY", "ETORO_API_KEY")
        private_key = pick("ETORO_PRIVATE_KEY", "ETORO_USER_KEY", "ETORO_REAL_USER_KEY")
        return public_key, private_key

    def _headers(self) -> dict[str,str]:
        public_key,private_key=self.credentials()
        if not public_key or not private_key:
            raise EtoroLiveError("eToro-REAL-Zugangsdaten fehlen (Öffentlicher Key / Privater Key).")
        return {
            "x-api-key": public_key,
            "x-user-key": private_key,
            "x-request-id": str(uuid.uuid4()),
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": "TradePilot/1.0 (manual live safety bridge)",
        }

    @staticmethod
    def _decode(resp: requests.Response) -> Any:
        try:
            payload=resp.json()
        except Exception:
            payload=resp.text
        if not resp.ok:
            text=json.dumps(payload, ensure_ascii=False) if isinstance(payload,(dict,list)) else str(payload)
            raise EtoroLiveError(f"eToro API {resp.status_code}: {text[:900]}")
        return payload

    @staticmethod
    def _portfolio_root(payload: Any) -> dict:
        if not isinstance(payload, dict):
            return {}
        cp = payload.get("clientPortfolio")
        if isinstance(cp, dict):
            return cp
        data = payload.get("data")
        if isinstance(data, dict):
            cp = data.get("clientPortfolio")
            return cp if isinstance(cp, dict) else data
        return payload

    def open_position_count(self) -> int:
        resp=self.session.get(LIVE_PORTFOLIO_URL, headers=self._headers(), timeout=self.timeout)
        root=self._portfolio_root(self._decode(resp))
        rows=root.get("positions", [])
        return len(rows) if isinstance(rows, list) else 0

    @staticmethod
    def _instrument_rows(payload: Any) -> list[dict]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x,dict)]
        if not isinstance(payload, dict):
            return []
        out=[]
        for node in (payload, payload.get("data")):
            if isinstance(node,list):
                out.extend(x for x in node if isinstance(x,dict))
            elif isinstance(node,dict):
                for key in ("instruments","items","results","data"):
                    rows=node.get(key)
                    if isinstance(rows,list):
                        out.extend(x for x in rows if isinstance(x,dict))
        # stable de-dup by object serialization
        seen=set(); clean=[]
        for row in out:
            key=(row.get("instrumentId"), row.get("instrumentID"), row.get("id"), row.get("symbol"), row.get("ticker"))
            if key not in seen:
                seen.add(key); clean.append(row)
        return clean

    def _load_instrument_cache(self) -> dict[str, dict]:
        try:
            if not self.instrument_cache_path.exists():
                return {}
            raw=json.loads(self.instrument_cache_path.read_text(encoding="utf-8"))
            if not isinstance(raw,dict):
                return {}
            clean={}
            for k,v in raw.items():
                if isinstance(k,str) and isinstance(v,dict):
                    clean[k.strip().upper()]=v
            return clean
        except Exception:
            return {}

    def _save_instrument_cache(self, symbol: str, row: dict) -> None:
        cache=self._load_instrument_cache()
        cache[symbol.upper()]={
            "instrumentId": self._instrument_id(row),
            "symbol": symbol.upper(),
            "displayName": str(row.get("displayName") or row.get("instrumentDisplayName") or row.get("name") or symbol.upper()),
            "source": str(row.get("_resolutionSource") or "unknown"),
            "cachedAt": int(time.time()),
        }
        tmp=self.instrument_cache_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.instrument_cache_path)

    @staticmethod
    def _watchlist_instrument_ids(payload: Any) -> list[int]:
        """Extract instrument IDs from the official default-watchlist response."""
        if isinstance(payload, dict):
            for key in ("data", "items", "results"):
                node = payload.get(key)
                if isinstance(node, list):
                    payload = node
                    break
        if not isinstance(payload, list):
            return []

        out: list[int] = []
        seen: set[int] = set()
        for item in payload:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("itemType") or item.get("ItemType") or "").strip().lower()
            if item_type and item_type != "instrument":
                continue
            raw = item.get("itemId")
            if raw is None:
                raw = item.get("ItemId")
            try:
                iid = int(raw)
            except Exception:
                continue
            if iid > 0 and iid not in seen:
                seen.add(iid)
                out.append(iid)
        return out

    def _metadata_rows_for_ids(self, instrument_ids: list[int]) -> list[dict]:
        """Read official instrument metadata for known IDs, chunked to keep URLs bounded."""
        rows: list[dict] = []
        for pos in range(0, len(instrument_ids), 100):
            chunk = instrument_ids[pos:pos + 100]
            if not chunk:
                continue
            resp = self.session.get(
                INSTRUMENTS_METADATA_URL,
                headers=self._headers(),
                params={"instrumentIds": ",".join(str(x) for x in chunk)},
                timeout=self.timeout,
            )
            rows.extend(self._instrument_rows(self._decode(resp)))
        return rows

    @staticmethod
    def _row_symbol(row: dict) -> str:
        return str(
            row.get("internalSymbolFull")
            or row.get("symbolFull")
            or row.get("symbol")
            or row.get("ticker")
            or row.get("internalSymbol")
            or ""
        ).strip().upper()

    def _resolve_via_default_watchlist(self, symbol: str) -> dict | None:
        # Read-only fallback: obtain trusted instrument IDs from the user's default watchlist,
        # then resolve those IDs through the official instrument metadata endpoint.
        resp = self.session.get(
            DEFAULT_WATCHLIST_ITEMS_URL,
            headers=self._headers(),
            params={"itemsPerPage": 1000, "itemsLimit": 1000},
            timeout=self.timeout,
        )
        ids = self._watchlist_instrument_ids(self._decode(resp))
        if not ids:
            return None

        rows = self._metadata_rows_for_ids(ids)
        exact = [r for r in rows if self._row_symbol(r) == symbol]
        with_id = [r for r in exact if any(r.get(k) is not None for k in ("instrumentId", "instrumentID", "id"))]
        if len(with_id) == 1:
            row = dict(with_id[0])
            row["symbol"] = symbol
            row["displayName"] = str(
                row.get("displayName") or row.get("instrumentDisplayName") or row.get("name") or symbol
            )
            row["_resolutionSource"] = "default_watchlist+instrument_metadata"
            return row
        if len(with_id) > 1:
            raise EtoroLiveError(
                f"{symbol}: Mehrere exakte Treffer nach Watchlist+Instrument-Metadaten; LIVE wird blockiert."
            )
        return None

    def search_exact_instrument(self, symbol: str, allow_cache: bool = True) -> dict:
        symbol=str(symbol or "").strip().upper()
        if not symbol or len(symbol)>12 or not all(c.isalnum() or c in '.-' for c in symbol):
            raise EtoroLiveError("Ticker fehlt oder ist ungültig.")

        # 1) Local immutable-ID cache. Once a mapping was resolved safely, reuse it.
        cached=self._load_instrument_cache().get(symbol) if allow_cache else None
        if isinstance(cached,dict):
            try:
                if self._instrument_id(cached)>0 and str(cached.get("symbol") or "").upper()==symbol:
                    row=dict(cached); row["_resolutionSource"]="local_cache"
                    return row
            except Exception:
                pass

        # 2) Official market-data search. Some live keys currently return HTTP 400 with an empty body.
        search_error=None
        try:
            resp=self.session.get(
                f"{BASE_V1}/market-data/search",
                headers=self._headers(),
                params={"internalSymbolFull":symbol},
                timeout=self.timeout,
            )
            rows=self._instrument_rows(self._decode(resp))
            exact=[]
            for row in rows:
                s=self._row_symbol(row)
                if s==symbol:
                    exact.append(row)
            with_id=[r for r in exact if r.get("instrumentId") is not None or r.get("instrumentID") is not None or r.get("id") is not None]
            if len(with_id)==1:
                row=dict(with_id[0]); row["_resolutionSource"]="market_data_search"
                self._save_instrument_cache(symbol,row)
                return row
            if len(with_id)>1:
                raise EtoroLiveError(f"{symbol}: {len(with_id)} exakte Search-Treffer mit Instrument-ID; LIVE wird blockiert.")
        except EtoroLiveError as exc:
            search_error=str(exc)

        # 3) Documented read-only default-watchlist endpoint. Its itemId is the instrument ID.
        # This fallback does NOT add/modify a watchlist; it only reads it.
        try:
            row=self._resolve_via_default_watchlist(symbol)
            if row is not None:
                self._save_instrument_cache(symbol,row)
                return row
        except EtoroLiveError as exc:
            raise EtoroLiveError(
                f"Instrument-Auflösung fehlgeschlagen. Search: {search_error or 'kein exakter Treffer'} | "
                f"Watchlist-Fallback: {exc}"
            ) from exc

        extra=f" Search-Fehler: {search_error}" if search_error else ""
        raise EtoroLiveError(
            f"{symbol} konnte nicht sicher auf eine eToro-Instrument-ID aufgelöst werden.{extra} "
            f"Fallback: Der Ticker ist nicht in deiner eToro-Standard-Watchlist. "
            f"Füge {symbol} in der eToro-App manuell zur Standard-Watchlist hinzu und starte den Lookup erneut. "
            "TradePilot verändert die Watchlist nicht automatisch und sendet keine Order ohne eindeutige ID."
        )

    @staticmethod
    def _instrument_id(row: dict) -> int:
        raw=row.get("instrumentId")
        if raw is None: raw=row.get("instrumentID")
        if raw is None: raw=row.get("id")
        try: value=int(raw)
        except Exception as exc: raise EtoroLiveError("eToro Instrument-ID fehlt/ungültig.") from exc
        if value<=0: raise EtoroLiveError("eToro Instrument-ID ungültig.")
        return value

    @staticmethod
    def _eurusd_rate() -> float:
        try:
            hist=yf.Ticker("EURUSD=X").history(period="5d", interval="1d", auto_adjust=False)
            close=float(hist["Close"].dropna().iloc[-1])
            if not 0.5 <= close <= 2.0:
                raise ValueError("unplausibler EUR/USD-Kurs")
            return close
        except Exception as exc:
            raise EtoroLiveError(f"EUR/USD konnte nicht sicher geladen werden; LIVE blockiert. ({exc})") from exc

    def prepare_market_buy(self, symbol: str, budget_eur: float) -> dict:
        try: eur=round(float(budget_eur),2)
        except Exception as exc: raise EtoroLiveError("Budget ist keine gültige Zahl.") from exc
        if eur<=0 or eur>MAX_LIVE_EUR:
            raise EtoroLiveError(f"Harte LIVE-Grenze: maximal {MAX_LIVE_EUR:.2f} EUR pro Order.")
        if self.open_position_count()>=1:
            raise EtoroLiveError("LIVE-Sicherheitsstopp: Bereits mindestens eine offene REAL-Position.")
        instrument=self.search_exact_instrument(symbol)
        iid=self._instrument_id(instrument)
        resolved=str(instrument.get("symbol") or instrument.get("ticker") or symbol).strip().upper()
        if resolved != str(symbol).strip().upper():
            raise EtoroLiveError("Ticker-Auflösung weicht ab; LIVE blockiert.")
        fx=self._eurusd_rate()
        usd=round(eur*fx,2)
        token=str(uuid.uuid4())
        return {
            "token": token,
            "prepared_at": time.time(),
            "environment":"REAL",
            "symbol":resolved,
            "instrument_id":iid,
            "instrument_name":str(instrument.get("displayName") or instrument.get("name") or resolved),
            "budget_eur":eur,
            "amount_usd":usd,
            "eurusd":fx,
            "leverage":1,
        }

    def validate_execution_gate(self, prepared: dict, confirmation: str) -> dict:
        """Final REAL gate. Re-check all critical values after explicit LIVE confirmation.

        This method performs GET/read-only validation only and never submits an order.
        It intentionally bypasses the instrument cache for the final symbol<->ID check.
        If any reviewed critical value changed, a fresh review is required.
        """
        if str(confirmation or "").strip().upper() != "LIVE":
            raise EtoroLiveError("FINAL-GATE: Bestätigung muss exakt LIVE lauten.")
        if not isinstance(prepared,dict) or prepared.get("environment")!="REAL":
            raise EtoroLiveError("FINAL-GATE: Ungültige vorbereitete LIVE-Order.")
        token=str(prepared.get("token") or "")
        if not token or token in self._used_tokens:
            raise EtoroLiveError("FINAL-GATE: Vorbereitung ist bereits verbraucht oder ungültig.")
        try:
            age=time.time()-float(prepared.get("prepared_at",0))
        except Exception:
            age=999999
        if age < 0 or age > PREPARED_TTL_SECONDS:
            raise EtoroLiveError("FINAL-GATE: Review ist abgelaufen. Bitte neu vorbereiten.")

        eur=round(float(prepared.get("budget_eur",0)),2)
        reviewed_usd=round(float(prepared.get("amount_usd",0)),2)
        symbol=str(prepared.get("symbol") or "").strip().upper()
        reviewed_iid=int(prepared.get("instrument_id") or 0)
        if eur<=0 or eur>MAX_LIVE_EUR or reviewed_usd<=0 or not symbol or reviewed_iid<=0:
            raise EtoroLiveError("FINAL-GATE: Review verletzt die harten Sicherheitsgrenzen.")
        if int(prepared.get("leverage") or 0) != 1:
            raise EtoroLiveError("FINAL-GATE: Hebel muss 1x sein.")
        if self.open_position_count() >= 1:
            raise EtoroLiveError("FINAL-GATE: Inzwischen wurde eine offene REAL-Position erkannt.")

        # Bypass cache on the final check: symbol and ID must still match official live metadata/search.
        fresh=self.search_exact_instrument(symbol, allow_cache=False)
        fresh_iid=self._instrument_id(fresh)
        fresh_symbol=str(fresh.get("symbol") or fresh.get("ticker") or symbol).strip().upper()
        if fresh_symbol != symbol or fresh_iid != reviewed_iid:
            raise EtoroLiveError("FINAL-GATE: Instrument-Zuordnung hat sich geändert. Neue Review erforderlich.")

        fresh_fx=self._eurusd_rate()
        fresh_usd=round(eur*fresh_fx,2)
        if fresh_usd != reviewed_usd:
            raise EtoroLiveError(
                f"FINAL-GATE: EUR/USD hat den Orderbetrag von {reviewed_usd:.2f} auf {fresh_usd:.2f} USD geändert. "
                "Neue Review erforderlich."
            )
        return {
            "ok": True,
            "token": token,
            "symbol": symbol,
            "instrument_id": fresh_iid,
            "budget_eur": eur,
            "amount_usd": fresh_usd,
            "eurusd": fresh_fx,
            "leverage": 1,
            "validated_at": time.time(),
        }

    def build_execution_readiness(self, prepared: dict, confirmation: str) -> dict:
        """Build the final reviewed request description without sending it.

        This deliberately ends at the transaction boundary. It performs the same
        GET-only final gate, constructs the reviewed payload preview, and returns
        it for inspection/logging. No POST is possible from this method.
        """
        gate=self.validate_execution_gate(prepared, confirmation)
        body={
            "action":"open",
            "transaction":"buy",
            "instrumentId":gate["instrument_id"],
            "orderType":"mkt",
            "amount":gate["amount_usd"],
            "orderCurrency":"usd",
            "leverage":1,
            "stopLossType":"fixed",
        }
        return {
            "ok":True,
            "mode":"READINESS_ONLY_NO_POST",
            "symbol":gate["symbol"],
            "instrument_id":gate["instrument_id"],
            "budget_eur":gate["budget_eur"],
            "amount_usd":gate["amount_usd"],
            "eurusd":gate["eurusd"],
            "leverage":1,
            "payload_preview":body,
            "validated_at":gate["validated_at"],
        }

    def execute_confirmed(self, prepared: dict, confirmation: str) -> dict:
        raise EtoroLiveError("0.6.6.6: Echtgeld-POST ist in diesem Build deaktiviert. Nur Execution Readiness ist erlaubt.")

    def place_prepared(self, prepared: dict) -> dict:
        raise EtoroLiveError("0.6.6.6: Echtgeld-POST ist in diesem Build deaktiviert.")

