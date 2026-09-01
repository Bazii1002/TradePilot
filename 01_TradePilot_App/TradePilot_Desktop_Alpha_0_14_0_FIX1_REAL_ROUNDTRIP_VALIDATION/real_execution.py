from __future__ import annotations
import json, os, time, uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import requests
from etoro_live_manual import EtoroManualLiveBroker, MAX_LIVE_EUR

OPEN_URL_REAL = "https://public-api.etoro.com/api/v2/trading/execution/orders"
PORTFOLIO_URL_REAL = "https://public-api.etoro.com/api/v1/trading/info/portfolio"
ARM_TTL_SECONDS = 600

class RealExecutionError(RuntimeError): pass

def _read_env(path: Path):
    out={}
    if not path.exists(): return out
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1); out[k.strip()]=v.strip().strip('"').strip("'")
    return out

def _pick(d,*names):
    for n in names:
        if isinstance(d,dict) and d.get(n) is not None: return d[n]
    return None

def _portfolio_root(payload):
    if not isinstance(payload,dict): return {}
    if isinstance(payload.get('clientPortfolio'),dict): return payload['clientPortfolio']
    if isinstance(payload.get('data'),dict): return payload['data']
    return payload

def _positions(payload):
    root=_portfolio_root(payload)
    for key in ('positions','openPositions','open_positions'):
        rows=root.get(key)
        if isinstance(rows,list): return [r for r in rows if isinstance(r,dict)]
    return []

def _position_id(row):
    x=_pick(row,'positionId','positionID','PositionId','id'); return '' if x is None else str(x)

def _instrument_id(row):
    x=_pick(row,'instrumentId','instrumentID','InstrumentId','marketId')
    try: x=int(x); return x if x>0 else None
    except: return None

def _response_ids(payload):
    roots=[]
    if isinstance(payload,dict):
        roots=[payload]
        if isinstance(payload.get('data'),dict): roots.append(payload['data'])
    def one(*names):
        for r in roots:
            x=_pick(r,*names)
            if x is not None: return str(x)
        return ''
    return {'order_id':one('orderId','orderID'),'position_id':one('positionId','positionID'),'token':one('token'),'reference_id':one('referenceId','referenceID')}

@dataclass(frozen=True)
class SafetyConfig:
    enabled: bool; auto_enabled: bool; max_trade_eur: float; max_open_positions: int; max_daily_loss_eur: float

class RealExecutionManager:
    """0.14.0 manual REAL validation transport. Fail closed, no automatic POST retry."""
    def __init__(self,app_dir:Path,timeout:float=20.0):
        self.app_dir=Path(app_dir); self.data_dir=self.app_dir/'data'; self.data_dir.mkdir(parents=True,exist_ok=True)
        self.central_env=self.app_dir.parent.parent/'.env'; self.local_env=self.app_dir/'.env'; self.timeout=float(timeout)
        self.session=requests.Session(); self.manual=EtoroManualLiveBroker(self.app_dir,timeout=self.timeout)
        self.log_path=self.data_dir/'real_execution.jsonl'; self.uncertain_lock=self.data_dir/'REAL_EXECUTION_UNCERTAIN.json'
        self.kill_switch=self.data_dir/'REAL_KILL_SWITCH.lock'; self.position_state=self.data_dir/'real_positions_state.json'
        self.arm_file=self.data_dir/'REAL_EXECUTION_ARM.json'
    def _env(self):
        e={}; e.update(_read_env(self.central_env)); e.update(_read_env(self.local_env))
        for k in ('TRADEPILOT_REAL_EXECUTION_ENABLED','TRADEPILOT_REAL_AUTOTRADING_ENABLED','TRADEPILOT_MAX_REAL_TRADE_EUR','TRADEPILOT_MAX_REAL_POSITIONS','TRADEPILOT_MAX_DAILY_LOSS_EUR'):
            if os.getenv(k): e[k]=os.getenv(k,'')
        return e
    def config(self):
        e=self._env(); yes=lambda n:e.get(n,'').strip().upper() in {'YES','TRUE','1','ON'}
        try: mt=min(MAX_LIVE_EUR,float(e.get('TRADEPILOT_MAX_REAL_TRADE_EUR',MAX_LIVE_EUR)))
        except: mt=MAX_LIVE_EUR
        try: mp=max(1,min(1,int(e.get('TRADEPILOT_MAX_REAL_POSITIONS','1'))))
        except: mp=1
        try: ml=max(1.0,min(20.0,float(e.get('TRADEPILOT_MAX_DAILY_LOSS_EUR','20'))))
        except: ml=20.0
        return SafetyConfig(yes('TRADEPILOT_REAL_EXECUTION_ENABLED'),False,mt,mp,ml)
    def _headers(self,request_id=None):
        h=self.manual._headers(); h['x-request-id']=request_id or str(uuid.uuid4()); h['Content-Type']='application/json'; return h
    def _log(self,event,**fields):
        rec={'ts':datetime.now().astimezone().isoformat(),'event':event,**fields}
        with self.log_path.open('a',encoding='utf-8') as f:f.write(json.dumps(rec,ensure_ascii=False,separators=(',',':'))+'\n')
    def _decode(self,resp):
        try:p=resp.json()
        except:p=resp.text
        if not resp.ok:
            t=json.dumps(p,ensure_ascii=False) if isinstance(p,(dict,list)) else str(p)
            raise RealExecutionError(f'eToro API {resp.status_code}: {t[:700]}')
        return p
    def portfolio(self): return self._decode(self.session.get(PORTFOLIO_URL_REAL,headers=self._headers(),timeout=self.timeout))
    def position_rows(self): return _positions(self.portfolio())
    def safety_status(self):
        c=self.config()
        try: rows=self.position_rows(); ok=True; err=''
        except Exception as ex: rows=[];ok=False;err=str(ex)
        return {'execution_enabled':c.enabled,'auto_enabled':False,'max_trade_eur':c.max_trade_eur,'max_open_positions':c.max_open_positions,'max_daily_loss_eur':c.max_daily_loss_eur,'open_positions':len(rows) if ok else -1,'broker_ok':ok,'error':err,'kill_switch':self.kill_switch.exists(),'uncertain_lock':self.uncertain_lock.exists(),'armed':self.arm_status().get('armed',False)}
    def _assert_common(self):
        c=self.config()
        if not c.enabled: raise RealExecutionError('REAL execution ist standardmäßig LOCKED. TRADEPILOT_REAL_EXECUTION_ENABLED=YES fehlt.')
        if self.kill_switch.exists(): raise RealExecutionError('REAL Kill Switch ist aktiv.')
        if self.uncertain_lock.exists(): raise RealExecutionError('UNCERTAIN LOCK aktiv. Erst Reconcile.')
        return c
    def preflight_buy(self,symbol,budget_eur,strategy='MANUAL'):
        c=self.config(); budget_eur=float(budget_eur)
        if budget_eur<=0 or budget_eur>c.max_trade_eur or budget_eur>MAX_LIVE_EUR: raise RealExecutionError(f'Trade blockiert: maximal {c.max_trade_eur:.2f} EUR.')
        rows=self.position_rows()
        if len(rows)>=c.max_open_positions: raise RealExecutionError(f'Trade blockiert: {len(rows)} REAL-Position(en), Limit {c.max_open_positions}.')
        p=self.manual.prepare_market_buy(symbol,budget_eur); p['strategy']=str(strategy).upper(); p['leverage']=1
        self._log('PREFLIGHT_BUY',symbol=p['symbol'],instrument_id=p['instrument_id'],budget_eur=p['budget_eur'])
        return p
    def arm_buy(self,prepared):
        token=str(uuid.uuid4()); rec={'kind':'BUY','token':token,'created':time.time(),'symbol':prepared['symbol'],'instrument_id':int(prepared['instrument_id']),'budget_eur':float(prepared['budget_eur']),'amount_usd':float(prepared['amount_usd'])}
        self.arm_file.write_text(json.dumps(rec,indent=2),encoding='utf-8'); self._log('ARM_BUY',symbol=rec['symbol'],budget_eur=rec['budget_eur']); return rec
    def arm_close(self,position_id):
        rows=self.position_rows(); row=next((r for r in rows if _position_id(r)==str(position_id)),None)
        if not row: raise RealExecutionError('Position-ID ist im aktuellen REAL-Portfolio nicht offen.')
        token=str(uuid.uuid4()); rec={'kind':'CLOSE','token':token,'created':time.time(),'position_id':str(position_id),'instrument_id':_instrument_id(row)}
        self.arm_file.write_text(json.dumps(rec,indent=2),encoding='utf-8'); self._log('ARM_CLOSE',position_id=str(position_id)); return rec
    def arm_status(self):
        try:r=json.loads(self.arm_file.read_text(encoding='utf-8'))
        except:return {'armed':False}
        age=time.time()-float(r.get('created',0)); return {**r,'armed':0<=age<=ARM_TTL_SECONDS,'age_seconds':age}
    def _consume_arm(self,kind,**match):
        s=self.arm_status()
        if not s.get('armed') or s.get('kind')!=kind: raise RealExecutionError('Kein gültiges ARM-Fenster (max. 10 Minuten).')
        for k,v in match.items():
            if str(s.get(k))!=str(v): raise RealExecutionError(f'ARM stimmt nicht mit {k} überein.')
        self.arm_file.unlink(missing_ok=True); return s
    def _confirm_position(self,position_id='',instrument_id=None,attempts=4):
        for i in range(attempts):
            for r in self.position_rows():
                if position_id and _position_id(r)==str(position_id): return r
                if not position_id and instrument_id is not None and _instrument_id(r)==instrument_id:return r
            if i<attempts-1: time.sleep(1.5)
        return None
    def execute_buy(self,prepared,confirmation,auto=False):
        if auto: raise RealExecutionError('REAL AutoTrading bleibt in 0.14.0 hart gesperrt.')
        self._assert_common()
        symbol=str(prepared['symbol']).upper(); eur=float(prepared['budget_eur']); iid=int(prepared['instrument_id'])
        expected=f'EXECUTE REAL BUY {symbol} {eur:.2f} EUR'
        if confirmation.strip()!=expected: raise RealExecutionError(f'Bestätigung falsch. Erwartet exakt: {expected}')
        self._consume_arm('BUY',symbol=symbol,instrument_id=iid,budget_eur=eur)
        payload={'action':'open','transaction':'buy','instrumentId':iid,'orderType':'mkt','amount':float(prepared['amount_usd']),'orderCurrency':'usd','leverage':1}
        rid=str(uuid.uuid4()); self._log('REAL_BUY_POST_ATTEMPT',request_id=rid,symbol=symbol,instrument_id=iid,budget_eur=eur)
        try:
            resp=self.session.post(OPEN_URL_REAL,headers=self._headers(rid),json=payload,timeout=self.timeout); body=self._decode(resp)
        except Exception as ex:
            self.uncertain_lock.write_text(json.dumps({'kind':'BUY','ts':time.time(),'instrument_id':iid,'symbol':symbol,'request_id':rid,'reason':str(ex)},indent=2),encoding='utf-8'); self._log('REAL_BUY_UNCERTAIN',request_id=rid,error=str(ex)); raise
        ids=_response_ids(body); row=self._confirm_position(position_id=ids['position_id'],instrument_id=iid)
        if row is None:
            self.uncertain_lock.write_text(json.dumps({'kind':'BUY','ts':time.time(),'instrument_id':iid,'symbol':symbol,'request_id':rid,'response_ids':ids,'reason':'POST succeeded but portfolio confirmation missing'},indent=2),encoding='utf-8'); raise RealExecutionError('BUY Antwort erhalten, aber Position nicht verifiziert. UNCERTAIN LOCK gesetzt.')
        pid=_position_id(row); self._write_position_state({'status':'CONFIRMED_REAL','symbol':symbol,'instrument_id':iid,'position_id':pid,'budget_eur':eur,'amount_usd':float(prepared['amount_usd']),'request_id':rid,'order_id':ids['order_id'],'strategy':prepared.get('strategy','MANUAL')})
        self._log('REAL_BUY_CONFIRMED',position_id=pid,request_id=rid,order_id=ids['order_id']); return {'ok':True,'position_id':pid,'request_id':rid,'order_id':ids['order_id'],'response':body}
    def close_position(self,position_id,confirmation,auto=False):
        if auto: raise RealExecutionError('REAL AutoTrading bleibt in 0.14.0 hart gesperrt.')
        self._assert_common(); pid=str(position_id)
        expected=f'EXECUTE REAL CLOSE {pid}'
        if confirmation.strip()!=expected: raise RealExecutionError(f'Bestätigung falsch. Erwartet exakt: {expected}')
        arm=self._consume_arm('CLOSE',position_id=pid); iid=arm.get('instrument_id')
        # Current eToro v2 unified order API supports action=open/close and closes by positionId.
        payload={'action':'close','positionId':pid,'orderType':'mkt'}
        rid=str(uuid.uuid4()); self._log('REAL_CLOSE_POST_ATTEMPT',request_id=rid,position_id=pid)
        try:
            resp=self.session.post(OPEN_URL_REAL,headers=self._headers(rid),json=payload,timeout=self.timeout); body=self._decode(resp)
        except Exception as ex:
            self.uncertain_lock.write_text(json.dumps({'kind':'CLOSE','ts':time.time(),'position_id':pid,'request_id':rid,'reason':str(ex)},indent=2),encoding='utf-8'); self._log('REAL_CLOSE_UNCERTAIN',request_id=rid,error=str(ex)); raise
        # Verify CLOSED by absence from portfolio; never retry POST.
        still=self._confirm_position(position_id=pid,attempts=4)
        if still is not None:
            self.uncertain_lock.write_text(json.dumps({'kind':'CLOSE','ts':time.time(),'position_id':pid,'request_id':rid,'reason':'POST succeeded but position still visible'},indent=2),encoding='utf-8'); raise RealExecutionError('CLOSE Antwort erhalten, Position aber noch sichtbar. UNCERTAIN LOCK gesetzt.')
        st=self.load_position_state(); st.pop(pid,None); self._save_state(st); self._log('REAL_CLOSE_CONFIRMED',position_id=pid,request_id=rid); return {'ok':True,'position_id':pid,'request_id':rid,'response':body}
    def _save_state(self,state):
        tmp=self.position_state.with_suffix('.tmp'); tmp.write_text(json.dumps(state,indent=2),encoding='utf-8'); tmp.replace(self.position_state)
    def _write_position_state(self,entry):
        st=self.load_position_state(); pid=str(entry.get('position_id') or '')
        if pid: st[pid]={**entry,'saved_at':time.time()}; self._save_state(st)
    def load_position_state(self):
        try:r=json.loads(self.position_state.read_text(encoding='utf-8')); return r if isinstance(r,dict) else {}
        except:return {}
    def reconcile(self,clear_uncertain_if_safe=False):
        rows=self.position_rows(); broker_ids={_position_id(r) for r in rows if _position_id(r)}; local_ids=set(self.load_position_state())
        uncertain=None
        if self.uncertain_lock.exists():
            try:uncertain=json.loads(self.uncertain_lock.read_text(encoding='utf-8'))
            except:uncertain={'reason':'unreadable'}
        safe=False
        if uncertain:
            if uncertain.get('kind')=='BUY':
                iid=uncertain.get('instrument_id'); safe=any(_instrument_id(r)==iid for r in rows) or not rows
            elif uncertain.get('kind')=='CLOSE': safe=str(uncertain.get('position_id')) not in broker_ids
        if clear_uncertain_if_safe and uncertain and safe:self.uncertain_lock.unlink(missing_ok=True); self._log('UNCERTAIN_LOCK_CLEARED_BY_RECONCILE')
        result={'broker_positions':len(rows),'broker_position_ids':sorted(broker_ids),'local_position_ids':sorted(local_ids),'orphan_broker':sorted(broker_ids-local_ids),'stale_local':sorted(local_ids-broker_ids),'uncertain_lock':bool(uncertain),'uncertain_safe_to_clear':safe}; self._log('RECONCILE',**result); return result
    def activate_kill_switch(self,reason='manual'): self.kill_switch.write_text(json.dumps({'ts':time.time(),'reason':reason},indent=2),encoding='utf-8'); self._log('KILL_SWITCH_ON',reason=reason)
    def clear_kill_switch(self): self.kill_switch.unlink(missing_ok=True); self._log('KILL_SWITCH_OFF')
