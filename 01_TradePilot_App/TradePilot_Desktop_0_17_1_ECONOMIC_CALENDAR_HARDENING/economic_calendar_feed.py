from __future__ import annotations

import json
import os
from datetime import timedelta
from pathlib import Path
from typing import Iterable

import requests

from macro_logic import ECONOMIC_CALENDAR_URL, _now_utc, _parse_dt, normalize_event

FETCH_LOOKBACK_DAYS = 1
FETCH_AHEAD_DAYS = 14
EVENT_CACHE_MAX_MINUTES = 180
MAX_EVENTS = 250


def _event_key(event: dict) -> tuple[str, str, str]:
    dt = _parse_dt(event.get('scheduled_at'))
    stamp = dt.isoformat() if dt else str(event.get('scheduled_at') or '')
    return (
        str(event.get('country') or '—').strip().upper(),
        str(event.get('event_name') or '—').strip().lower(),
        stamp,
    )


def normalize_dedupe_sort(raw_events: Iterable[dict]) -> list[dict]:
    by_key: dict[tuple[str, str, str], dict] = {}
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        event = normalize_event(raw)
        if not event:
            continue
        key = _event_key(event)
        # Prefer the richer duplicate (Actual/Forecast/Previous filled in).
        richness = sum(event.get(k) not in (None, '', '-', '—') for k in ('actual', 'forecast', 'previous'))
        old = by_key.get(key)
        old_richness = -1 if old is None else sum(old.get(k) not in (None, '', '-', '—') for k in ('actual', 'forecast', 'previous'))
        if old is None or richness >= old_richness:
            by_key[key] = event
    rows = list(by_key.values())
    rows.sort(key=lambda e: _parse_dt(e.get('scheduled_at')) or _now_utc())
    return rows[:MAX_EVENTS]


class EconomicCalendarProvider:
    """Pure-Python calendar provider. No QObject/QTimer dependency.

    This lets diagnostics run without creating a Qt event loop and is also the
    single normalization/deduplication point used by the desktop engine.
    """

    def __init__(self, app_dir: Path, session: requests.Session | None = None):
        self.app_dir = Path(app_dir)
        self.data_dir = self.app_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.data_dir / 'economic_calendar_cache.json'
        self.session = session or requests.Session()

    def _urls(self) -> list[str]:
        # Primary is the existing TradePilot provider. Optional extra GET-only
        # providers can be configured locally without changing trading code.
        urls = [ECONOMIC_CALENDAR_URL]
        extra = os.getenv('TRADEPILOT_ECONOMIC_CALENDAR_URLS', '').strip()
        if extra:
            urls.extend(x.strip() for x in extra.split(';') if x.strip())
        out: list[str] = []
        for url in urls:
            if url and url not in out:
                out.append(url)
        return out

    @staticmethod
    def _extract_payload(payload) -> list[dict]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ('data', 'events', 'calendar', 'results', 'items'):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        # Some APIs return date -> [events]
        flattened: list[dict] = []
        for value in payload.values():
            if isinstance(value, list):
                flattened.extend(x for x in value if isinstance(x, dict))
        return flattened

    def _write_cache(self, events: list[dict], source: str) -> None:
        tmp = self.cache_file.with_suffix('.tmp')
        tmp.write_text(json.dumps({
            'updated_at': _now_utc().isoformat(),
            'source': source,
            'events': events,
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.cache_file)

    def load_cache(self, max_age_minutes: int = EVENT_CACHE_MAX_MINUTES) -> tuple[list[dict], dict]:
        try:
            raw = json.loads(self.cache_file.read_text(encoding='utf-8'))
            ts = _parse_dt(raw.get('updated_at'))
            if not ts:
                return [], {'ok': False, 'stale': True, 'reason': 'Cache ohne Zeitstempel'}
            age = (_now_utc() - ts).total_seconds() / 60.0
            events = normalize_dedupe_sort(raw.get('events') or [])
            return events, {
                'ok': bool(events),
                'stale': age > max_age_minutes,
                'age_minutes': round(age, 1),
                'source': raw.get('source') or 'cache',
                'updated_at': ts.isoformat(),
            }
        except Exception as exc:
            return [], {'ok': False, 'stale': True, 'reason': str(exc)}

    def fetch(self) -> tuple[list[dict], dict]:
        now = _now_utc()
        params = {
            'from': (now - timedelta(days=FETCH_LOOKBACK_DAYS)).date().isoformat(),
            'to': (now + timedelta(days=FETCH_AHEAD_DAYS)).date().isoformat(),
        }
        raw_all: list[dict] = []
        errors: list[str] = []
        used: list[str] = []
        for url in self._urls():
            try:
                r = self.session.get(url, params=params, timeout=12, headers={'User-Agent': 'TradePilot/0.17.1'})
                r.raise_for_status()
                rows = self._extract_payload(r.json())
                if rows:
                    raw_all.extend(rows)
                    used.append(url)
            except Exception as exc:
                errors.append(f'{url}: {exc}')
        events = normalize_dedupe_sort(raw_all)
        if events:
            self._write_cache(events, ', '.join(used) or ECONOMIC_CALENDAR_URL)
            return events, {
                'ok': True,
                'stale': False,
                'source': 'live',
                'providers': len(used),
                'raw_count': len(raw_all),
                'event_count': len(events),
                'errors': errors,
                'updated_at': now.isoformat(),
                'horizon_days': FETCH_AHEAD_DAYS,
            }

        cached, meta = self.load_cache()
        if cached and not meta.get('stale', True):
            return cached, {
                **meta,
                'ok': True,
                'source': 'cache-fallback',
                'errors': errors,
                'event_count': len(cached),
                'horizon_days': FETCH_AHEAD_DAYS,
            }
        raise RuntimeError('Kalender live leer/fehlerhaft und kein frischer Cache verfügbar' + (': ' + ' | '.join(errors) if errors else ''))
