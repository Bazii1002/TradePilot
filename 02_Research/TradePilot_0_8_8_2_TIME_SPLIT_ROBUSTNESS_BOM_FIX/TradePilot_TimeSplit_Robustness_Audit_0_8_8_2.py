
from __future__ import annotations
import argparse, math, sys
from pathlib import Path
import pandas as pd
import numpy as np

VERSION = "0.8.8.2 TIME-SPLIT / ROBUSTNESS BOM FIX"

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
}

def find_col(df, canonical, required=True):
    for c in ALIASES[canonical]:
        if c in df.columns:
            return c
    if required:
        raise KeyError(
            f"Keine passende Spalte für {canonical}. Erwartet eine von: {ALIASES[canonical]}\n"
            f"Vorhandene Spalten: {list(df.columns)}"
        )
    return None

def prep(df):
    # Robust gegen UTF-8-BOM und unsichtbare/führende Leerzeichen in CSV-Spaltennamen.
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    mapping = {}
    for key in ["Symbol","Modell","Stichtag","Rendite_12M","Alpha_12M",
                "Qualitaet","Entwicklung","Bewertung","Value_Trap","Drawdown_Score","Trend"]:
        mapping[key] = find_col(df, key)
    mapping["Sektor_Alpha_12M"] = find_col(df, "Sektor_Alpha_12M", required=False)

    out = pd.DataFrame(index=df.index)
    out["Aktie"] = df[mapping["Symbol"]].astype(str)
    out["Modell"] = df[mapping["Modell"]].astype(str).str.upper()
    out["Datum"] = pd.to_datetime(df[mapping["Stichtag"]], errors="coerce")
    out["R12"] = pd.to_numeric(df[mapping["Rendite_12M"]], errors="coerce")
    out["Alpha"] = pd.to_numeric(df[mapping["Alpha_12M"]], errors="coerce")
    if mapping["Sektor_Alpha_12M"]:
        out["SektorAlpha"] = pd.to_numeric(df[mapping["Sektor_Alpha_12M"]], errors="coerce")
    else:
        out["SektorAlpha"] = out["Alpha"]
    out["Q"] = pd.to_numeric(df[mapping["Qualitaet"]], errors="coerce")
    out["Dev"] = pd.to_numeric(df[mapping["Entwicklung"]], errors="coerce")
    out["Val"] = pd.to_numeric(df[mapping["Bewertung"]], errors="coerce")
    out["Trap"] = pd.to_numeric(df[mapping["Value_Trap"]], errors="coerce")
    out["DD"] = pd.to_numeric(df[mapping["Drawdown_Score"]], errors="coerce")
    out["Trend"] = pd.to_numeric(df[mapping["Trend"]], errors="coerce")
    out = out.dropna(subset=["Datum","Aktie","Modell","R12","Alpha"]).copy()
    return out

def collapse_episodes(df, max_gap_days=130):
    if df.empty:
        return df.copy()
    rows=[]
    for _,g in df.sort_values(["Aktie","Datum"]).groupby("Aktie", sort=False):
        last=None
        for idx,r in g.iterrows():
            if last is None or (r["Datum"]-last).days > max_gap_days:
                rows.append(idx)
            last=r["Datum"]
    return df.loc[rows].copy()

def trimmean(s, frac=0.10):
    s=pd.Series(s).dropna().sort_values()
    if len(s)==0: return np.nan
    k=int(np.floor(len(s)*frac))
    if len(s)-2*k <= 0: return float(s.mean())
    return float(s.iloc[k:len(s)-k].mean())

def metrics(df):
    if df.empty:
        return {
            "n":0,"aktien":0,"epis":0,"ret_mean":np.nan,"ret_med":np.nan,
            "alpha_med":np.nan,"sekt_med":np.nan,"pos":np.nan,"loss20":np.nan,
            "trim10":np.nan,"ohne_top1":np.nan,"ohne_top3":np.nan,
            "stock_mean":np.nan,"stock_med":np.nan,"stock_alpha":np.nan,"stock_sekt":np.nan,
            "ep_ret_med":np.nan,"ep_alpha_med":np.nan,"ep_sekt_med":np.nan,
        }
    ep=collapse_episodes(df)
    sr=df["R12"].sort_values(ascending=False)
    stock=df.groupby("Aktie").agg(R12=("R12","mean"),Alpha=("Alpha","mean"),SektorAlpha=("SektorAlpha","mean"))
    return {
        "n":len(df),
        "aktien":df["Aktie"].nunique(),
        "epis":len(ep),
        "ret_mean":float(df["R12"].mean()),
        "ret_med":float(df["R12"].median()),
        "alpha_med":float(df["Alpha"].median()),
        "sekt_med":float(df["SektorAlpha"].median()),
        "pos":float((df["R12"]>0).mean()*100),
        "loss20":float((df["R12"]<=-20).mean()*100),
        "trim10":trimmean(df["R12"]),
        "ohne_top1":float(sr.iloc[1:].mean()) if len(sr)>1 else np.nan,
        "ohne_top3":float(sr.iloc[3:].mean()) if len(sr)>3 else np.nan,
        "stock_mean":float(stock["R12"].mean()),
        "stock_med":float(stock["R12"].median()),
        "stock_alpha":float(stock["Alpha"].median()),
        "stock_sekt":float(stock["SektorAlpha"].median()),
        "ep_ret_med":float(ep["R12"].median()) if len(ep) else np.nan,
        "ep_alpha_med":float(ep["Alpha"].median()) if len(ep) else np.nan,
        "ep_sekt_med":float(ep["SektorAlpha"].median()) if len(ep) else np.nan,
    }

def candidates():
    return {
        "STD_DD80_Bew0_54": ("STANDARD", lambda d:(d.DD>=80)&(d.Val<=54)),
        "STD_DD80_Q0_54": ("STANDARD", lambda d:(d.DD>=80)&(d.Q<=54)),
        "STD_DD80_Trend0_54": ("STANDARD", lambda d:(d.DD>=80)&(d.Trend<=54)),
        "STD_Trap60_100_DD80": ("STANDARD", lambda d:(d.Trap>=60)&(d.DD>=80)),
        "STD_DD60_79_Trend80_100": ("STANDARD", lambda d:(d.DD>=60)&(d.DD<=79)&(d.Trend>=80)),
        "STD_DD60_79_Trend55_69": ("STANDARD", lambda d:(d.DD>=60)&(d.DD<=79)&(d.Trend>=55)&(d.Trend<=69)),
        "CAP_Trap20_59_DD40_59": ("CAPITAL_MARKETS", lambda d:(d.Trap>=20)&(d.Trap<=59)&(d.DD>=40)&(d.DD<=59)),
        "CAP_Q55_69_Dev0_54": ("CAPITAL_MARKETS", lambda d:(d.Q>=55)&(d.Q<=69)&(d.Dev<=54)),
        "BANK_Baseline": ("BANK", lambda d:pd.Series(True,index=d.index)),
        "BANK_Trend55_79": ("BANK", lambda d:(d.Trend>=55)&(d.Trend<=79)),
    }

def split_part(chosen, split, median_date):
    if split=="FULL": return chosen
    if split=="EARLY_HALF": return chosen[chosen.Datum<=median_date]
    if split=="LATE_HALF": return chosen[chosen.Datum>median_date]
    if split=="Y2023_2024": return chosen[chosen.Datum.dt.year.isin([2023,2024])]
    if split=="Y2025": return chosen[chosen.Datum.dt.year.eq(2025)]
    if split=="Y2026": return chosen[chosen.Datum.dt.year.eq(2026)]
    return chosen.iloc[0:0]

def audit(df):
    median_date=df["Datum"].sort_values().iloc[len(df)//2]
    splits=["FULL","EARLY_HALF","LATE_HALF","Y2023_2024","Y2025","Y2026"]
    rows=[]
    for name,(model,rule) in candidates().items():
        base=df[df.Modell.eq(model)].copy()
        chosen=base[rule(base)].copy()
        for split in splits:
            part=split_part(chosen,split,median_date)
            rows.append({"Kandidat":name,"Modell":model,"Split":split,**metrics(part)})
    return pd.DataFrame(rows)

def shortlist(s):
    rows=[]
    for cand,g in s.groupby("Kandidat",sort=False):
        f=g[g.Split=="FULL"].iloc[0]
        time=g[(g.Split!="FULL")&(g.n>0)]
        pos=int((time.alpha_med>0).sum())
        neg=int((time.alpha_med<=0).sum())
        sample_ok=(f.n>=20 and f.aktien>=10 and f.epis>=10)
        robust=(sample_ok and f.alpha_med>0 and f.ep_alpha_med>0 and f.stock_alpha>0
                and f.loss20<=20 and pos>=max(2,int(np.ceil(len(time)*0.60))))
        rows.append({
            "Kandidat":cand,"Modell":f.Modell,
            "Full_n":int(f.n),"Aktien":int(f.aktien),"Epis":int(f.epis),
            "Full_Median":f.ret_med,"Full_Alpha":f.alpha_med,"Full_SektorAlpha":f.sekt_med,
            "Episoden_Alpha":f.ep_alpha_med,"Aktien_Alpha":f.stock_alpha,
            "Trim10":f.trim10,"OhneTop1":f.ohne_top1,"OhneTop3":f.ohne_top3,
            "Minus20_pct":f.loss20,"Positive_Zeitsplits":pos,"Negative_Zeitsplits":neg,
            "Stichprobe_OK":"JA" if sample_ok else "NEIN",
            "Robustheitskandidat":"JA" if robust else "NEIN"
        })
    return pd.DataFrame(rows).sort_values(["Robustheitskandidat","Full_Alpha"],ascending=[False,False])

def fnum(x):
    return "--" if pd.isna(x) else f"{x:+.1f}"

def print_report(s,sl):
    print("="*142)
    print("TRADEPILOT 0.8.8.2 TIME-SPLIT / ROBUSTNESS BOM FIX")
    print("="*142)
    for cand,g in s.groupby("Kandidat",sort=False):
        print(f"\n{cand} | {g.iloc[0].Modell}")
        print(f"{'Split':12} {'n':>5} {'Akt':>5} {'Epis':>5} {'12M Med':>9} {'Alpha':>9} {'SektA':>9} {'EpAlpha':>9} {'StkAlpha':>9} {'<=-20':>8}")
        for _,r in g.iterrows():
            loss="--" if pd.isna(r.loss20) else f"{r.loss20:.1f}%"
            print(f"{r.Split:12} {int(r.n):5d} {int(r.aktien):5d} {int(r.epis):5d} {fnum(r.ret_med):>9} {fnum(r.alpha_med):>9} {fnum(r.sekt_med):>9} {fnum(r.ep_alpha_med):>9} {fnum(r.stock_alpha):>9} {loss:>8}")
    print("\n"+"="*142)
    print("ROBUSTHEITS-SHORTLIST")
    print("="*142)
    print(f"{'Kandidat':34} {'n':>4} {'Akt':>4} {'Epis':>5} {'Med':>8} {'Alpha':>8} {'EpA':>8} {'StkA':>8} {'Trim10':>8} {'Top3Out':>8} {'<=-20':>8} {'OK':>5} {'ROBUST':>7}")
    for _,r in sl.iterrows():
        loss="--" if pd.isna(r.Minus20_pct) else f"{r.Minus20_pct:.1f}%"
        print(f"{r.Kandidat:34} {int(r.Full_n):4d} {int(r.Aktien):4d} {int(r.Epis):5d} {fnum(r.Full_Median):>8} {fnum(r.Full_Alpha):>8} {fnum(r.Episoden_Alpha):>8} {fnum(r.Aktien_Alpha):>8} {fnum(r.Trim10):>8} {fnum(r.OhneTop3):>8} {loss:>8} {r.Stichprobe_OK:>5} {r.Robustheitskandidat:>7}")

def find_csv(here):
    folders=[
        here,
        here.parent/"TradePilot_0_8_8_TIME_SPLIT_ROBUSTNESS_AUDIT",
        here.parent/"TradePilot_0_8_7_INTERACTION_AUDIT",
        here.parent/"TradePilot_0_8_6_COMPONENT_AUDIT",
        here.parent/"TradePilot_0_8_5_1_SCORE_AUDIT_FIX",
    ]
    found=[]
    for p in folders:
        if p.exists():
            found += list(p.glob("TradePilot_Backtest_0.8.5.1_SCORE_AUDIT_FIX_*.csv"))
    return max(found,key=lambda p:p.stat().st_mtime) if found else None

def selftest():
    # deliberately use REAL production-style schema: Symbol + Stichtag
    rows=[]
    dates=pd.date_range("2023-06-30",periods=160,freq="7D")
    for i,d in enumerate(dates):
        model=["STANDARD","BANK","CAPITAL_MARKETS","ENERGY"][i%4]
        dd=20+(i*7)%81
        trend=(i*13)%101
        q=(i*11)%101
        val=(i*17)%80
        trap=(i*19)%101
        dev=(i*23)%101
        alpha=(dd-50)*0.15 + (18 if dd>=80 and trend<=54 else 0)
        rows.append({
            "Symbol":f"T{i%45:02d}","Modell":model,"Stichtag":d,
            "Rendite_12M":alpha+18,"Alpha_12M":alpha,"Sektor_Alpha_12M":alpha,
            "Qualitaet":q,"Entwicklung":dev,"Bewertung":val,"Value_Trap":trap,
            "Drawdown_Score":dd,"Trend":trend
        })
    testdf = pd.DataFrame(rows)
    testdf = testdf.rename(columns={"Symbol":"\ufeffSymbol"})
    df=prep(testdf)
    s=audit(df); sl=shortlist(s)
    assert len(df)==160
    assert len(sl)==10
    assert set(["FULL","EARLY_HALF","LATE_HALF","Y2023_2024","Y2025","Y2026"]).issubset(set(s.Split))
    print("TradePilot 0.8.8.2 TIME-SPLIT / ROBUSTNESS BOM FIX SELFTEST: OK")
    print("Produktionsschema Symbol/Stichtag + UTF-8-BOM: OK")
    print(f"Kandidaten: {len(sl)} | Splits: {s.Split.nunique()}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",default="")
    ap.add_argument("--selftest",action="store_true")
    a=ap.parse_args()
    if a.selftest:
        selftest(); return
    here=Path(__file__).resolve().parent
    csv=Path(a.csv) if a.csv else find_csv(here)
    if csv is None or not csv.exists():
        print("FEHLER: Keine Full-Beobachtungs-CSV gefunden.")
        sys.exit(2)
    raw=pd.read_csv(csv,sep=None,engine="python")
    df=prep(raw)
    print(f"Quelle: {csv}")
    print(f"12M-Beobachtungen: {len(df)} | Aktien: {df.Aktie.nunique()} | Zeitraum: {df.Datum.min().date()} bis {df.Datum.max().date()}")
    s=audit(df); sl=shortlist(s)
    print_report(s,sl)
    stamp=pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    f1=here/f"TradePilot_TimeSplit_0.8.8.2_{stamp}.csv"
    f2=here/f"TradePilot_Robustness_Shortlist_0.8.8.2_{stamp}.csv"
    s.to_csv(f1,index=False,encoding="utf-8-sig")
    sl.to_csv(f2,index=False,encoding="utf-8-sig")
    print("\n"+"="*142)
    print(f"Zeit-Split-CSV gespeichert: {f1.name}")
    print(f"Robustheits-Shortlist:      {f2.name}")
    print("WICHTIG: Keine Scorelogik wurde verändert.")
    print("="*142)

if __name__=="__main__":
    main()
