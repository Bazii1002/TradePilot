from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from economic_calendar_feed import EconomicCalendarProvider
from macro_logic import (
    CACHE_MAX_MINUTES, MARKET_TICKERS,
    _now_utc, _parse_dt, compute_macro_snapshot,
    economic_surprise, market_regime_from_moves,
)


class MacroRiskEngine(QObject):
    changed = Signal()
    refreshFinished = Signal(object, str, object)

    def __init__(self, app_dir: Path):
        super().__init__()
        self.app_dir = Path(app_dir)
        self.data_dir = self.app_dir / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.data_dir / 'macro_snapshot.json'
        self.calendar_provider = EconomicCalendarProvider(self.app_dir)
        self._busy = False
        self._last_error = ''
        self._last_update = 'Noch nicht aktualisiert'
        self._feed_status = 'Kalender noch nicht geladen'
        self._snapshot = compute_macro_snapshot([], data_ok=False)
        self.refreshFinished.connect(self._apply_refresh)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refreshNow)
        self.timer.start(5 * 60 * 1000)
        self._load_cache()
        QTimer.singleShot(700, self.refreshNow)

    def _load_cache(self):
        try:
            p = json.loads(self.cache_file.read_text(encoding='utf-8'))
            ts = _parse_dt(p.get('updated_at'))
            if ts and (_now_utc() - ts).total_seconds() <= CACHE_MAX_MINUTES * 60:
                self._snapshot = p.get('snapshot') or self._snapshot
                self._last_update = 'Cache · ' + ts.astimezone().strftime('%H:%M:%S')
                self._feed_status = 'Snapshot-Cache aktiv'
        except Exception:
            pass

    def _fetch_events(self) -> list[dict]:
        # Compatibility hook for existing diagnostics.
        events, _meta = self.calendar_provider.fetch()
        return events

    def _fetch_calendar(self) -> tuple[list[dict], dict]:
        return self.calendar_provider.fetch()

    def _fetch_market_reaction(self) -> dict:
        import yfinance as yf
        moves: dict[str, float | None] = {}
        for label, ticker in MARKET_TICKERS.items():
            try:
                df = yf.download(ticker, period='2d', interval='5m', progress=False, auto_adjust=False, threads=False)
                if df is None or df.empty or len(df) < 2:
                    moves[label] = None; continue
                closes = df['Close'].dropna()
                if hasattr(closes, 'columns'):
                    closes = closes.iloc[:, 0]
                if len(closes) < 2:
                    moves[label] = None; continue
                end = float(closes.iloc[-1]); start = float(closes.iloc[max(0, len(closes) - 7)])
                moves[label] = round((end - start) * 100.0, 2) if label == 'US10Y' else round((end / start - 1.0) * 100.0, 2)
            except Exception:
                moves[label] = None
        regime = market_regime_from_moves(moves)
        return {'moves': moves, **regime}

    @Slot()
    def refreshNow(self):
        if self._busy:
            return
        self._busy = True
        self.changed.emit()

        def worker():
            try:
                events, feed_meta = self._fetch_calendar()
                market = self._fetch_market_reaction()
                if not events:
                    raise RuntimeError('Kalender liefert keine verwertbaren Events')
                # stale calendar data can never unlock more aggression
                data_ok = bool(events) and not bool(feed_meta.get('stale', False))
                snap = compute_macro_snapshot(events, market=market, data_ok=data_ok)
                snap['calendar_meta'] = feed_meta
                self.refreshFinished.emit(snap, '' if data_ok else 'Kalenderdaten veraltet → fail-closed', feed_meta)
            except Exception as exc:
                safe = compute_macro_snapshot(
                    list(self._snapshot.get('upcoming') or []),
                    market={'moves': {}, 'regime': 'NEUTRAL', 'confidence': 0, 'complete': False},
                    data_ok=False,
                )
                self.refreshFinished.emit(safe, str(exc), {'ok': False, 'stale': True, 'source': 'none'})

        threading.Thread(target=worker, daemon=True, name='macro-risk-refresh').start()

    @Slot(object, str, object)
    def _apply_refresh(self, snap, error, feed_meta):
        self._busy = False
        self._snapshot = dict(snap or {})
        self._last_error = error or ''
        meta = dict(feed_meta or {})
        src = meta.get('source', 'unknown')
        count = int(meta.get('event_count', len(self._snapshot.get('upcoming') or [])))
        horizon = meta.get('horizon_days', 14)
        self._feed_status = f'{src} · {count} Events · {horizon} Tage' + (' · STALE' if meta.get('stale') else '')
        self._last_update = datetime.now().strftime('%H:%M:%S') + (' · FAIL-CLOSED' if error else '')
        try:
            tmp = self.cache_file.with_suffix('.tmp')
            tmp.write_text(json.dumps({'updated_at': _now_utc().isoformat(), 'snapshot': self._snapshot}, ensure_ascii=False, indent=2), encoding='utf-8')
            tmp.replace(self.cache_file)
        except Exception:
            pass
        # Faster polling around a release so Actual can be picked up quickly.
        near = False
        for e in list(self._snapshot.get('upcoming') or []) + list(self._snapshot.get('recent') or []):
            mins = e.get('minutes_to_event')
            if mins is not None and -20 <= float(mins) <= 10:
                near = True; break
        self.timer.setInterval(60 * 1000 if near else 5 * 60 * 1000)
        self.changed.emit()

    def gate(self) -> dict:
        return {
            'allow_new_trade': bool(self._snapshot.get('allow_new_trade', False)),
            'position_multiplier': float(self._snapshot.get('position_multiplier', 0.0)),
            'risk': str(self._snapshot.get('risk', 'HIGH')),
            'regime': str(self._snapshot.get('regime', 'NEUTRAL')),
            'reason': str(self._snapshot.get('reason', 'Makrodaten unklar')),
        }

    @Property(bool, notify=changed)
    def busy(self): return self._busy
    @Property(str, notify=changed)
    def risk(self): return str(self._snapshot.get('risk', 'HIGH'))
    @Property(str, notify=changed)
    def regime(self): return str(self._snapshot.get('regime', 'NEUTRAL'))
    @Property(int, notify=changed)
    def confidence(self): return int(self._snapshot.get('confidence', 0))
    @Property(bool, notify=changed)
    def allowNewTrade(self): return bool(self._snapshot.get('allow_new_trade', False))
    @Property(str, notify=changed)
    def positionMultiplierText(self): return f"{float(self._snapshot.get('position_multiplier',0))*100:.0f}%"
    @Property(str, notify=changed)
    def reasonText(self): return str(self._snapshot.get('reason', '—'))
    @Property(str, notify=changed)
    def lastUpdateText(self): return self._last_update
    @Property(str, notify=changed)
    def lastErrorText(self): return self._last_error
    @Property(str, notify=changed)
    def feedStatusText(self): return self._feed_status
    @Property(int, notify=changed)
    def upcomingEventCount(self): return len(self._snapshot.get('upcoming') or [])
    @Property(str, notify=changed)
    def nextEventText(self):
        e = self._snapshot.get('next_event')
        if not e: return 'Kein nächstes Event · Datenlage konservativ'
        mins = e.get('minutes_to_event')
        when = f'in {int(round(mins))} Min.' if mins is not None and mins >= 0 else 'veröffentlicht'
        return f"{e.get('event_name','—')} · {e.get('relevance','—')} · {when}"
    @Property(str, notify=changed)
    def botImpactText(self):
        if not self._snapshot.get('data_ok', False): return 'Neue Trades blockiert · Daten unsicher (fail-closed)'
        if not self.allowNewTrade: return 'Neue Trades pausiert · bestehende Positionen nur überwachen'
        mult = float(self._snapshot.get('position_multiplier', 1.0))
        if mult < 1.0: return f'Neue Trades erlaubt · Positionsgröße auf {mult*100:.0f}% reduziert'
        return 'Neue Trades normal · bestehende Positionen unverändert überwacht'
    @Property(str, notify=changed)
    def eventsJson(self):
        rows = []
        # upcoming first, then recently released. This mirrors the eToro-like "upcoming" view.
        all_events = list(self._snapshot.get('upcoming') or []) + list(self._snapshot.get('recent') or [])
        for e in all_events[:80]:
            dt = _parse_dt(e.get('scheduled_at')); local = dt.astimezone() if dt else None
            mins = e.get('minutes_to_event')
            if mins is None: countdown = '—'
            elif mins >= 1440: countdown = f'in {int(mins//1440)}T {int((mins%1440)//60)}h'
            elif mins >= 60: countdown = f'in {int(mins//60)}h {int(mins%60)}m'
            elif mins >= 0: countdown = f'in {max(0,int(round(mins)))} Min.'
            else: countdown = f'vor {abs(int(round(mins)))} Min.'
            surprise = e.get('surprise') or economic_surprise(e)
            rows.append({**e,
                'date_text': local.strftime('%d.%m.') if local else '—',
                'time_text': local.strftime('%H:%M') if local else '—',
                'countdown': countdown,
                'forecast_text': '—' if e.get('forecast') is None else str(e.get('forecast')),
                'previous_text': '—' if e.get('previous') is None else str(e.get('previous')),
                'actual_text': '—' if e.get('actual') is None else str(e.get('actual')),
                'surprise_text': surprise.get('text', '—'),
                'surprise_direction': surprise.get('direction', 'UNKNOWN'),
            })
        return json.dumps(rows, ensure_ascii=False)
    @Property(str, notify=changed)
    def marketMovesJson(self): return json.dumps((self._snapshot.get('market') or {}).get('moves') or {}, ensure_ascii=False)
