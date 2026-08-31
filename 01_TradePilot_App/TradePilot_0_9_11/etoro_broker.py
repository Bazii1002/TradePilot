from __future__ import annotations

"""Minimal eToro Demo API adapter for TradePilot 0.9.11.

Safety scope of 0.9.11:
- Demo account only.
- Credentials stay in a local .env file next to the application.
- Real execution endpoint is intentionally not implemented.
- AutoTrader is not yet wired to this broker; only explicit manual demo tests are allowed.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Any

import requests

BASE_V1 = "https://public-api.etoro.com/api/v1"
DEMO_ORDER_URL = "https://public-api.etoro.com/api/v2/trading/execution/demo/orders"


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
    ordered = ["ETORO_ENV", "ETORO_API_KEY", "ETORO_USER_KEY"]
    lines = ["# TradePilot local eToro credentials - DO NOT COMMIT"]
    for key in ordered:
        if key in current:
            value = current[key].replace("\n", "").replace("\r", "")
            lines.append(f"{key}={value}")
    for key in sorted(k for k in current if k not in ordered):
        value = current[key].replace("\n", "").replace("\r", "")
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class EtoroDemoBroker:
    def __init__(self, app_dir: Path, timeout: float = 20.0):
        self.app_dir = Path(app_dir)
        self.env_path = self.app_dir / ".env"
        self.timeout = float(timeout)
        self.session = requests.Session()

    def credentials(self) -> tuple[str, str]:
        env = _load_dotenv(self.env_path)
        api_key = os.getenv("ETORO_API_KEY", "").strip() or env.get("ETORO_API_KEY", "").strip()
        user_key = os.getenv("ETORO_USER_KEY", "").strip() or env.get("ETORO_USER_KEY", "").strip()
        return api_key, user_key

    def save_credentials(self, api_key: str, user_key: str) -> None:
        api_key = str(api_key or "").strip()
        user_key = str(user_key or "").strip()
        if not api_key or not user_key:
            raise EtoroError("API-Key und User-Key dürfen nicht leer sein.")
        _write_dotenv(self.env_path, {
            "ETORO_ENV": "demo",
            "ETORO_API_KEY": api_key,
            "ETORO_USER_KEY": user_key,
        })

    def _headers(self) -> dict[str, str]:
        api_key, user_key = self.credentials()
        if not api_key or not user_key:
            raise EtoroError("eToro-Zugangsdaten fehlen. Bitte zuerst lokal speichern.")
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
            raise EtoroError(f"eToro API {response.status_code}: {text[:700]}")
        return payload

    def demo_portfolio(self) -> dict:
        response = self.session.get(
            f"{BASE_V1}/trading/info/demo/portfolio",
            headers=self._headers(),
            timeout=self.timeout,
        )
        payload = self._decode_response(response)
        return payload if isinstance(payload, dict) else {"data": payload}

    def test_connection(self) -> dict:
        payload = self.demo_portfolio()
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            data = {}
        positions = data.get("positions", [])
        return {
            "ok": True,
            "currency": data.get("currency") or data.get("accountCurrency") or "—",
            "buying_power": data.get("buyingPower", data.get("cash", data.get("availableCash"))),
            "equity": data.get("equity", data.get("portfolioValue", data.get("netEquity"))),
            "positions": len(positions) if isinstance(positions, list) else None,
            "raw": payload,
        }

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
        # Prefer exact symbol match if present.
        for row in rows:
            if isinstance(row, dict) and str(row.get("symbol", "")).upper() == symbol:
                return row
        first = rows[0]
        if not isinstance(first, dict):
            raise EtoroError(f"Ungültige Instrument-Antwort für {symbol}.")
        return first

    def place_demo_market_buy(self, symbol: str, amount_usd: float) -> dict:
        amount = float(amount_usd)
        if amount <= 0:
            raise EtoroError("Orderbetrag muss größer als 0 sein.")
        instrument = self.search_instrument(symbol)
        instrument_id = instrument.get("instrumentId") or instrument.get("instrumentID") or instrument.get("id")
        if instrument_id is None:
            raise EtoroError("eToro Instrument-ID fehlt in der Suchantwort.")
        body = {
            "action": "open",
            "transaction": "buy",
            "instrumentId": int(instrument_id),
            "orderType": "mkt",
            "amount": round(amount, 2),
            "orderCurrency": "usd",
            "leverage": 1,
            "stopLossType": "fixed",
        }
        response = self.session.post(
            DEMO_ORDER_URL,
            headers=self._headers(),
            json=body,
            timeout=self.timeout,
        )
        payload = self._decode_response(response)
        return {
            "ok": True,
            "symbol": str(symbol).upper(),
            "instrument_id": int(instrument_id),
            "amount": round(amount, 2),
            "response": payload,
        }
