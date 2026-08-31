from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import math
import pandas as pd
import numpy as np

VERSION = "0.8.7 INTERACTION AUDIT"

REQUIRED = [
    "Symbol", "Modell", "Stichtag", "Rendite_12M", "Alpha_12M",
    "Qualitaet", "Entwicklung", "Bewertung", "Value_Trap", "Drawdown_Score", "Trend",
]

# Bewusst gröbere, fachlich unterschiedliche Bänder: genug Stichprobe + Sweet-Spots sichtbar.
BANDS = {
    "Qualitaet": [(0,54,"Q 0-54"),(55,69,"Q 55-69"),(70,100,"Q 70-100")],
    "Entwicklung": [(0,54,"Entw 0-54"),(55,69,"Entw 55-69"),(70,100,"Entw 70-100")],
    "Bewertung": [(0,54,"Bew 0-54"),(55,69,"Bew 55-69"),(70,100,"Bew 70-100")],
    "Value_Trap": [(0,19,"Trap 0-19"),(20,59,"Trap 20-59"),(60,100,"Trap 60-100")],
    "Drawdown_Score": [(0,39,"DD 0-39"),(40,59,"DD 40-59"),(60,79,"DD 60-79"),(80,100,"DD 80-100")],
    "Trend": [(0,54,"Trend 0-54"),(55,69,"Trend 55-69"),(70,79,"Trend 70-79"),(80,100,"Trend 80-100")],
}

INTERACTIONS = [
    ("Drawdown_Score", "Trend"),
    ("Drawdown_Score", "Qualitaet"),
    ("Drawdown_Score", "Bewertung"),
    ("Bewertung", "Qualitaet"),
    ("Qualitaet", "Entwicklung"),
    ("Value_Trap", "Drawdown_Score"),
]


def nval(s):
    return pd.to_numeric(s, errors="coerce")


def episode_count(df: pd.DataFrame, max_gap_days: int = 130) -> int:
    if df.empty:
        return 0
    x = df[["Symbol", "Stichtag"]].copy()
    x["_d"] = pd.to_datetime(x["Stichtag"], errors="coerce")
    x = x.dropna(subset=["_d"]).sort_values(["Symbol", "_d"])
    n = 0
    for _, g in x.groupby("Symbol", sort=False):
        last = None
        for d in g["_d"]:
            if last is None or (d-last).days > max_gap_days:
                n += 1
            last = d
    return n


def med(s):
    z=nval(s).dropna()
    return float(z.median()) if len(z) else np.nan


def mean(s):
    z=nval(s).dropna()
    return float(z.mean()) if len(z) else np.nan


def metrics(sel: pd.DataFrame) -> dict:
    full = sel[nval(sel["Rendite_12M"]).notna()].copy()
    r = nval(full["Rendite_12M"])
    a = nval(full["Alpha_12M"])
    if "Sektor_Alpha_12M" in full.columns:
        sa = nval(full["Sektor_Alpha_12M"])
    else:
        sa = pd.Series(index=full.index, dtype=float)
    return {
        "Signale": int(len(sel)),
        "12M_n": int(len(full)),
        "Aktien": int(full["Symbol"].nunique()) if len(full) else 0,
        "Episoden": int(episode_count(full)),
        "12M_Mittel": mean(r),
        "12M_Median": med(r),
        "Alpha_Median": med(a),
        "SektorAlpha_Median": med(sa),
        "SPY_geschlagen_pct": float((a>0).mean()*100) if len(a) else np.nan,
        "Sektor_geschlagen_pct": float((sa>0).mean()*100) if len(sa.dropna()) else np.nan,
        "Positiv_pct": float((r>0).mean()*100) if len(r) else np.nan,
        "Minus20_pct": float((r<=-20).mean()*100) if len(r) else np.nan,
    }


def model_baselines(df: pd.DataFrame) -> dict[str,dict]:
    out={}
    for model in ["ALLE"] + sorted(df["Modell"].dropna().unique().tolist()):
        src=df if model=="ALLE" else df[df["Modell"]==model]
        out[model]=metrics(src)
    return out


def in_band(df, col, lo, hi):
    v=nval(df[col])
    return (v>=lo)&(v<=hi)


def interaction_audit(df: pd.DataFrame) -> pd.DataFrame:
    bases=model_baselines(df)
    rows=[]
    models=["ALLE"]+sorted(df["Modell"].dropna().unique().tolist())
    for model in models:
        src=df if model=="ALLE" else df[df["Modell"]==model]
        base=bases[model]
        for a,b in INTERACTIONS:
            for alo,ahi,alab in BANDS[a]:
                for blo,bhi,blab in BANDS[b]:
                    sel=src[in_band(src,a,alo,ahi)&in_band(src,b,blo,bhi)].copy()
                    m=metrics(sel)
                    rows.append({
                        "Modell":model,"Interaktion":f"{a} x {b}",
                        "Komponente_A":a,"Band_A":alab,"A_min":alo,"A_max":ahi,
                        "Komponente_B":b,"Band_B":blab,"B_min":blo,"B_max":bhi,
                        **m,
                        "Alpha_Uplift_vs_Modell": m["Alpha_Median"]-base["Alpha_Median"] if not pd.isna(m["Alpha_Median"]) and not pd.isna(base["Alpha_Median"]) else np.nan,
                        "SektorAlpha_Uplift_vs_Modell": m["SektorAlpha_Median"]-base["SektorAlpha_Median"] if not pd.isna(m["SektorAlpha_Median"]) and not pd.isna(base["SektorAlpha_Median"]) else np.nan,
                        "Minus20_Delta_vs_Modell": m["Minus20_pct"]-base["Minus20_pct"] if not pd.isna(m["Minus20_pct"]) and not pd.isna(base["Minus20_pct"]) else np.nan,
                    })
    out=pd.DataFrame(rows)
    out["Stichprobe_OK"]=(out["12M_n"]>=20)&(out["Aktien"]>=10)&(out["Episoden"]>=10)
    return out


SWEET_SPOTS = [
    ("DD80 + Trend55-79", lambda d: (nval(d.Drawdown_Score)>=80)&nval(d.Trend).between(55,79)),
    ("DD80 + Trend70-79", lambda d: (nval(d.Drawdown_Score)>=80)&nval(d.Trend).between(70,79)),
    ("DD80 + Trend55-69", lambda d: (nval(d.Drawdown_Score)>=80)&nval(d.Trend).between(55,69)),
    ("DD80 + Bewertung>=55", lambda d: (nval(d.Drawdown_Score)>=80)&(nval(d.Bewertung)>=55)),
    ("DD80 + Qualitaet>=70", lambda d: (nval(d.Drawdown_Score)>=80)&(nval(d.Qualitaet)>=70)),
    ("DD80 + Bew>=55 + Trend55-79", lambda d: (nval(d.Drawdown_Score)>=80)&(nval(d.Bewertung)>=55)&nval(d.Trend).between(55,79)),
    ("DD80 + Q>=70 + Trend55-79", lambda d: (nval(d.Drawdown_Score)>=80)&(nval(d.Qualitaet)>=70)&nval(d.Trend).between(55,79)),
    ("Bewertung>=55 + Q>=70", lambda d: (nval(d.Bewertung)>=55)&(nval(d.Qualitaet)>=70)),
    ("Trend55-79", lambda d: nval(d.Trend).between(55,79)),
    ("Trend70-79", lambda d: nval(d.Trend).between(70,79)),
    ("Trap<20 + DD>=60", lambda d: (nval(d.Value_Trap)<20)&(nval(d.Drawdown_Score)>=60)),
    ("Trap<40 + DD>=80", lambda d: (nval(d.Value_Trap)<40)&(nval(d.Drawdown_Score)>=80)),
]


def sweet_spot_audit(df:pd.DataFrame)->pd.DataFrame:
    bases=model_baselines(df)
    rows=[]
    models=["ALLE"]+sorted(df["Modell"].dropna().unique().tolist())
    for model in models:
        src=df if model=="ALLE" else df[df["Modell"]==model]
        base=bases[model]
        for name,fn in SWEET_SPOTS:
            mask=fn(src).fillna(False)
            m=metrics(src[mask].copy())
            rows.append({"Modell":model,"Filter":name,**m,
                "Alpha_Uplift_vs_Modell":m["Alpha_Median"]-base["Alpha_Median"] if not pd.isna(m["Alpha_Median"]) and not pd.isna(base["Alpha_Median"]) else np.nan,
                "SektorAlpha_Uplift_vs_Modell":m["SektorAlpha_Median"]-base["SektorAlpha_Median"] if not pd.isna(m["SektorAlpha_Median"]) and not pd.isna(base["SektorAlpha_Median"]) else np.nan,
                "Minus20_Delta_vs_Modell":m["Minus20_pct"]-base["Minus20_pct"] if not pd.isna(m["Minus20_pct"]) and not pd.isna(base["Minus20_pct"]) else np.nan,
            })
    out=pd.DataFrame(rows)
    out["Stichprobe_OK"]=(out["12M_n"]>=20)&(out["Aktien"]>=10)&(out["Episoden"]>=10)
    return out


def fmt(v, pct=False):
    if pd.isna(v): return "--"
    return f"{v:+.1f}%" if pct else f"{v:+.1f}"


def print_baselines(df):
    print("\n"+"="*142)
    print("MODELL-BASISLINIEN 12M")
    print("="*142)
    print(f"{'Modell':<18}{'n':>7}{'Aktien':>8}{'Epis':>7}{'12M Med':>11}{'Alpha Med':>12}{'Sekt A':>10}{'SPY%':>8}{'Positiv%':>10}{'<=-20%':>9}")
    for model,m in model_baselines(df).items():
        print(f"{model:<18}{m['12M_n']:7d}{m['Aktien']:8d}{m['Episoden']:7d}{fmt(m['12M_Median'],True):>11}{fmt(m['Alpha_Median']):>12}{fmt(m['SektorAlpha_Median']):>10}{m['SPY_geschlagen_pct']:7.1f}%{m['Positiv_pct']:9.1f}%{m['Minus20_pct']:8.1f}%")


def print_sweet(sweet):
    print("\n"+"="*142)
    print("SWEET-SPOT TESTS | bewusst vorab definierte Kombinationen")
    print("="*142)
    for model in ["ALLE"]+[m for m in sweet.Modell.unique() if m!="ALLE"]:
        print(f"\n{model}")
        print(f"{'Filter':<34}{'n':>6}{'Akt.':>6}{'Epis':>6}{'12M Med':>10}{'Alpha':>9}{'SektA':>9}{'A-Uplift':>10}{'Pos%':>8}{'<=-20':>8}{'OK':>5}")
        x=sweet[sweet.Modell==model].sort_values(["Stichprobe_OK","Alpha_Median"],ascending=[False,False])
        for _,r in x.iterrows():
            print(f"{r['Filter']:<34}{int(r['12M_n']):6d}{int(r['Aktien']):6d}{int(r['Episoden']):6d}{fmt(r['12M_Median'],True):>10}{fmt(r['Alpha_Median']):>9}{fmt(r['SektorAlpha_Median']):>9}{fmt(r['Alpha_Uplift_vs_Modell']):>10}{r['Positiv_pct']:7.1f}%{r['Minus20_pct']:7.1f}%{('JA' if r['Stichprobe_OK'] else 'NEIN'):>5}")


def print_top_interactions(inter, topn=12):
    print("\n"+"="*142)
    print("TOP INTERAKTIONSZELLEN | nur Stichprobe_OK (>=20 12M, >=10 Aktien, >=10 Episoden)")
    print("="*142)
    for model in ["ALLE"]+[m for m in inter.Modell.unique() if m!="ALLE"]:
        x=inter[(inter.Modell==model)&(inter.Stichprobe_OK)].copy()
        x=x.sort_values(["Alpha_Median","Minus20_pct"],ascending=[False,True]).head(topn)
        print(f"\n{model} | {len(x)} angezeigte Zellen")
        if x.empty:
            print("  Keine Zelle erfüllt aktuell die Mindeststichprobe.")
            continue
        print(f"{'Interaktion':<34}{'Band A':<16}{'Band B':<17}{'n':>5}{'Akt.':>6}{'12M':>9}{'Alpha':>9}{'SektA':>9}{'<=-20':>8}")
        for _,r in x.iterrows():
            print(f"{r['Interaktion']:<34}{r['Band_A']:<16}{r['Band_B']:<17}{int(r['12M_n']):5d}{int(r['Aktien']):6d}{fmt(r['12M_Median'],True):>9}{fmt(r['Alpha_Median']):>9}{fmt(r['SektorAlpha_Median']):>9}{r['Minus20_pct']:7.1f}%")


def candidate_shortlist(inter,sweet):
    a=inter[inter.Stichprobe_OK].copy()
    a["Typ"]="INTERAKTION"
    a["Kandidat"]=a["Interaktion"]+" | "+a["Band_A"]+" + "+a["Band_B"]
    b=sweet[sweet.Stichprobe_OK].copy()
    b["Typ"]="SWEET_SPOT"
    b["Kandidat"]=b["Filter"]
    cols=["Modell","Typ","Kandidat","12M_n","Aktien","Episoden","12M_Median","Alpha_Median","SektorAlpha_Median","SPY_geschlagen_pct","Positiv_pct","Minus20_pct","Alpha_Uplift_vs_Modell","SektorAlpha_Uplift_vs_Modell","Minus20_Delta_vs_Modell"]
    out=pd.concat([a[cols],b[cols]],ignore_index=True)
    # Forschungsranking: Alpha zuerst, dann Risiko. KEINE automatische Strategieentscheidung.
    out=out.sort_values(["Modell","Alpha_Median","Minus20_pct","12M_n"],ascending=[True,False,True,False])
    return out


def find_latest(start:Path):
    folders=[start, start.parent/"TradePilot_0_8_6_COMPONENT_AUDIT", start.parent/"TradePilot_0_8_5_1_SCORE_AUDIT_FIX"]
    pats=["TradePilot_Backtest_0.8.5.1_SCORE_AUDIT_FIX_*.csv"]
    found=[]
    for folder in folders:
        if not folder.exists(): continue
        for p in pats:
            found.extend(folder.glob(p))
    found=[f for f in found if "Schwellenmatrix" not in f.name and "ScoreAudit" not in f.name and "Component" not in f.name and "Interaction" not in f.name]
    return max(found,key=lambda p:p.stat().st_mtime) if found else None


def run(df:pd.DataFrame):
    missing=[c for c in REQUIRED if c not in df.columns]
    if missing: raise ValueError("Fehlende Spalten: "+", ".join(missing))
    print_baselines(df)
    inter=interaction_audit(df)
    sweet=sweet_spot_audit(df)
    print_sweet(sweet)
    print_top_interactions(inter)
    short=candidate_shortlist(inter,sweet)
    return inter,sweet,short


def main():
    ap=argparse.ArgumentParser(description="TradePilot 0.8.7 INTERACTION AUDIT")
    ap.add_argument("csv",nargs="?",help="Beobachtungs-CSV. Ohne Angabe automatische Suche in 0.8.7/0.8.6/0.8.5.1.")
    args=ap.parse_args()
    path=Path(args.csv).expanduser().resolve() if args.csv else find_latest(Path.cwd())
    if not path or not path.exists():
        raise SystemExit("Keine Full-Beobachtungs-CSV gefunden. Lege sie in diesen Ordner oder lass den 0.8.6/0.8.5.1-Ordner daneben bestehen.")
    print("="*110); print(f"TRADEPILOT {VERSION}"); print("="*110)
    print(f"Quelle: {path}")
    df=pd.read_csv(path)
    print(f"Beobachtungen: {len(df)} | Aktien: {df.Symbol.nunique()} | Modelle: {', '.join(sorted(df.Modell.dropna().unique()))}")
    inter,sweet,short=run(df)
    stamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    f1=Path(f"TradePilot_InteractionAudit_Cells_0.8.7_{stamp}.csv")
    f2=Path(f"TradePilot_InteractionAudit_SweetSpots_0.8.7_{stamp}.csv")
    f3=Path(f"TradePilot_InteractionAudit_Shortlist_0.8.7_{stamp}.csv")
    inter.to_csv(f1,index=False,encoding="utf-8-sig")
    sweet.to_csv(f2,index=False,encoding="utf-8-sig")
    short.to_csv(f3,index=False,encoding="utf-8-sig")
    print("\n"+"="*110)
    print(f"Interaktionszellen gespeichert: {f1.name}")
    print(f"Sweet-Spots gespeichert:       {f2.name}")
    print(f"Kandidaten-Shortlist:           {f3.name}")
    print("WICHTIG: 0.8.7 verändert KEINE Scorelogik. Es sucht Kombinationseffekte in der 0.6.1-Forschungsbasis.")
    print("Mindeststichprobe ist nur ein Filter, keine wissenschaftliche Signifikanzprüfung.")
    print("="*110)

if __name__=="__main__":
    main()
