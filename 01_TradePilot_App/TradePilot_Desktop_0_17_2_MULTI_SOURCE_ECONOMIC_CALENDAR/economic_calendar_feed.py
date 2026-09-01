from __future__ import annotations

import json
import os
import re
from datetime import timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests

from macro_logic import ECONOMIC_CALENDAR_URL, _now_utc, _parse_dt, normalize_event

FETCH_LOOKBACK_DAYS = 1
FETCH_AHEAD_DAYS = 14
EVENT_CACHE_MAX_MINUTES = 180
MAX_EVENTS = 250
TE_API_ROOT = "https://api.tradingeconomics.com"
DEFAULT_TE_COUNTRIES = "united states,euro area,germany,united kingdom"


def _clean_name(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    aliases = {
        "non farm payrolls": "nonfarm payrolls",
        "employment situation": "nonfarm payrolls",
        "consumer price index": "cpi",
        "cpi consumer price index": "cpi",
    }
    return aliases.get(s, s)


def _country_code(value: str) -> str:
    s = str(value or "").strip().lower()
    mapping = {
        "united states": "US", "usa": "US", "us": "US", "usd": "US",
        "euro area": "EU", "eurozone": "EU", "eur": "EU", "european union": "EU",
        "germany": "DE", "de": "DE", "deutschland": "DE",
        "united kingdom": "GB", "uk": "GB", "gb": "GB", "great britain": "GB", "gbp": "GB",
        "japan": "JP", "jp": "JP", "jpy": "JP",
        "canada": "CA", "ca": "CA", "cad": "CA",
        "australia": "AU", "au": "AU", "aud": "AU",
        "china": "CN", "cn": "CN", "cny": "CN",
        "switzerland": "CH", "ch": "CH", "chf": "CH",
    }
    return mapping.get(s, str(value or "—").strip().upper() or "—")


def _event_key(event: dict) -> tuple[str, str, str]:
    dt = _parse_dt(event.get("scheduled_at"))
    # Providers can differ by a few seconds. Minute precision is enough for calendar merge.
    stamp = dt.strftime("%Y-%m-%dT%H:%M") if dt else str(event.get("scheduled_at") or "")[:16]
    return (_country_code(event.get("country")), _clean_name(event.get("event_name")), stamp)


def _has(v) -> bool:
    return v not in (None, "", "-", "—", "null", "None")


def _richness(event: dict) -> int:
    return sum(_has(event.get(k)) for k in ("country", "forecast", "previous", "actual", "unit", "source"))


def _merge_event(old: dict | None, new: dict) -> dict:
    if old is None:
        out = dict(new)
        out.setdefault("field_sources", {})
        src = out.get("provider") or out.get("source") or "unknown"
        for k in ("country", "forecast", "previous", "actual", "unit"):
            if _has(out.get(k)):
                out["field_sources"].setdefault(k, src)
        return out
    # Preserve the identity/timing from richer row, but fill every missing field from the other provider.
    primary, secondary = (new, old) if _richness(new) >= _richness(old) else (old, new)
    out = dict(primary)
    fs = dict(old.get("field_sources") or {})
    fs.update(new.get("field_sources") or {})
    for k in ("country", "forecast", "previous", "actual", "unit", "importance_source", "source", "semantic", "relevance"):
        if not _has(out.get(k)) and _has(secondary.get(k)):
            out[k] = secondary.get(k)
            fs[k] = secondary.get("provider") or secondary.get("source") or "unknown"
    # Actual is time-sensitive: prefer any available Actual, regardless of row richness.
    if _has(new.get("actual")):
        out["actual"] = new.get("actual"); fs["actual"] = new.get("provider") or new.get("source") or "unknown"
    # Forecast/Previous may be absent in the timing provider, so enrich them independently.
    for k in ("forecast", "previous"):
        if _has(new.get(k)) and not _has(old.get(k)):
            out[k] = new.get(k); fs[k] = new.get("provider") or new.get("source") or "unknown"
        elif _has(old.get(k)) and not _has(new.get(k)):
            out[k] = old.get(k); fs[k] = old.get("provider") or old.get("source") or "unknown"
    out["country"] = _country_code(out.get("country"))
    out["field_sources"] = fs
    providers = []
    for e in (old, new):
        name = e.get("provider") or e.get("source")
        if name and name not in providers:
            providers.append(name)
    out["merged_providers"] = providers
    return out


def normalize_dedupe_sort(raw_events: Iterable[dict]) -> list[dict]:
    by_key: dict[tuple[str, str, str], dict] = {}
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        event = normalize_event(raw)
        if not event:
            continue
        event["provider"] = str(raw.get("_provider") or raw.get("provider") or raw.get("source") or raw.get("Source") or "primary")
        event["country"] = _country_code(event.get("country"))
        event["unit"] = raw.get("unit") or raw.get("Unit") or raw.get("currency") or raw.get("Currency") or None
        key = _event_key(event)
        by_key[key] = _merge_event(by_key.get(key), event)
    rows = list(by_key.values())
    rows.sort(key=lambda e: _parse_dt(e.get("scheduled_at")) or _now_utc())
    return rows[:MAX_EVENTS]


class EconomicCalendarProvider:
    """Multi-source, GET-only economic calendar provider.

    Source order:
      1) Existing TradePilot/Xoomar feed (no extra key)
      2) Trading Economics when TRADEPILOT_TRADING_ECONOMICS_KEY is configured
      3) Optional custom GET JSON URLs via TRADEPILOT_ECONOMIC_CALENDAR_URLS

    Missing values are enriched field-by-field. Contradictory/missing data never
    increases trading aggression; the MacroRiskEngine remains fail-closed.
    """

    def __init__(self, app_dir: Path, session: requests.Session | None = None):
        self.app_dir = Path(app_dir)
        self.data_dir = self.app_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.data_dir / "economic_calendar_cache.json"
        self.session = session or requests.Session()

    @staticmethod
    def _extract_payload(payload) -> list[dict]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("data", "events", "calendar", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        flattened: list[dict] = []
        for value in payload.values():
            if isinstance(value, list):
                flattened.extend(x for x in value if isinstance(x, dict))
        return flattened

    def _primary_urls(self) -> list[str]:
        urls = [ECONOMIC_CALENDAR_URL]
        extra = os.getenv("TRADEPILOT_ECONOMIC_CALENDAR_URLS", "").strip()
        if extra:
            urls.extend(x.strip() for x in extra.split(";") if x.strip())
        out = []
        for u in urls:
            if u and u not in out:
                out.append(u)
        return out

    def _fetch_primary(self, params: dict) -> tuple[list[dict], list[str]]:
        rows_all, errors = [], []
        for idx, url in enumerate(self._primary_urls()):
            label = "xoomar" if idx == 0 else f"custom-{idx}"
            try:
                r = self.session.get(url, params=params, timeout=12, headers={"User-Agent": "TradePilot/0.17.2"})
                r.raise_for_status()
                rows = self._extract_payload(r.json())
                for row in rows:
                    row = dict(row); row["_provider"] = label; rows_all.append(row)
            except Exception as exc:
                errors.append(f"{label}: {exc}")
        return rows_all, errors

    def _fetch_tradingeconomics(self, start: str, end: str) -> tuple[list[dict], list[str]]:
        key = os.getenv("TRADEPILOT_TRADING_ECONOMICS_KEY", "").strip()
        if not key:
            return [], ["tradingeconomics: not-configured"]
        countries = os.getenv("TRADEPILOT_TRADING_ECONOMICS_COUNTRIES", DEFAULT_TE_COUNTRIES).strip()
        country_path = quote(countries, safe=",")
        url = f"{TE_API_ROOT}/calendar/country/{country_path}/{start}/{end}"
        try:
            r = self.session.get(url, params={"c": key, "f": "json", "values": "true"}, timeout=15, headers={"User-Agent": "TradePilot/0.17.2"})
            r.raise_for_status()
            rows = self._extract_payload(r.json())
            out = []
            for row in rows:
                row = dict(row)
                row["_provider"] = "tradingeconomics"
                # Prefer numeric values if the account role returns them; otherwise strings remain usable.
                if row.get("ForecastValue") is not None: row.setdefault("forecast", row.get("ForecastValue"))
                if row.get("PreviousValue") is not None: row.setdefault("previous", row.get("PreviousValue"))
                if row.get("ActualValue") is not None: row.setdefault("actual", row.get("ActualValue"))
                out.append(row)
            return out, []
        except Exception as exc:
            return [], [f"tradingeconomics: {exc}"]

    def _write_cache(self, events: list[dict], source: str, provider_status: dict) -> None:
        tmp = self.cache_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({
            "updated_at": _now_utc().isoformat(), "source": source,
            "provider_status": provider_status, "events": events,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.cache_file)

    def load_cache(self, max_age_minutes: int = EVENT_CACHE_MAX_MINUTES) -> tuple[list[dict], dict]:
        try:
            raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
            ts = _parse_dt(raw.get("updated_at"))
            if not ts:
                return [], {"ok": False, "stale": True, "reason": "Cache ohne Zeitstempel"}
            age = (_now_utc() - ts).total_seconds() / 60.0
            events = normalize_dedupe_sort(raw.get("events") or [])
            return events, {
                "ok": bool(events), "stale": age > max_age_minutes,
                "age_minutes": round(age, 1), "source": raw.get("source") or "cache",
                "provider_status": raw.get("provider_status") or {},
                "updated_at": ts.isoformat(),
            }
        except Exception as exc:
            return [], {"ok": False, "stale": True, "reason": str(exc)}

    @staticmethod
    def _completeness(events: list[dict]) -> dict:
        if not events:
            return {"country": 0, "forecast": 0, "previous": 0, "actual_released": 0}
        now = _now_utc()
        released = [e for e in events if (_parse_dt(e.get("scheduled_at")) or now) <= now]
        pct = lambda n, d: int(round((100*n/d), 0)) if d else 0
        return {
            "country": pct(sum(_has(e.get("country")) and e.get("country") != "—" for e in events), len(events)),
            "forecast": pct(sum(_has(e.get("forecast")) for e in events), len(events)),
            "previous": pct(sum(_has(e.get("previous")) for e in events), len(events)),
            "actual_released": pct(sum(_has(e.get("actual")) for e in released), len(released)) if released else 100,
        }

    def fetch(self) -> tuple[list[dict], dict]:
        now = _now_utc()
        start = (now - timedelta(days=FETCH_LOOKBACK_DAYS)).date().isoformat()
        end = (now + timedelta(days=FETCH_AHEAD_DAYS)).date().isoformat()
        params = {"from": start, "to": end}

        primary, err_primary = self._fetch_primary(params)
        te_rows, err_te = self._fetch_tradingeconomics(start, end)
        raw_all = primary + te_rows
        events = normalize_dedupe_sort(raw_all)

        provider_status = {
            "xoomar/custom": {"rows": len(primary), "ok": bool(primary)},
            "tradingeconomics": {"rows": len(te_rows), "ok": bool(te_rows), "configured": bool(os.getenv("TRADEPILOT_TRADING_ECONOMICS_KEY", "").strip())},
        }
        errors = err_primary + err_te
        if events:
            completeness = self._completeness(events)
            self._write_cache(events, "multi-source-live", provider_status)
            return events, {
                "ok": True, "stale": False, "source": "multi-source-live",
                "providers": sum(1 for x in provider_status.values() if x.get("ok")),
                "provider_status": provider_status,
                "raw_count": len(raw_all), "event_count": len(events),
                "completeness": completeness, "errors": errors,
                "updated_at": now.isoformat(), "horizon_days": FETCH_AHEAD_DAYS,
            }

        cached, meta = self.load_cache()
        if cached and not meta.get("stale", True):
            return cached, {**meta, "ok": True, "source": "cache-fallback", "errors": errors,
                            "event_count": len(cached), "horizon_days": FETCH_AHEAD_DAYS,
                            "completeness": self._completeness(cached)}
        raise RuntimeError("Kalender live leer/fehlerhaft und kein frischer Cache verfügbar" + (": " + " | ".join(errors) if errors else ""))
