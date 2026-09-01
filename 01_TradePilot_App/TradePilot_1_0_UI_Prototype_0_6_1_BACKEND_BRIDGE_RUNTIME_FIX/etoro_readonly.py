from __future__ import annotations

"""Read-only eToro REAL adapter for TradePilot 1.0 UI Prototype 0.6.

This module intentionally contains no order endpoint and no HTTP POST/PUT/PATCH/DELETE.
It only reads the authenticated REAL portfolio and REAL P/L surfaces.
"""

import json
import math
import os
import uuid
from pathlib import Path
from typing import Any

import requests

BASE_V1 = "https://public-api.etoro.com/api/v1"
REAL_PORTFOLIO_URL = f"{BASE_V1}/trading/info/portfolio"
REAL_PNL_URL = f"{BASE_V1}/trading/info/real/pnl"


class EtoroReadOnlyError(RuntimeError):
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


def write_credentials(path: Path, api_key: str, user_key: str) -> None:
    api_key = str(api_key or "").strip().replace("\n", "").replace("\r", "")
    user_key = str(user_key or "").strip().replace("\n", "").replace("\r", "")
    if not api_key or not user_key:
        raise EtoroReadOnlyError("API-Key und REAL User-Key dürfen nicht leer sein.")
    text = (
        "# TradePilot local eToro REAL credentials - DO NOT COMMIT\n"
        "ETORO_ENV=real\n"
        f"ETORO_API_KEY={api_key}\n"
        f"ETORO_REAL_USER_KEY={user_key}\n"
    )
    path.write_text(text, encoding="utf-8")


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except Exception:
        return None


def _norm_key(key: Any) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum())


def _pick_number(mapping: dict, keys: tuple[str, ...]) -> float | None:
    wanted = {_norm_key(k) for k in keys}
    for key, value in mapping.items():
        if _norm_key(key) in wanted:
            number = _finite(value)
            if number is not None:
                return number
    return None


def _pick_text(mapping: dict, keys: tuple[str, ...]) -> str | None:
    wanted = {_norm_key(k) for k in keys}
    for key, value in mapping.items():
        if _norm_key(key) in wanted and value is not None:
            text = str(value).strip()
            if text:
                return text
    return None


def _unwrap(payload: Any) -> dict:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"positions": data}
        return payload
    if isinstance(payload, list):
        return {"positions": payload}
    return {}


def _positions(data: dict) -> list[dict]:
    for key in ("positions", "openPositions", "portfolio", "items"):
        rows = data.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _position_value(position: dict) -> float | None:
    return _pick_number(position, (
        "currentValue", "marketValue", "positionValue", "value", "invested",
        "investedAmount", "investment", "amount"
    ))


def _position_pnl(position: dict) -> float | None:
    return _pick_number(position, ("pnl", "profitLoss", "profit", "unrealizedPnl", "openPnl"))


def _position_row(position: dict, currency: str) -> dict:
    symbol = _pick_text(position, ("symbol", "ticker", "instrumentSymbol", "internalSymbol"))
    name = _pick_text(position, ("instrumentName", "displayName", "name", "marketName"))
    instrument_id = _pick_text(position, ("instrumentId", "instrumentID", "marketId", "id"))
    if not symbol:
        symbol = name or (f"#{instrument_id}" if instrument_id else "POSITION")
    if not name:
        name = symbol
    value = _position_value(position)
    pnl = _position_pnl(position)
    units = _pick_number(position, ("units", "shares", "quantity", "amountUnits"))
    opened = _pick_text(position, ("openDate", "openedAt", "createdAt", "openTime", "date")) or ""
    return {
        "symbol": str(symbol)[:16],
        "company": str(name)[:48],
        "value": value,
        "pnl": pnl,
        "units": units,
        "time": opened,
        "currency": currency,
    }


def parse_snapshot(portfolio_payload: Any, pnl_payload: Any | None = None) -> dict:
    data = _unwrap(portfolio_payload)
    pnl_data = _unwrap(pnl_payload) if pnl_payload is not None else {}
    positions = _positions(data)

    currency = (_pick_text(data, ("currency", "accountCurrency", "baseCurrency")) or "USD").upper()
    cash = _pick_number(data, (
        "buyingPower", "cash", "availableCash", "cashAvailable", "availableBalance",
        "cashBalance", "balance"
    ))
    equity = _pick_number(data, (
        "equity", "portfolioValue", "netEquity", "totalValue", "totalEquity", "accountValue"
    ))
    invested = _pick_number(data, (
        "invested", "investedAmount", "positionsValue", "marketValue", "openPositionsValue"
    ))

    position_values = [v for v in (_position_value(p) for p in positions) if v is not None]
    if invested is None and position_values:
        invested = sum(position_values)
    if equity is None and cash is not None and invested is not None:
        equity = cash + invested
    if invested is None and equity is not None and cash is not None:
        invested = max(0.0, equity - cash)
    if cash is None and equity is not None and invested is not None:
        cash = equity - invested

    open_pnls = [v for v in (_position_pnl(p) for p in positions) if v is not None]
    open_pnl = sum(open_pnls) if open_pnls else _pick_number(data, ("pnl", "openPnl", "unrealizedPnl"))

    today_pnl = _pick_number(pnl_data, (
        "todayPnl", "dailyPnl", "dayPnl", "todayProfit", "dailyProfit", "dayProfit"
    ))
    if today_pnl is None:
        today_pnl = _pick_number(data, (
            "todayPnl", "dailyPnl", "dayPnl", "todayProfit", "dailyProfit", "dayProfit"
        ))
    today_pct = _pick_number(pnl_data, (
        "todayPnlPercent", "dailyPnlPercent", "dayPnlPercent", "todayPercent", "dailyPercent"
    ))
    if today_pct is None:
        today_pct = _pick_number(data, (
            "todayPnlPercent", "dailyPnlPercent", "dayPnlPercent", "todayPercent", "dailyPercent"
        ))

    rows = [_position_row(p, currency) for p in positions]
    return {
        "currency": currency,
        "cash": cash,
        "invested": invested,
        "equity": equity,
        "open_pnl": open_pnl,
        "today_pnl": today_pnl,
        "today_pct": today_pct,
        "positions": rows,
        "position_count": len(rows),
        "portfolio_top_keys": sorted(str(k) for k in (portfolio_payload.keys() if isinstance(portfolio_payload, dict) else [])),
        "data_keys": sorted(str(k) for k in data.keys()),
        "pnl_keys": sorted(str(k) for k in pnl_data.keys()),
    }


class EtoroReadOnlyClient:
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

    def has_credentials(self) -> bool:
        api_key, user_key = self.credentials()
        return bool(api_key and user_key)

    def _headers(self) -> dict[str, str]:
        api_key, user_key = self.credentials()
        if not api_key or not user_key:
            raise EtoroReadOnlyError("eToro-REAL-Zugangsdaten fehlen. 03_SETUP_ETORO_KEYS.bat ausführen.")
        return {
            "x-api-key": api_key,
            "x-user-key": user_key,
            "x-request-id": str(uuid.uuid4()),
            "accept": "application/json",
        }

    @staticmethod
    def _decode(response: requests.Response) -> Any:
        try:
            payload = response.json()
        except Exception:
            payload = response.text
        if not response.ok:
            if response.status_code == 429:
                raise EtoroReadOnlyError("eToro API Rate Limit (429). TradePilot wartet bis zum nächsten Refresh.")
            text = json.dumps(payload, ensure_ascii=False) if isinstance(payload, (dict, list)) else str(payload)
            raise EtoroReadOnlyError(f"eToro API {response.status_code}: {text[:700]}")
        return payload

    def _get(self, url: str) -> Any:
        response = self.session.get(url, headers=self._headers(), timeout=self.timeout)
        return self._decode(response)

    def portfolio(self) -> Any:
        return self._get(REAL_PORTFOLIO_URL)

    def pnl_optional(self) -> tuple[Any | None, str | None]:
        try:
            return self._get(REAL_PNL_URL), None
        except Exception as exc:
            return None, str(exc)

    def snapshot(self) -> dict:
        portfolio = self.portfolio()
        pnl, pnl_warning = self.pnl_optional()
        result = parse_snapshot(portfolio, pnl)
        result["pnl_warning"] = pnl_warning
        return result
