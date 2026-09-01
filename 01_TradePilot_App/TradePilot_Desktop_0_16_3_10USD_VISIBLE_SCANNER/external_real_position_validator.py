from __future__ import annotations
import json, time
from datetime import datetime
from pathlib import Path
from typing import Any

from real_execution import RealExecutionManager, _position_id, _instrument_id, _pick
from production_real_core import ProductionRealCore, RealExitEngine

class ExternalValidationError(RuntimeError):
    pass

def _number(row: dict, *names: str):
    for n in names:
        if row.get(n) is not None:
            try: return float(row[n])
            except Exception: pass
    return None

def _text(row: dict, *names: str):
    for n in names:
        if row.get(n) is not None and str(row[n]).strip():
            return str(row[n]).strip()
    return ''

def normalize_external_position(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ExternalValidationError('Ungültige Broker-Position')
    pid=_position_id(row)
    iid=_instrument_id(row)
    symbol=_text(row,'symbol','ticker','instrumentSymbol','internalSymbol')
    if not symbol:
        symbol=f'#{iid}' if iid else 'POSITION'
    return {
        'position_id': pid,
        'instrument_id': iid,
        'symbol': symbol.upper(),
        'units': _number(row,'units','shares','quantity','amountUnits'),
        'invested': _number(row,'investedAmount','investment','invested','amount'),
        'current_value': _number(row,'currentValue','marketValue','positionValue','value'),
        'pnl': _number(row,'pnl','profitLoss','profit','unrealizedPnl','openPnl'),
        'open_rate': _number(row,'openRate','openPrice','averageOpenPrice','price'),
        'raw_keys': sorted(str(k) for k in row.keys()),
    }

class ExternalRealPositionValidator:
    """0.16.2 read-only observer for a position opened by the user at the broker.

    It NEVER adopts the position into the production execution state and NEVER sends POST.
    """
    def __init__(self, app_dir: Path):
        self.app_dir=Path(app_dir)
        self.real=RealExecutionManager(self.app_dir)
        self.core=ProductionRealCore(self.app_dir)
        self.path=self.app_dir/'data'/'external_real_position_validation.json'

    def broker_positions(self) -> list[dict[str,Any]]:
        return self.real.position_rows()

    def observe(self) -> dict[str,Any]:
        before=self.core.machine.snapshot()
        rows=self.broker_positions()
        after=self.core.machine.snapshot()
        if before != after:
            raise ExternalValidationError('Read-only observer hat Production State verändert')
        normalized=[normalize_external_position(r) for r in rows]
        rec={
            'version':'0.16.2',
            'ts':datetime.now().astimezone().isoformat(),
            'mode':'EXTERNAL_OBSERVE_ONLY',
            'broker_positions':len(rows),
            'positions':normalized,
            'production_state':after.get('state','IDLE'),
            'production_state_unchanged':True,
            'broker_post_calls':0,
            'automatic_close':False,
        }
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
        return rec

    def restart_validation(self) -> dict[str,Any]:
        first=self.observe()
        # New instances simulate an application restart. No state mutation is allowed.
        second=ExternalRealPositionValidator(self.app_dir).observe()
        ids1=[p['position_id'] for p in first['positions']]
        ids2=[p['position_id'] for p in second['positions']]
        return {
            'ok': ids1==ids2,
            'before_ids':ids1,
            'after_ids':ids2,
            'production_state':second['production_state'],
            'post_retry':False,
            'broker_post_calls':0,
        }

    def exit_preview(self, position: dict[str,Any], market_row: dict[str,Any]|None=None) -> dict[str,Any]:
        # External positions are not automatically managed. We can only calculate/display a preview.
        # If no compatible market row is supplied, no synthetic prices are invented.
        if market_row is None:
            return {'available':False,'close':False,'reason':'MARKET_DATA_REQUIRED','broker_post_calls':0,'observe_only':True}
        shadow={
            'entry_price': position.get('open_rate'),
            'level':2,
            'symbol':position.get('symbol'),
        }
        if shadow['entry_price'] is None:
            return {'available':False,'close':False,'reason':'OPEN_PRICE_NOT_AVAILABLE','broker_post_calls':0,'observe_only':True}
        out=RealExitEngine.decision(shadow,market_row)
        return {**out,'available':True,'broker_post_calls':0,'observe_only':True}
