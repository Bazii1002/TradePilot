
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
import numpy as np

VERSION = "0.8.9 CANDIDATE SCORE DESIGN"

ALIASES = {
    "Symbol": ["Symbol","Aktie","Ticker","symbol","ticker"],
    "Modell": ["Modell","Model","model"],
    "Stichtag": ["Stichtag","Datum","Date","date"],
    "Rendite_12M": ["Rendite_12M","Forward_12M","12M","Return_12M","forward_12m"],
    "Alpha_12M": ["Alpha_12M","SPY_Alpha_12M","12M_Alpha","alpha_12m"],
    "Sektor_Alpha_12M": ["Sektor_Alpha_12M","Sector_Alpha_12M","SektorAlpha_12M","sector_alpha_12m"],
    "Qualitaet": ["Qualitaet","Quality","Qualitaets_Score","quality_score"],
    "Entwicklung": ["Entwicklung","Development","Entwicklungs_Score","development_score"],
    "Bewertung": ["Bewertung","Valuation","Bewertungs_Score","valuation_score"],
    "Value_Trap": ["Value_Trap","Trap","ValueTrap","trap_score"],
    "Drawdown_Score": ["Drawdown_Score","DrawdownScore","drawdown_score"],
    "Trend": ["Trend","Trend_Score","trend_score"],
    "Unternehmensscore": ["B061_Unternehmensscore","Unternehmensscore","Company_Score","company_score"],
    "Einstiegsscore": ["B061_Einstiegsscore","Einstiegsscore","Entry_Score","entry_score"],
}

def clean_columns(df):
    df = df.copy()
    df.columns = [str(c).replace("\ufeff","").strip() for c in df.columns]
    return df

def find_col(df, key, required=True):
    for c in ALIASES[key]:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"Keine passende Spalte für {key}. Vorhanden: {list(df.columns)}")
    return None

def prep(raw):
    raw = clean_columns(raw)
    m = {k: find_col(raw,k) for k in [
        "Symbol","Modell","Stichtag","Rendite_12M","Alpha_12M",
        "Qualitaet","Entwicklung","Bewertung","Value_Trap","Drawdown_Score","Trend",
        "Unternehmensscore","Einstiegsscore"
    ]}
    m["Sektor_Alpha_12M"] = find_col(raw,"Sektor_Alpha_12M",required=False)
    out = pd.DataFrame(index=raw.index)
    out["Aktie"] = raw[m["Symbol"]].astype(str)
    out["Modell"] = raw[m["Modell"]].astype(str).str.upper()
    out["Datum"] = pd.to_datetime(raw[m["Stichtag"]],errors="coerce")
    for src,dst in [
        ("Rendite_12M","R12"),("Alpha_12M","Alpha"),("Qualitaet","Q"),("Entwicklung","Dev"),
        ("Bewertung","Val"),("Value_Trap","Trap"),("Drawdown_Score","DD"),("Trend","Trend"),
        ("Unternehmensscore","U"),("Einstiegsscore","E")
    ]:
        out[dst] = pd.to_numeric(raw[m[src]],errors="coerce")
    if m["Sektor_Alpha_12M"]:
        out["SektorAlpha"] = pd.to_numeric(raw[m["Sektor_Alpha_12M"]],errors="coerce")
    else:
        out["SektorAlpha"] = out["Alpha"]
    return out.dropna(subset=["Aktie","Modell","Datum","R12","Alpha"]).copy()

def collapse_episodes(df,max_gap_days=130):
    if df.empty: return df.copy()
    keep=[]
    for _,g in df.sort_values(["Aktie","Datum"]).groupby("Aktie",sort=False):
        last=None
        for idx,r in g.iterrows():
            if last is None or (r.Datum-last).days>max_gap_days:
                keep.append(idx)
            last=r.Datum
    return df.loc[keep].copy()

def metrics(df):
    if df.empty:
        return dict(n=0,aktien=0,epis=0,med=np.nan,alpha=np.nan,sekt=np.nan,pos=np.nan,loss20=np.nan,
                    ep_alpha=np.nan,stock_alpha=np.nan)
    ep=collapse_episodes(df)
    stock=df.groupby("Aktie").agg(Alpha=("Alpha","mean"),SektorAlpha=("SektorAlpha","mean"),R12=("R12","mean"))
    return dict(
        n=len(df),aktien=df.Aktie.nunique(),epis=len(ep),
        med=float(df.R12.median()),alpha=float(df.Alpha.median()),sekt=float(df.SektorAlpha.median()),
        pos=float((df.R12>0).mean()*100),loss20=float((df.R12<=-20).mean()*100),
        ep_alpha=float(ep.Alpha.median()) if len(ep) else np.nan,
        stock_alpha=float(stock.Alpha.median()) if len(stock) else np.nan
    )

def rules():
    # Baseline reference is deliberately unchanged 0.6.1 threshold.
    return {
        "BASELINE_ALL_U70_E65": ("ALL", lambda d:(d.U>=70)&(d.E>=65)),
        "STD_BASELINE_U70_E65": ("STANDARD", lambda d:(d.U>=70)&(d.E>=65)),
        "STD_RECOVERY_DD80_Bew0_54": ("STANDARD", lambda d:(d.DD>=80)&(d.Val<=54)),
        "STD_RECOVERY_OR_BASELINE": ("STANDARD", lambda d:((d.U>=70)&(d.E>=65)) | ((d.DD>=80)&(d.Val<=54))),
        "BANK_BASELINE_ALL": ("BANK", lambda d:pd.Series(True,index=d.index)),
        "BANK_TREND55_79": ("BANK", lambda d:(d.Trend>=55)&(d.Trend<=79)),
        "CAP_BASELINE_U70_E65": ("CAPITAL_MARKETS", lambda d:(d.U>=70)&(d.E>=65)),
        "CAP_TRAP20_59_DD40_59": ("CAPITAL_MARKETS", lambda d:(d.Trap>=20)&(d.Trap<=59)&(d.DD>=40)&(d.DD<=59)),
        "CAP_Q55_69_DEV0_54": ("CAPITAL_MARKETS", lambda d:(d.Q>=55)&(d.Q<=69)&(d.Dev<=54)),
        "CAP_CANDIDATE_UNION": ("CAPITAL_MARKETS", lambda d:
            ((d.Trap>=20)&(d.Trap<=59)&(d.DD>=40)&(d.DD<=59)) |
            ((d.Q>=55)&(d.Q<=69)&(d.Dev<=54))
        ),
        "ENERGY_BASELINE_U70_E65": ("ENERGY", lambda d:(d.U>=70)&(d.E>=65)),
    }

def split_frames(df):
    med_date = df.Datum.sort_values().iloc[len(df)//2]
    return {
        "FULL": df,
        "EARLY_HALF": df[df.Datum<=med_date],
        "LATE_HALF": df[df.Datum>med_date],
        "Y2023_2024": df[df.Datum.dt.year.isin([2023,2024])],
        "Y2025": df[df.Datum.dt.year.eq(2025)],
    }

def audit(df):
    rows=[]
    for split,sdf in split_frames(df).items():
        for name,(model,rule) in rules().items():
            base=sdf if model=="ALL" else sdf[sdf.Modell.eq(model)]
            chosen=base[rule(base)].copy()
            rows.append({"Split":split,"Kandidat":name,"Modell":model,**metrics(chosen)})
    return pd.DataFrame(rows)

def scorecard(a):
    rows=[]
    for cand,g in a.groupby("Kandidat",sort=False):
        f=g[g.Split=="FULL"].iloc[0]
        early=g[g.Split=="EARLY_HALF"].iloc[0]
        late=g[g.Split=="LATE_HALF"].iloc[0]
        # research grading, deliberately conservative
        sample_ok = f.n>=20 and f.aktien>=10 and f.epis>=10
        stable_time = (not pd.isna(early.alpha) and not pd.isna(late.alpha) and early.alpha>0 and late.alpha>0)
        robust_core = (f.alpha>0 and f.ep_alpha>0 and f.stock_alpha>0 and f.loss20<=20)
        grade = "A" if sample_ok and stable_time and robust_core else ("B" if sample_ok and robust_core else "C")
        rows.append({
            "Kandidat":cand,"Modell":f.Modell,
            "n":int(f.n),"Aktien":int(f.aktien),"Episoden":int(f.epis),
            "12M_Median":f.med,"Alpha_Median":f.alpha,"SektorAlpha_Median":f.sekt,
            "Episoden_Alpha":f.ep_alpha,"Aktien_Alpha":f.stock_alpha,
            "Positiv_pct":f.pos,"Minus20_pct":f.loss20,
            "Early_Alpha":early.alpha,"Late_Alpha":late.alpha,
            "Sample_OK":"JA" if sample_ok else "NEIN",
            "Zeitstabil":"JA" if stable_time else "NEIN",
            "Research_Grade":grade
        })
    return pd.DataFrame(rows).sort_values(["Research_Grade","Alpha_Median"],ascending=[True,False])

def compare_pairs(card):
    idx={r.Kandidat:r for _,r in card.iterrows()}
    pairs=[
        ("STANDARD","STD_BASELINE_U70_E65","STD_RECOVERY_DD80_Bew0_54"),
        ("STANDARD_UNION","STD_BASELINE_U70_E65","STD_RECOVERY_OR_BASELINE"),
        ("BANK","BANK_BASELINE_ALL","BANK_TREND55_79"),
        ("CAP_TRAP","CAP_BASELINE_U70_E65","CAP_TRAP20_59_DD40_59"),
        ("CAP_QDEV","CAP_BASELINE_U70_E65","CAP_Q55_69_DEV0_54"),
        ("CAP_UNION","CAP_BASELINE_U70_E65","CAP_CANDIDATE_UNION"),
    ]
    out=[]
    for label,b,c in pairs:
        if b not in idx or c not in idx: continue
        rb,rc=idx[b],idx[c]
        out.append({
            "Vergleich":label,"Baseline":b,"Kandidat":c,
            "Delta_Alpha":rc.Alpha_Median-rb.Alpha_Median,
            "Delta_EpisodenAlpha":rc.Episoden_Alpha-rb.Episoden_Alpha,
            "Delta_Loss20":rc.Minus20_pct-rb.Minus20_pct,
            "Baseline_n":rb.n,"Kandidat_n":rc.n,
            "Kandidat_Grade":rc.Research_Grade
        })
    return pd.DataFrame(out)

def fmt(x):
    return "--" if pd.isna(x) else f"{x:+.1f}"

def print_report(a,card,comp):
    print("="*150)
    print("TRADEPILOT 0.8.9 CANDIDATE SCORE DESIGN")
    print("="*150)
    print("Forschungsvergleich modellabhängiger Regeln gegen unveränderte 0.6.1-Referenzen.")
    print("\nFULL-SAMPLE SCORECARD")
    print("-"*150)
    print(f"{'Kandidat':36} {'n':>5} {'Akt':>5} {'Epis':>5} {'Med':>8} {'Alpha':>8} {'SektA':>8} {'EpA':>8} {'StkA':>8} {'<=-20':>8} {'EarlyA':>8} {'LateA':>8} {'Grade':>7}")
    for _,r in card.iterrows():
        loss="--" if pd.isna(r.Minus20_pct) else f"{r.Minus20_pct:.1f}%"
        print(f"{r.Kandidat:36} {int(r.n):5d} {int(r.Aktien):5d} {int(r.Episoden):5d} {fmt(r['12M_Median']):>8} {fmt(r.Alpha_Median):>8} {fmt(r.SektorAlpha_Median):>8} {fmt(r.Episoden_Alpha):>8} {fmt(r.Aktien_Alpha):>8} {loss:>8} {fmt(r.Early_Alpha):>8} {fmt(r.Late_Alpha):>8} {r.Research_Grade:>7}")
    print("\nDIREKTE VERGLEICHE")
    print("-"*150)
    if comp.empty:
        print("Keine Vergleichspaare.")
    else:
        print(f"{'Vergleich':18} {'Delta Alpha':>12} {'Delta EpA':>12} {'Delta <=-20':>13} {'n Base':>8} {'n Kand':>8} {'Grade':>7}")
        for _,r in comp.iterrows():
            print(f"{r.Vergleich:18} {fmt(r.Delta_Alpha):>12} {fmt(r.Delta_EpisodenAlpha):>12} {fmt(r.Delta_Loss20):>13} {int(r.Baseline_n):8d} {int(r.Kandidat_n):8d} {r.Kandidat_Grade:>7}")
    print("\nZEITSPLITS DER KANDIDATEN")
    print("-"*150)
    for cand,g in a.groupby("Kandidat",sort=False):
        print(f"\n{cand}")
        for _,r in g.iterrows():
            print(f"  {r.Split:12} n={int(r.n):4d} | Med {fmt(r.med):>7} | Alpha {fmt(r.alpha):>7} | EpA {fmt(r.ep_alpha):>7} | <=-20 {('--' if pd.isna(r.loss20) else f'{r.loss20:.1f}%'):>6}")

def find_csv(here):
    folders=[
        here,
        here.parent/"TradePilot_0_8_8_2_TIME_SPLIT_ROBUSTNESS_BOM_FIX",
        here.parent/"TradePilot_0_8_8_1_TIME_SPLIT_ROBUSTNESS_FIX",
        here.parent/"TradePilot_0_8_7_INTERACTION_AUDIT",
        here.parent/"TradePilot_0_8_6_COMPONENT_AUDIT",
        here.parent/"TradePilot_0_8_5_1_SCORE_AUDIT_FIX",
    ]
    files=[]
    for p in folders:
        if p.exists():
            files += list(p.glob("TradePilot_Backtest_0.8.5.1_SCORE_AUDIT_FIX_*.csv"))
    return max(files,key=lambda p:p.stat().st_mtime) if files else None

def selftest():
    rows=[]
    dates=pd.date_range("2023-06-30",periods=180,freq="7D")
    for i,d in enumerate(dates):
        model=["STANDARD","BANK","CAPITAL_MARKETS","ENERGY"][i%4]
        dd=20+(i*7)%81; trend=(i*13)%101; q=(i*11)%101; dev=(i*23)%101; val=(i*17)%80; trap=(i*19)%101
        u=(i*29)%101; e=(i*31)%101
        alpha=(dd-50)*0.12 + (16 if model=="STANDARD" and dd>=80 and val<=54 else 0)
        if model=="BANK": alpha += 8
        if model=="CAPITAL_MARKETS" and 20<=trap<=59 and 40<=dd<=59: alpha += 10
        rows.append({
            "\ufeffSymbol":f"T{i%55:02d}","Modell":model,"Stichtag":d,
            "Rendite_12M":alpha+18,"Alpha_12M":alpha,"Sektor_Alpha_12M":alpha,
            "Qualitaet":q,"Entwicklung":dev,"Bewertung":val,"Value_Trap":trap,
            "Drawdown_Score":dd,"Trend":trend,"B061_Unternehmensscore":u,"B061_Einstiegsscore":e
        })
    df=prep(pd.DataFrame(rows))
    a=audit(df); c=scorecard(a); comp=compare_pairs(c)
    assert len(c)==len(rules())
    assert len(comp)>=5
    print("TradePilot 0.8.9 CANDIDATE SCORE DESIGN SELFTEST: OK")
    print("Produktionsschema + BOM: OK")
    print(f"Kandidaten: {len(c)} | Vergleichspaare: {len(comp)}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",default="")
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    if args.selftest:
        selftest(); return
    here=Path(__file__).resolve().parent
    csv=Path(args.csv) if args.csv else find_csv(here)
    if csv is None or not csv.exists():
        print("FEHLER: Keine Full-Beobachtungs-CSV gefunden.")
        sys.exit(2)
    raw=pd.read_csv(csv,sep=None,engine="python")
    df=prep(raw)
    print(f"Quelle: {csv}")
    print(f"12M-Beobachtungen: {len(df)} | Aktien: {df.Aktie.nunique()} | Zeitraum: {df.Datum.min().date()} bis {df.Datum.max().date()}")
    a=audit(df); c=scorecard(a); comp=compare_pairs(c)
    print_report(a,c,comp)
    stamp=pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    f1=here/f"TradePilot_CandidateDesign_Detail_0.8.9_{stamp}.csv"
    f2=here/f"TradePilot_CandidateDesign_Scorecard_0.8.9_{stamp}.csv"
    f3=here/f"TradePilot_CandidateDesign_Comparisons_0.8.9_{stamp}.csv"
    a.to_csv(f1,index=False,encoding="utf-8-sig")
    c.to_csv(f2,index=False,encoding="utf-8-sig")
    comp.to_csv(f3,index=False,encoding="utf-8-sig")
    print("\n"+"="*150)
    print(f"Detail gespeichert:      {f1.name}")
    print(f"Scorecard gespeichert:   {f2.name}")
    print(f"Vergleiche gespeichert:  {f3.name}")
    print("WICHTIG: 0.8.9 verändert KEINE Produktions-Scorelogik. Research Grade A/B/C ist nur ein Forschungsfilter.")
    print("="*150)

if __name__=="__main__":
    main()
