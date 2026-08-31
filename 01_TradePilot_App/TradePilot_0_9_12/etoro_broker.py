from __future__ import annotations

"""eToro Real API adapter for TradePilot 0.9.12.

Safety scope:
- Real portfolio connection is supported.
- Live orders are explicit/manual only in 0.9.12; AutoTrader is NOT wired to live execution.
- Hard user budget: maximum EUR 10.00 per live order.
- eToro unified live execution uses USD in the documented examples, therefore the EUR budget
  is converted with a fresh EURUSD=X quote. If FX cannot be obtained, the live order is refused.
- Long BUY only, leverage 1. No shorting.
- If the real portfolio already contains an open position, a new live test order is refused.
- Credentials stay in a local .env file.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any

import requests
import yfinance as yf

BASE_V1 = "https://public-api.etoro.com/api/v1"
LIVE_ORDER_URL = "https://public-api.etoro.com/api/v2/trading/execution/orders"
LIVE_PORTFOLIO_URL = f"{BASE_V1}/trading/info/portfolio"
MAX_LIVE_EUR = 10.00


class EtoroError(RuntimeError):
    pass


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        if not path.exists():
            return values
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                values[key] = value
    except Exception:
        return {}
    return values


def _write_dotenv(path: Path, updates: dict[str, str]) -> None:
    current = _load_dotenv(path)
    current.update({k: str(v).strip() for k, v in updates.items()})
    ordered = ["ETORO_ENV", "ETORO_API_KEY", "ETORO_REAL_USER_KEY"]
    lines = ["# TradePilot local eToro REAL credentials - DO NOT COMMIT"]
    for key in ordered:
        if key in current:
            value = current[key].replace("\n", "").replace("\r", "")
            lines.append(f"{key}={value}")
    for key in sorted(k for k in current if k not in ordered):
        value = current[key].replace("\n", "").replace("\r", "")
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class EtoroLiveBroker:
    def __init__(self, app_dir: Path, timeout: float = 20.0):
        self.app_dir = Path(app_dir)
        self.env_path = self.app_dir / ".env"
        self.timeout = float(timeout)
        self.session = requests.Session()

    def credentials(self) -> tuple[str, str]:
        env = _load_dotenv(self.env_path)
        api_key = os.getenv("ETORO_API_KEY", "").strip() or env.get("ETORO_API_KEY", "").strip()
        user_key = os.getenv("ETORO_REAL_USER_KEY", "").strip() or env.get("ETORO_REAL_USER_KEY", "").strip()
        return api_key, user_key

    def save_credentials(self, api_key: str, user_key: str) -> None:
        api_key = str(api_key or "").strip()
        user_key = str(user_key or "").strip()
        if not api_key or not user_key:
            raise EtoroError("API-Key und REAL User-Key dürfen nicht leer sein.")
        _write_dotenv(self.env_path, {
            "ETORO_ENV": "real",
            "ETORO_API_KEY": api_key,
            "ETORO_REAL_USER_KEY": user_key,
        })

    def _headers(self) -> dict[str, str]:
        api_key, user_key = self.credentials()
        if not api_key or not user_key:
            raise EtoroError("eToro-REAL-Zugangsdaten fehlen. Bitte zuerst lokal speichern.")
        return {
            "x-api-key": api_key,
            "x-user-key": user_key,
            "x-request-id": str(uuid.uuid4()),
            "content-type": "application/json",
            "accept": "application/json",
        }

    @staticmethod
    def _decode_response(response: requests.Response) -> Any:
        try:
            payload = response.json()
        except Exception:
            payload = response.text
        if not response.ok:
            text = json.dumps(payload, ensure_ascii=False) if isinstance(payload, (dict, list)) else str(payload)
            raise EtoroError(f"eToro API {response.status_code}: {text[:900]}")
        return payload

    def real_portfolio(self) -> dict:
        response = self.session.get(LIVE_PORTFOLIO_URL, headers=self._headers(), timeout=self.timeout)
        payload = self._decode_response(response)
        return payload if isinstance(payload, dict) else {"data": payload}

    @staticmethod
    def _portfolio_data(payload: dict) -> dict:
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        return data if isinstance(data, dict) else {}

    def test_connection(self) -> dict:
        payload = self.real_portfolio()
        data = self._portfolio_data(payload)
        positions = data.get("positions", [])
        return {
            "ok": True,
            "environment": "REAL",
            "currency": data.get("currency") or data.get("accountCurrency") or "—",
            "buying_power": data.get("buyingPower", data.get("cash", data.get("availableCash"))),
            "equity": data.get("equity", data.get("portfolioValue", data.get("netEquity"))),
            "positions": len(positions) if isinstance(positions, list) else None,
            "raw": payload,
        }

    def open_position_count(self) -> int:
        data = self._portfolio_data(self.real_portfolio())
        positions = data.get("positions", [])
        return len(positions) if isinstance(positions, list) else 0

    def search_instrument(self, symbol: str) -> dict:
        symbol = str(symbol or "").strip().upper()
        if not symbol:
            raise EtoroError("Ticker fehlt.")
        response = self.session.get(
            f"{BASE_V1}/market-data/search",
            headers=self._headers(),
            params={"search": symbol},
            timeout=self.timeout,
        )
        payload = self._decode_response(response)
        rows = []
        if isinstance(payload, dict):
            rows = payload.get("data") or payload.get("instruments") or payload.get("items") or []
        elif isinstance(payload, list):
            rows = payload
        if not isinstance(rows, list) or not rows:
            raise EtoroError(f"Kein eToro-Instrument für {symbol} gefunden.")
        for row in rows:
            if isinstance(row, dict) and str(row.get("symbol", "")).upper() == symbol:
                return row
        first = rows[0]
        if not isinstance(first, dict):
            raise EtoroError(f"Ungültige Instrument-Antwort für {symbol}.")
        return first

    @staticmethod
    def _eurusd_rate() -> float:
        try:
            hist = yf.Ticker("EURUSD=X").history(period="5d", interval="1d", auto_adjust=False)
            if hist is None or hist.empty:
                raise ValueError("keine FX-Daten")
            close = float(hist["Close"].dropna().iloc[-1])
            if not 0.5 <= close <= 2.0:
                raise ValueError("unplausibler EUR/USD-Kurs")
            return close
        except Exception as exc:
            raise EtoroError(f"EUR/USD-Kurs konnte nicht sicher geladen werden; LIVE-Order wird blockiert. ({exc})") from exc

    def live_amount_usd_for_eur_budget(self, amount_eur: float) -> tuple[float, float]:
        eur = round(float(amount_eur), 2)
        if eur <= 0 or eur > MAX_LIVE_EUR:
            raise EtoroError(f"Harte LIVE-Grenze: maximal {MAX_LIVE_EUR:.2f} EUR pro Order.")
        rate = self._eurusd_rate()
        usd = round(eur * rate, 2)
        if usd <= 0:
            raise EtoroError("Umgerechneter Orderbetrag ist ungültig.")
        return usd, rate

    def place_live_market_buy(self, symbol: str, amount_eur: float) -> dict:
        eur = round(float(amount_eur), 2)
        if eur <= 0 or eur > MAX_LIVE_EUR:
            raise EtoroError(f"Harte LIVE-Grenze: maximal {MAX_LIVE_EUR:.2f} EUR pro Order.")
        if self.open_position_count() >= 1:
            raise EtoroError("LIVE-Sicherheitsstopp: Das eToro-REAL-Portfolio hat bereits mindestens eine offene Position. 0.9.12 erlaubt keinen weiteren Testkauf.")
        amount_usd, fx = self.live_amount_usd_for_eur_budget(eur)
        instrument = self.search_instrument(symbol)
        instrument_id = instrument.get("instrumentId") or instrument.get("instrumentID") or instrument.get("id")
        if instrument_id is None:
            raise EtoroError("eToro Instrument-ID fehlt in der Suchantwort.")
        body = {
            "action": "open",
            "transaction": "buy",
            "instrumentId": int(instrument_id),
            "orderType": "mkt",
            "amount": amount_usd,
            "orderCurrency": "usd",
            "leverage": 1,
            "stopLossType": "fixed",
        }
        response = self.session.post(LIVE_ORDER_URL, headers=self._headers(), json=body, timeout=self.timeout)
        payload = self._decode_response(response)
        return {
            "ok": True,
            "environment": "REAL",
            "symbol": str(symbol).upper(),
            "instrument_id": int(instrument_id),
            "budget_eur": eur,
            "amount_usd": amount_usd,
            "eurusd": fx,
            "leverage": 1,
            "response": payload,
        }
