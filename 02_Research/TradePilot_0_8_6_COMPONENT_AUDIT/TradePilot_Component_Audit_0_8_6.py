from __future__ import annotations

import argparse
from pathlib import Path
import math
import pandas as pd
import numpy as np
from datetime import datetime

VERSION = "0.8.6 COMPONENT AUDIT"

COMPONENTS = {
    "Qualitaet": {
        "direction": "higher_better",
        "bands": [(0,39,"0-39"),(40,54,"40-54"),(55,69,"55-69"),(70,79,"70-79"),(80,100,"80-100")],
    },
    "Entwicklung": {
        "direction": "higher_better",
        "bands": [(0,39,"0-39"),(40,54,"40-54"),(55,69,"55-69"),(70,79,"70-79"),(80,100,"80-100")],
    },
    "Bewertung": {
        "direction": "higher_better",
        "bands": [(0,39,"0-39"),(40,54,"40-54"),(55,69,"55-69"),(70,79,"70-79"),(80,100,"80-100")],
    },
    "Value_Trap": {
        "direction": "lower_better",
        "bands": [(0,19,"0-19"),(20,39,"20-39"),(40,59,"40-59"),(60,79,"60-79"),(80,100,"80-100")],
    },
    "Drawdown_Score": {
        "direction": "higher_better",
        "bands": [(0,19,"0-19"),(20,39,"20-39"),(40,59,"40-59"),(60,79,"60-79"),(80,100,"80-100")],
    },
    "Trend": {
        "direction": "higher_better",
        "bands": [(0,39,"0-39"),(40,54,"40-54"),(55,69,"55-69"),(70,79,"70-79"),(80,100,"80-100")],
    },
}

REQUIRED = ["Symbol","Modell","Stichtag","Rendite_12M","Alpha_12M"] + list(COMPONENTS)


def episode_count(df: pd.DataFrame, max_gap_days: int = 130) -> int:
    if df.empty:
        return 0
    x=df.copy()
    x['_Datum']=pd.to_datetime(x['Stichtag'],errors='coerce')
    x=x.dropna(subset=['_Datum']).sort_values(['Symbol','_Datum'])
    n=0
    for _,g in x.groupby('Symbol',sort=False):
        last=None
        for d in g['_Datum']:
            if last is None or (d-last).days>max_gap_days:
                n+=1
            last=d
    return n


def safe_median(s):
    s=pd.to_numeric(s,errors='coerce').dropna()
    return float(s.median()) if len(s) else float('nan')


def safe_mean(s):
    s=pd.to_numeric(s,errors='coerce').dropna()
    return float(s.mean()) if len(s) else float('nan')


def band_row(df, model, component, lo, hi, label, direction):
    b=df if model=='ALLE' else df[df['Modell']==model]
    vals=pd.to_numeric(b[component],errors='coerce')
    sel=b[(vals>=lo)&(vals<=hi)].copy()
    full=sel[pd.to_numeric(sel['Rendite_12M'],errors='coerce').notna()].copy()
    r=pd.to_numeric(full['Rendite_12M'],errors='coerce')
    a=pd.to_numeric(full['Alpha_12M'],errors='coerce')
    sa=pd.to_numeric(full.get('Sektor_Alpha_12M',pd.Series(index=full.index,dtype=float)),errors='coerce')
    return {
        'Modell':model,'Komponente':component,'Richtung':direction,'Band':label,'Band_min':lo,'Band_max':hi,
        'Signale':len(sel),'12M_n':len(full),'Aktien':int(full['Symbol'].nunique()) if len(full) else 0,
        'Episoden':episode_count(full),'12M_Median':safe_median(r),'12M_Mittel':safe_mean(r),
        'Alpha_Median':safe_median(a),'SektorAlpha_Median':safe_median(sa),
        'SPY_geschlagen_pct':float((a>0).mean()*100) if len(a) else float('nan'),
        'Sektor_geschlagen_pct':float((sa>0).mean()*100) if len(sa.dropna()) else float('nan'),
        'Positiv_pct':float((r>0).mean()*100) if len(r) else float('nan'),
        'Minus20_pct':float((r<=-20).mean()*100) if len(r) else float('nan'),
    }


def rank_corr(df, component, target):
    x=pd.to_numeric(df[component],errors='coerce')
    y=pd.to_numeric(df[target],errors='coerce')
    m=x.notna() & y.notna()
    if m.sum()<8: return float('nan')
    xr=x[m].rank(method='average')
    yr=y[m].rank(method='average')
    return float(xr.corr(yr))


def component_summary(bands_df, source_df):
    rows=[]
    models=['ALLE']+sorted(source_df['Modell'].dropna().unique().tolist())
    for model in models:
        src=source_df if model=='ALLE' else source_df[source_df['Modell']==model]
        full=src[pd.to_numeric(src['Rendite_12M'],errors='coerce').notna()].copy()
        for comp,cfg in COMPONENTS.items():
            part=bands_df[(bands_df['Modell']==model)&(bands_df['Komponente']==comp)].copy()
            enough=part[part['12M_n']>=10].copy()
            if cfg['direction']=='higher_better':
                ordered=enough.sort_values('Band_min')
            else:
                ordered=enough.sort_values('Band_min',ascending=False)  # "besser" läuft von hohem Trap zu niedrigem Trap
            alphas=ordered['Alpha_Median'].dropna().tolist()
            medians=ordered['12M_Median'].dropna().tolist()
            monotonic_alpha=np.nan
            if len(alphas)>=3:
                monotonic_alpha=float(pd.Series(range(len(alphas))).corr(pd.Series(alphas),method='spearman'))
            # best-direction spread: best extreme minus worst extreme, where sample >=10
            valid=part[part['12M_n']>=10].sort_values('Band_min')
            spread=np.nan
            if len(valid)>=2:
                low=float(valid.iloc[0]['Alpha_Median'])
                high=float(valid.iloc[-1]['Alpha_Median'])
                spread=(high-low) if cfg['direction']=='higher_better' else (low-high)
            rho_alpha=rank_corr(full,comp,'Alpha_12M')
            rho_ret=rank_corr(full,comp,'Rendite_12M')
            if cfg['direction']=='lower_better':
                rho_alpha = -rho_alpha if not math.isnan(rho_alpha) else rho_alpha
                rho_ret = -rho_ret if not math.isnan(rho_ret) else rho_ret
            rows.append({
                'Modell':model,'Komponente':comp,'Richtung':cfg['direction'],'12M_n':len(full),
                'Spearman_Alpha_rho_erwartete_Richtung':rho_alpha,
                'Spearman_Rendite_rho_erwartete_Richtung':rho_ret,
                'Extreme_Alpha_Spread_erwartete_Richtung':spread,
                'Band_Monotonie_Alpha':monotonic_alpha,
            })
    return pd.DataFrame(rows)


def print_model_table(bands, model):
    print('\n'+'='*126)
    print(f'KOMPONENTENWIRKUNG 12M | {model}')
    print('='*126)
    print(f"{'Komponente':<16} {'Band':<8} {'n':>5} {'Aktien':>7} {'Epis':>6} {'12M Med':>9} {'Alpha Med':>10} {'Sekt A':>9} {'Pos%':>7} {'<=-20%':>8}")
    print('-'*126)
    x=bands[bands['Modell']==model]
    for comp in COMPONENTS:
        p=x[x['Komponente']==comp]
        for _,r in p.iterrows():
            def f(v): return '   --' if pd.isna(v) else f'{v:+6.1f}'
            print(f"{comp:<16} {r['Band']:<8} {int(r['12M_n']):5d} {int(r['Aktien']):7d} {int(r['Episoden']):6d} {f(r['12M_Median']):>9} {f(r['Alpha_Median']):>10} {f(r['SektorAlpha_Median']):>9} {r['Positiv_pct']:6.1f}% {r['Minus20_pct']:7.1f}%")
        print('-'*126)


def print_summary(summary):
    print('\n'+'='*126)
    print('KOMPONENTEN-RANKING: WELCHE ROHKOMPONENTE HAT TATSÄCHLICH PROGNOSEKRAFT?')
    print('='*126)
    print('Positiver rho = höhere Komponente ist besser; bei Value_Trap wurde die erwartete Richtung bereits umgedreht.')
    for model in ['ALLE'] + [m for m in summary['Modell'].unique() if m!='ALLE']:
        print(f'\n{model}')
        x=summary[summary['Modell']==model].sort_values('Spearman_Alpha_rho_erwartete_Richtung',ascending=False)
        for _,r in x.iterrows():
            rho=r['Spearman_Alpha_rho_erwartete_Richtung']; spread=r['Extreme_Alpha_Spread_erwartete_Richtung']
            rt='--' if pd.isna(rho) else f'{rho:+.3f}'
            st='--' if pd.isna(spread) else f'{spread:+.1f}'
            print(f"  {r['Komponente']:<16} rho Alpha {rt:>7} | Extreme-Alpha-Spread {st:>7}")


def audit(df):
    missing=[c for c in REQUIRED if c not in df.columns]
    if missing: raise ValueError('Fehlende Spalten: '+', '.join(missing))
    rows=[]
    models=['ALLE']+sorted(df['Modell'].dropna().unique().tolist())
    for model in models:
        for comp,cfg in COMPONENTS.items():
            for lo,hi,label in cfg['bands']:
                rows.append(band_row(df,model,comp,lo,hi,label,cfg['direction']))
    bands=pd.DataFrame(rows)
    summary=component_summary(bands,df)
    for model in models:
        print_model_table(bands,model)
    print_summary(summary)
    return bands,summary


def find_latest(folder:Path):
    pats=['TradePilot_Backtest_0.8.5.1_SCORE_AUDIT_FIX_*.csv','TradePilot_Backtest_0.8.6_COMPONENT_AUDIT_*.csv']
    files=[]
    for p in pats: files.extend(folder.glob(p))
    files=[f for f in files if 'Schwellenmatrix' not in f.name and 'ScoreAudit' not in f.name and 'Component' not in f.name]
    return max(files,key=lambda p:p.stat().st_mtime) if files else None


def main():
    ap=argparse.ArgumentParser(description='TradePilot 0.8.6 COMPONENT AUDIT')
    ap.add_argument('csv',nargs='?',help='Beobachtungs-CSV aus 0.8.5.1. Ohne Angabe wird die neueste im Ordner verwendet.')
    args=ap.parse_args()
    path=Path(args.csv).expanduser().resolve() if args.csv else find_latest(Path.cwd())
    if not path or not path.exists():
        raise SystemExit('Keine Beobachtungs-CSV gefunden. Kopiere die Full-CSV aus 0.8.5.1 in diesen Ordner oder gib ihren Pfad als Argument an.')
    print('='*100); print('TRADEPILOT 0.8.6 COMPONENT AUDIT'); print('='*100)
    print(f'Quelle: {path}')
    df=pd.read_csv(path)
    print(f'Beobachtungen: {len(df)} | Aktien: {df.Symbol.nunique()} | Modelle: {", ".join(sorted(df.Modell.dropna().unique()))}')
    bands,summary=audit(df)
    stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    f1=Path(f'TradePilot_ComponentAudit_Bands_0.8.6_{stamp}.csv')
    f2=Path(f'TradePilot_ComponentAudit_Summary_0.8.6_{stamp}.csv')
    bands.to_csv(f1,index=False,encoding='utf-8-sig')
    summary.to_csv(f2,index=False,encoding='utf-8-sig')
    print('\n'+'='*100)
    print(f'Bandanalyse gespeichert: {f1.name}')
    print(f'Komponenten-Zusammenfassung gespeichert: {f2.name}')
    print('WICHTIG: 0.8.6 verändert KEINE Scorelogik. Es misst nur die Rohkomponenten der 0.6.1.')
    print('='*100)

if __name__=='__main__': main()
