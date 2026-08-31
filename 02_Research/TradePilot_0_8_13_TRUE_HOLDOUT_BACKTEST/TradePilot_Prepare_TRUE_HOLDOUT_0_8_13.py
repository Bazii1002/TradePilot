from __future__ import annotations
import hashlib, json, re, sys, time, pickle
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import yfinance as yf

VERSION='0.8.13 TRUE HOLDOUT PREPARE'
DATA=Path(r'C:\TradePilot\03_Research_Data')
LOCK=Path(r'C:\TradePilot\02_Research\TradePilot_0_8_11_TRUE_HOLDOUT_LOCK')
HOLDOUT=DATA/'TradePilot_True_Holdout_Universe_0.8.12.1.csv'
SEEN=LOCK/'TradePilot_0_8_11_SEEN_SYMBOLS.csv'
LOCKJSON=LOCK/'TradePilot_0_8_11_HOLDOUT_LOCK.json'
EXPECTED_HOLDOUT='34b38c903865506f8cfb1d80560a6717abf9b33c73ed8c6a2432c52e16fc310c'
EXPECTED_SEEN='b2c9a68966b9c538d9b46c2d79768ba197e375c730867de2b7ae25d3a35ee722'
EXPECTED_COUNT=494
META_CACHE=DATA/'holdout_cache_0_8_13'/'classification'

def norm(s): return str(s).strip().upper().replace('.', '-')
def sha_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def validate():
    for p in [HOLDOUT,SEEN,LOCKJSON]:
        if not p.exists(): raise FileNotFoundError(f'Pflichtdatei fehlt: {p}')
    hh=sha_file(HOLDOUT)
    if hh!=EXPECTED_HOLDOUT: raise RuntimeError(f'HOLDOUT-HASH ABWEICHEND\nErwartet: {EXPECTED_HOLDOUT}\nGefunden: {hh}')
    h=pd.read_csv(HOLDOUT,encoding='utf-8-sig'); h.columns=[str(c).replace('\\ufeff','').strip() for c in h.columns]
    if 'Symbol' not in h.columns: raise KeyError(f'Symbol fehlt: {list(h.columns)}')
    h['Symbol']=h['Symbol'].map(norm); h=h.drop_duplicates('Symbol').reset_index(drop=True)
    s=pd.read_csv(SEEN,encoding='utf-8-sig'); s.columns=[str(c).replace('\\ufeff','').strip() for c in s.columns]
    sc='Symbol' if 'Symbol' in s.columns else s.columns[0]
    seen=sorted(set(norm(x) for x in s[sc].dropna()))
    sh=hashlib.sha256('\n'.join(seen).encode()).hexdigest()
    if len(seen)!=EXPECTED_COUNT or sh!=EXPECTED_SEEN: raise RuntimeError('0.8.11 Seen-Symbol-Lock stimmt nicht mehr.')
    ov=sorted(set(h.Symbol)&set(seen))
    if ov: raise RuntimeError(f'Overlap mit Seen Symbols: {len(ov)} | {ov[:20]}')
    return h,hh,sh

def model_from_info(info):
    sector=str(info.get('sector') or '').lower(); industry=str(info.get('industry') or '').lower()
    banks=['banks - diversified','banks - regional','regional banks','diversified banks','banking services']
    cap=['capital markets','investment banking','brokerage','financial data','financial exchanges','asset management']
    if any(x in industry for x in banks): return 'BANK'
    if 'financial services' in sector and any(x in industry for x in cap): return 'CAPITAL_MARKETS'
    if 'energy' in sector: return 'ENERGY'
    return 'STANDARD'

def cache_path(sym): return META_CACHE/f'{re.sub(r"[^A-Za-z0-9_.-]","_",sym)}.pkl'
def get_meta(sym):
    p=cache_path(sym)
    if p.exists():
        try:
            with open(p,'rb') as f: return pickle.load(f)
        except Exception: pass
    err=None
    for i in range(3):
        try:
            t=yf.Ticker(sym)
            try: info=t.get_info()
            except Exception: info=t.info
            if not isinstance(info,dict): info={}
            out={'sector':str(info.get('sector') or ''),'industry':str(info.get('industry') or '')}
            META_CACHE.mkdir(parents=True,exist_ok=True)
            with open(p,'wb') as f: pickle.dump(out,f)
            return out
        except Exception as e:
            err=e; time.sleep(1+i)
    raise err or RuntimeError('Metadaten nicht verfügbar')

def classify(h):
    fixed=[]; todo=[]
    for _,r in h.iterrows():
        sym=norm(r.Symbol); sec=str(r.get('Sector','') or '')
        sl=sec.lower()
        if sl=='energy': fixed.append((sym,'ENERGY',sec,'Index-Sektor'))
        elif sl in ('financials','financial services','finance') or not sl: todo.append((sym,sec))
        else: fixed.append((sym,'STANDARD',sec,'Index-Sektor'))
    print(f'Financial/unklare Titel für Yahoo-Industrieklassifikation: {len(todo)}')
    with ThreadPoolExecutor(max_workers=min(8,max(1,len(todo)))) as ex:
        fut={ex.submit(get_meta,s):(s,sec) for s,sec in todo}
        done=0
        for f in as_completed(fut):
            s,sec=fut[f]; done+=1
            try:
                info=f.result(); m=model_from_info(info); fixed.append((s,m,info.get('sector',''),info.get('industry','')))
                print(f'  [{done:03}/{len(todo)}] {s:<7} -> {m:<15} | {info.get("industry","")}')
            except Exception as e:
                fixed.append((s,'STANDARD',sec,f'METADATA_FEHLER: {e}'))
                print(f'  [{done:03}/{len(todo)}] {s:<7} -> STANDARD fallback')
    return pd.DataFrame(fixed,columns=['Symbol','Modell','Sector_Metadata','Industry_Metadata']).drop_duplicates('Symbol').sort_values('Symbol')

def write_universe(cls,here):
    models=['STANDARD','BANK','CAPITAL_MARKETS','ENERGY']
    d={m:cls.loc[cls.Modell==m,'Symbol'].tolist() for m in models}
    py='UNIVERSES = '+repr({'holdout':d})+'\n\ndef universe_count(u):\n    return sum(len(v) for v in u.values())\n'
    (here/'universe_large.py').write_text(py,encoding='utf-8')
    cls.to_csv(here/'TradePilot_Holdout_Classification_0.8.13.csv',index=False,encoding='utf-8-sig')
    return d

def main():
    here=Path(__file__).resolve().parent
    print('='*112); print('TRADEPILOT 0.8.13 TRUE HOLDOUT PREPARE'); print('='*112)
    h,hh,sh=validate(); print(f'Holdout: {len(h)} | Hash OK | Overlap 0 | Seen-Lock {EXPECTED_COUNT} OK')
    cls=classify(h); d=write_universe(cls,here)
    print('Modellmix: '+' | '.join(f'{k}={len(v)}' for k,v in d.items()))
    audit={'version':'0.8.13','holdout_hash':hh,'seen_hash':sh,'holdout_symbols':len(h),'model_mix':{k:len(v) for k,v in d.items()},'rule_blind_classification':True}
    (here/'TradePilot_Holdout_Prepare_Audit_0.8.13.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('universe_large.py erzeugt. Vorbereitung OK.')
if __name__=='__main__': main()
