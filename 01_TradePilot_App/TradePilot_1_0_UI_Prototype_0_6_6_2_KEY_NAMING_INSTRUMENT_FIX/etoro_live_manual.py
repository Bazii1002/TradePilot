from __future__ import annotations

"""Manual eToro REAL execution bridge for TradePilot UI Prototype 0.6.6.

Safety scope:
- Manual BUY only. AutoTrader is NOT connected to this module.
- Hard maximum EUR 10.00 per order; never auto-increase to broker minimums.
- Leverage fixed at 1; no shorting.
- At most one open REAL position during the manual live test phase.
- Exact ticker resolution to one eToro instrumentId before confirmation.
- Prepared order is immutable, single-use and expires after 120 seconds.
- Credentials remain local in .env.
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
        self.timeout = float(timeout)
        self.session = requests.Session()
        self._used_tokens: set[str] = set()

    def credentials(self) -> tuple[str, str]:
        env = _load_dotenv(self.env_path)
        public_key = (os.getenv("ETORO_PUBLIC_KEY", "").strip() or env.get("ETORO_PUBLIC_KEY", "").strip()
                      or os.getenv("ETORO_API_KEY", "").strip() or env.get("ETORO_API_KEY", "").strip())
        private_key = (os.getenv("ETORO_PRIVATE_KEY", "").strip() or env.get("ETORO_PRIVATE_KEY", "").strip()
                       or os.getenv("ETORO_REAL_USER_KEY", "").strip() or env.get("ETORO_REAL_USER_KEY", "").strip())
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

    def search_exact_instrument(self, symbol: str) -> dict:
        symbol=str(symbol or "").strip().upper()
        if not symbol or len(symbol)>12 or not all(c.isalnum() or c in '.-' for c in symbol):
            raise EtoroLiveError("Ticker fehlt oder ist ungültig.")
        resp=self.session.get(f"{BASE_V1}/market-data/search", headers=self._headers(), params={"internalSymbolFull":symbol}, timeout=self.timeout)
        rows=self._instrument_rows(self._decode(resp))
        exact=[]
        for row in rows:
            s=str(row.get("symbol") or row.get("ticker") or row.get("internalSymbolFull") or row.get("internalSymbol") or "").strip().upper()
            if s==symbol:
                exact.append(row)
        if not exact:
            raise EtoroLiveError(f"Kein eindeutiger exakter eToro-Treffer für {symbol}.")
        with_id=[r for r in exact if r.get("instrumentId") is not None or r.get("instrumentID") is not None or r.get("id") is not None]
        if len(with_id)!=1:
            raise EtoroLiveError(f"{symbol}: {len(with_id)} exakte Treffer mit Instrument-ID; LIVE wird blockiert.")
        return with_id[0]

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

    def place_prepared(self, prepared: dict) -> dict:
        if not isinstance(prepared,dict) or prepared.get("environment")!="REAL":
            raise EtoroLiveError("Ungültige vorbereitete LIVE-Order.")
        token=str(prepared.get("token") or "")
        if not token or token in self._used_tokens:
            raise EtoroLiveError("Vorbereitete Order ist bereits verbraucht oder ungültig.")
        try: age=time.time()-float(prepared.get("prepared_at",0))
        except Exception: age=999999
        if age<0 or age>PREPARED_TTL_SECONDS:
            raise EtoroLiveError("LIVE-Vorbereitung ist abgelaufen. Bitte neu vorbereiten.")
        eur=round(float(prepared.get("budget_eur",0)),2)
        usd=round(float(prepared.get("amount_usd",0)),2)
        symbol=str(prepared.get("symbol") or "").strip().upper()
        iid=int(prepared.get("instrument_id") or 0)
        if eur<=0 or eur>MAX_LIVE_EUR or usd<=0 or not symbol or iid<=0 or int(prepared.get("leverage") or 0)!=1:
            raise EtoroLiveError("Vorbereitete LIVE-Order verletzt Sicherheitsgrenzen.")
        if self.open_position_count()>=1:
            raise EtoroLiveError("LIVE-Sicherheitsstopp: Vor Versand wurde eine offene REAL-Position erkannt.")
        body={
            "action":"open",
            "transaction":"buy",
            "instrumentId":iid,
            "orderType":"mkt",
            "amount":usd,
            "orderCurrency":"usd",
            "leverage":1,
            "stopLossType":"fixed",
        }
        request_id=str(uuid.uuid4())
        headers=self._headers(); headers["x-request-id"]=request_id
        resp=self.session.post(LIVE_ORDER_URL, headers=headers, json=body, timeout=self.timeout)
        payload=self._decode(resp)
        self._used_tokens.add(token)
        return {
            "ok":True,"request_id":request_id,"symbol":symbol,"instrument_id":iid,
            "budget_eur":eur,"amount_usd":usd,"eurusd":float(prepared.get("eurusd",0)),
            "response":payload,
        }
