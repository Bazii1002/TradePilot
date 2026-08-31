from __future__ import annotations
from pathlib import Path
import math, sys
import pandas as pd

HERE=Path(__file__).resolve().parent
DATA=Path(r'C:\TradePilot\03_Research_Data')

def latest_raw():
    files=list(HERE.glob('TradePilot_Backtest_0.8.13_TRUE_HOLDOUT_RAW_*.csv'))
    if not files: files=list(HERE.glob('TradePilot_Backtest_0.8.13*.csv'))
    return max(files,key=lambda p:p.stat().st_mtime) if files else None

def episodes(df,gap=130):
    if df.empty:return df.copy()
    d=df.copy(); d['_d']=pd.to_datetime(d.Stichtag,errors='coerce'); out=[]
    for _,g in d.sort_values(['Symbol','_d']).groupby('Symbol',sort=False):
        keep=[]; last=None
        for idx,r in g.iterrows():
            if last is None or (r._d-last).days>gap: keep.append(idx)
            last=r._d
        out.append(g.loc[keep].drop(columns=['_d']))
    return pd.concat(out,ignore_index=True) if out else d.iloc[:0]

def met(df):
    d=df.copy()
    for c in ['Rendite_12M','Alpha_12M','Sektor_Alpha_12M']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d[d.Rendite_12M.notna() & d.Alpha_12M.notna()]
    if d.empty:return dict(n=0,Aktien=0,Episoden=0,Median=None,Alpha=None,SektorAlpha=None,EpisodenAlpha=None,AktienAlpha=None,Positiv=None,Minus20=None)
    ep=episodes(d); stock=d.groupby('Symbol').Alpha_12M.mean()
    return dict(n=len(d),Aktien=d.Symbol.nunique(),Episoden=len(ep),Median=float(d.Rendite_12M.median()),Alpha=float(d.Alpha_12M.median()),SektorAlpha=float(d.Sektor_Alpha_12M.median()),EpisodenAlpha=float(ep.Alpha_12M.median()),AktienAlpha=float(stock.median()),Positiv=float((d.Rendite_12M>0).mean()*100),Minus20=float((d.Rendite_12M<=-20).mean()*100))

def verdict(m):
    if m['n']>=20 and m['Aktien']>=10 and m['Episoden']>=10:
        if m['Alpha']>0 and m['EpisodenAlpha']>0 and m['AktienAlpha']>0 and m['Minus20']<=20:return 'PASS'
        return 'FAIL'
    if m['n']>=5 and m['Alpha'] is not None and m['Alpha']>0:return 'WATCH'
    return 'FAIL'

def run(path):
    x=pd.read_csv(path,encoding='utf-8-sig'); x.columns=[str(c).replace('\\ufeff','').strip() for c in x.columns]
    for c in ['Qualitaet','Entwicklung','Bewertung','Value_Trap','Drawdown_Score','Trend','B061_Unternehmensscore','B061_Einstiegsscore']:
        x[c]=pd.to_numeric(x[c],errors='coerce')
    tests=[
      ('ALL_MODEL_BASE',x,False),
      ('BASELINE_061_U70_E65',x[(x.B061_Unternehmensscore>=70)&(x.B061_Einstiegsscore>=65)],False),
      ('STD_MODEL_BASE',x[x.Modell=='STANDARD'],False),
      ('STD_BASELINE_061_U70_E65',x[(x.Modell=='STANDARD')&(x.B061_Unternehmensscore>=70)&(x.B061_Einstiegsscore>=65)],False),
      ('STD_RECOVERY_DD80_Bew0_54',x[(x.Modell=='STANDARD')&(x.Drawdown_Score>=80)&(x.Bewertung<=54)],True),
      ('BANK_BASELINE_ALL',x[x.Modell=='BANK'],True),
      ('BANK_TREND55_79',x[(x.Modell=='BANK')&(x.Trend>=55)&(x.Trend<=79)],True),
      ('CAP_MODEL_BASE',x[x.Modell=='CAPITAL_MARKETS'],False),
      ('CAP_TRAP20_59_DD40_59',x[(x.Modell=='CAPITAL_MARKETS')&(x.Value_Trap>=20)&(x.Value_Trap<=59)&(x.Drawdown_Score>=40)&(x.Drawdown_Score<=59)],True),
      ('CAP_Q55_69_DEV0_54',x[(x.Modell=='CAPITAL_MARKETS')&(x.Qualitaet>=55)&(x.Qualitaet<=69)&(x.Entwicklung<=54)],True),
      ('ENERGY_MODEL_BASE',x[x.Modell=='ENERGY'],False),
      ('ENERGY_BASELINE_061_U70_E65',x[(x.Modell=='ENERGY')&(x.B061_Unternehmensscore>=70)&(x.B061_Einstiegsscore>=65)],True),]
    rows=[]
    for name,d,cand in tests:
        m=met(d); rows.append({'Test':name,**m,'Verdict':verdict(m) if cand else 'REFERENCE'})
    r=pd.DataFrame(rows)
    def f(v):return '--' if v is None or pd.isna(v) else f'{v:+.1f}'
    print('\n'+'='*140);print('TRADEPILOT 0.8.13 TRUE HOLDOUT RESULTS');print('='*140)
    print(f"{'Test':34} {'n':>6} {'Akt':>5} {'Epis':>5} {'Med':>8} {'Alpha':>8} {'SektA':>8} {'EpA':>8} {'StkA':>8} {'Pos%':>7} {'<=-20':>7} {'Verdict':>10}")
    for _,q in r.iterrows():
        pos='--' if pd.isna(q.Positiv) else f'{q.Positiv:.1f}%'; loss='--' if pd.isna(q.Minus20) else f'{q.Minus20:.1f}%'
        print(f"{q.Test:<34} {int(q.n):6} {int(q.Aktien):5} {int(q.Episoden):5} {f(q.Median):>8} {f(q.Alpha):>8} {f(q.SektorAlpha):>8} {f(q.EpisodenAlpha):>8} {f(q.AktienAlpha):>8} {pos:>7} {loss:>7} {q.Verdict:>10}")
    print('\nPASS wurde VOR dem Holdout festgelegt: n>=20, >=10 Aktien, >=10 Episoden, Alpha/EpisodenAlpha/AktienAlpha >0, <=-20%-Quote <=20%.')
    print('WATCH: n>=5 und positiver Median-Alpha bei zu kleiner Stichprobe. FAIL: sonst. Forschungslabels, keine Handelsfreigabe.')
    stamp=pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')
    out=DATA/f'TradePilot_TRUE_HOLDOUT_Results_0.8.13_{stamp}.csv'; r.to_csv(out,index=False,encoding='utf-8-sig')
    obs=DATA/f'TradePilot_TRUE_HOLDOUT_Observations_0.8.13_{stamp}.csv'; x.to_csv(obs,index=False,encoding='utf-8-sig')
    print(f'\nHoldout-Ergebnis gespeichert: {out}'); print(f'Beobachtungen archiviert:    {obs}')
    return r

def main():
    p=latest_raw()
    if p is None: raise FileNotFoundError('Keine 0.8.13 Raw-Beobachtungs-CSV gefunden.')
    print(f'Quelle: {p}')
    run(p)
if __name__=='__main__':main()
