from __future__ import annotations
import json, time
from pathlib import Path

HANDOFF_TTL_SECONDS = 300

class SignalHandoffError(RuntimeError):
    pass

def handoff_path(app_dir: Path) -> Path:
    p=Path(app_dir)/'data'/'validated_real_handoff.json'
    p.parent.mkdir(parents=True,exist_ok=True)
    return p

def save_handoff(app_dir: Path, prepared: dict, signal: dict) -> dict:
    rec={
        'created': time.time(),
        'ttl_seconds': HANDOFF_TTL_SECONDS,
        'symbol': str(prepared['symbol']).upper(),
        'instrument_id': int(prepared['instrument_id']),
        'budget_eur': float(prepared['budget_eur']),
        'amount_usd': float(prepared['amount_usd']),
        'strategy': str(prepared.get('strategy') or 'DAY').upper(),
        'strategy_score': float(signal.get('score') or 0),
        'quality_score': float(signal.get('quality_score') or 0),
        'quality_confirmations': int(signal.get('quality_confirmations') or 0),
        'quality_checks': int(signal.get('quality_checks') or 5),
        'actionable': bool(signal.get('is_actionable')),
        'source': 'LIVE_END_TO_END_NO_POST',
    }
    tmp=handoff_path(app_dir).with_suffix('.tmp')
    tmp.write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding='utf-8')
    tmp.replace(handoff_path(app_dir))
    return rec

def load_handoff(app_dir: Path, require_fresh: bool=True) -> dict:
    p=handoff_path(app_dir)
    try: rec=json.loads(p.read_text(encoding='utf-8'))
    except Exception as exc: raise SignalHandoffError('Kein validiertes REAL-Signal vorhanden. Zuerst Test 31 ausführen.') from exc
    age=time.time()-float(rec.get('created',0))
    rec['age_seconds']=age
    if not rec.get('actionable'): raise SignalHandoffError('Gespeichertes Signal ist nicht ACTIONABLE.')
    if require_fresh and not (0 <= age <= HANDOFF_TTL_SECONDS):
        raise SignalHandoffError(f'Validiertes Signal ist abgelaufen ({age:.0f}s alt, max. {HANDOFF_TTL_SECONDS}s). Test 31 erneut ausführen.')
    if float(rec.get('budget_eur',999)) > 10.0: raise SignalHandoffError('Budget > 10 EUR blockiert.')
    return rec

def clear_handoff(app_dir: Path) -> None:
    handoff_path(app_dir).unlink(missing_ok=True)
