
from __future__ import annotations
import argparse, sys
from pathlib import Path
import pandas as pd
import numpy as np

VERSION = "0.8.10 WALK-FORWARD / OUT-OF-SAMPLE AUDIT"

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

TRAIN_START = pd.Timestamp("2023-06-30")
TRAIN_END   = pd.Timestamp("2024-06-30")
VALID_START = pd.Timestamp("2024-09-01")
VALID_END   = pd.Timestamp("2025-06-30")

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
    needed = ["Symbol","Modell","Stichtag","Rendite_12M","Alpha_12M",
              "Qualitaet","Entwicklung","Bewertung","Value_Trap","Drawdown_Score","Trend",
              "Unternehmensscore","Einstiegsscore"]
    m = {k: find_col(raw,k) for k in needed}
    m["Sektor_Alpha_12M"] = find_col(raw,"Sektor_Alpha_12M",required=False)

    out = pd.DataFrame(index=raw.index)
    out["Aktie"] = raw[m["Symbol"]].astype(str)
    out["Modell"] = raw[m["Modell"]].astype(str).str.upper()
    out["Datum"] = pd.to_datetime(raw[m["Stichtag"]],errors="coerce")
    pairs = [
        ("Rendite_12M","R12"),("Alpha_12M","Alpha"),("Qualitaet","Q"),
        ("Entwicklung","Dev"),("Bewertung","Val"),("Value_Trap","Trap"),
        ("Drawdown_Score","DD"),("Trend","Trend"),("Unternehmensscore","U"),
        ("Einstiegsscore","E")
    ]
    for src,dst in pairs:
        out[dst] = pd.to_numeric(raw[m[src]],errors="coerce")
    if m["Sektor_Alpha_12M"]:
        out["SektorAlpha"] = pd.to_numeric(raw[m["Sektor_Alpha_12M"]],errors="coerce")
    else:
        out["SektorAlpha"] = out["Alpha"]
    out = out.dropna(subset=["Aktie","Modell","Datum","R12","Alpha"]).copy()
    return out

def collapse_episodes(df,max_gap_days=130):
    if df.empty:
        return df.copy()
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
        return dict(n=0,aktien=0,epis=0,med=np.nan,alpha=np.nan,sekt=np.nan,
                    pos=np.nan,loss20=np.nan,ep_alpha=np.nan,stock_alpha=np.nan,
                    mean=np.nan,trim10=np.nan)
    ep = collapse_episodes(df)
    stock = df.groupby("Aktie").agg(Alpha=("Alpha","mean"),R12=("R12","mean"))
    s = df["R12"].dropna().sort_values()
    k = int(np.floor(len(s)*0.10))
    trim10 = float(s.iloc[k:len(s)-k].mean()) if len(s)-2*k>0 else float(s.mean())
    return dict(
        n=len(df), aktien=df.Aktie.nunique(), epis=len(ep),
        med=float(df.R12.median()), alpha=float(df.Alpha.median()),
        sekt=float(df.SektorAlpha.median()),
        pos=float((df.R12>0).mean()*100),
        loss20=float((df.R12<=-20).mean()*100),
        ep_alpha=float(ep.Alpha.median()) if len(ep) else np.nan,
        stock_alpha=float(stock.Alpha.median()) if len(stock) else np.nan,
        mean=float(df.R12.mean()), trim10=trim10
    )

def frozen_rules():
    # FROZEN from 0.8.9 – do not optimize inside this script.
    return {
        "STD_BASELINE_U70_E65": ("STANDARD", lambda d:(d.U>=70)&(d.E>=65)),
        "STD_RECOVERY_DD80_Bew0_54": ("STANDARD", lambda d:(d.DD>=80)&(d.Val<=54)),
        "BANK_BASELINE_ALL": ("BANK", lambda d:pd.Series(True,index=d.index)),
        "BANK_TREND55_79": ("BANK", lambda d:(d.Trend>=55)&(d.Trend<=79)),
        "CAP_TRAP20_59_DD40_59": ("CAPITAL_MARKETS", lambda d:(d.Trap>=20)&(d.Trap<=59)&(d.DD>=40)&(d.DD<=59)),
        "CAP_Q55_69_DEV0_54": ("CAPITAL_MARKETS", lambda d:(d.Q>=55)&(d.Q<=69)&(d.Dev<=54)),
        "ENERGY_BASELINE_U70_E65": ("ENERGY", lambda d:(d.U>=70)&(d.E>=65)),
    }

def periods(df):
    return {
        "TRAIN_2023-06_to_2024-06": df[(df.Datum>=TRAIN_START)&(df.Datum<=TRAIN_END)].copy(),
        "GAP_2024-07_to_2024-08": df[(df.Datum>TRAIN_END)&(df.Datum<VALID_START)].copy(),
        "VALID_2024-09_to_2025-06": df[(df.Datum>=VALID_START)&(df.Datum<=VALID_END)].copy(),
        "FULL_REFERENCE": df.copy(),
    }

def audit(df):
    rows=[]
    for period,pdf in periods(df).items():
        for name,(model,rule) in frozen_rules().items():
            base=pdf[pdf.Modell.eq(model)].copy()
            chosen=base[rule(base)].copy()
            rows.append({"Periode":period,"Kandidat":name,"Modell":model,**metrics(chosen)})
    return pd.DataFrame(rows)

def verdicts(a):
    rows=[]
    for cand,g in a.groupby("Kandidat",sort=False):
        tr=g[g.Periode=="TRAIN_2023-06_to_2024-06"].iloc[0]
        va=g[g.Periode=="VALID_2024-09_to_2025-06"].iloc[0]
        full=g[g.Periode=="FULL_REFERENCE"].iloc[0]

        train_ok = tr.n>=5 and tr.alpha>0 and tr.ep_alpha>0
        valid_sample = va.n>=5 and va.aktien>=4
        valid_core = valid_sample and va.alpha>0 and va.ep_alpha>0 and va.stock_alpha>0 and va.loss20<=20
        same_sign = (pd.notna(tr.alpha) and pd.notna(va.alpha) and tr.alpha>0 and va.alpha>0)
        alpha_decay = np.nan
        if pd.notna(tr.alpha) and tr.alpha != 0 and pd.notna(va.alpha):
            alpha_decay = va.alpha/tr.alpha

        if valid_core and same_sign:
            verdict="PASS"
        elif valid_sample and va.alpha>0:
            verdict="WATCH"
        else:
            verdict="FAIL"

        rows.append({
            "Kandidat":cand,"Modell":full.Modell,
            "Train_n":int(tr.n),"Train_Aktien":int(tr.aktien),"Train_Alpha":tr.alpha,"Train_EpAlpha":tr.ep_alpha,
            "Valid_n":int(va.n),"Valid_Aktien":int(va.aktien),"Valid_Epis":int(va.epis),
            "Valid_Median":va.med,"Valid_Alpha":va.alpha,"Valid_SektorAlpha":va.sekt,
            "Valid_EpAlpha":va.ep_alpha,"Valid_StockAlpha":va.stock_alpha,
            "Valid_Pos_pct":va.pos,"Valid_Minus20_pct":va.loss20,
            "Alpha_Retention":alpha_decay,
            "Verdict":verdict
        })
    order={"PASS":0,"WATCH":1,"FAIL":2}
    out=pd.DataFrame(rows)
    out["_o"]=out.Verdict.map(order)
    out=out.sort_values(["_o","Valid_Alpha"],ascending=[True,False]).drop(columns="_o")
    return out

def pairwise(a):
    pairs=[
        ("STANDARD","STD_BASELINE_U70_E65","STD_RECOVERY_DD80_Bew0_54"),
        ("BANK","BANK_BASELINE_ALL","BANK_TREND55_79"),
    ]
    rows=[]
    for label,b,c in pairs:
        for period in ["TRAIN_2023-06_to_2024-06","VALID_2024-09_to_2025-06"]:
            gb=a[(a.Kandidat==b)&(a.Periode==period)]
            gc=a[(a.Kandidat==c)&(a.Periode==period)]
            if gb.empty or gc.empty: continue
            rb=gb.iloc[0]; rc=gc.iloc[0]
            rows.append({
                "Vergleich":label,"Periode":period,"Baseline":b,"Kandidat":c,
                "Baseline_n":int(rb.n),"Kandidat_n":int(rc.n),
                "Delta_Alpha":rc.alpha-rb.alpha,
                "Delta_EpAlpha":rc.ep_alpha-rb.ep_alpha,
                "Delta_Minus20":rc.loss20-rb.loss20
            })
    return pd.DataFrame(rows)

def f(x):
    return "--" if pd.isna(x) else f"{x:+.1f}"

def print_report(df,a,v,p):
    print("="*154)
    print("TRADEPILOT 0.8.10 WALK-FORWARD / OUT-OF-SAMPLE AUDIT")
    print("="*154)
    print(f"Gesamtdaten: {df.Datum.min().date()} bis {df.Datum.max().date()} | 12M-Beobachtungen: {len(df)} | Aktien: {df.Aktie.nunique()}")
    print(f"TRAIN: {TRAIN_START.date()} bis {TRAIN_END.date()}")
    print("GAP:   2024-07-01 bis 2024-08-31")
    print(f"VALID: {VALID_START.date()} bis {VALID_END.date()}")
    print("REGELN SIND EINGEFROREN – KEINE SCHWELLENOPTIMIERUNG IN 0.8.10.")

    print("\nOUT-OF-SAMPLE VERDICTS")
    print("-"*154)
    print(f"{'Kandidat':34} {'Tr n':>5} {'TrA':>8} {'Va n':>5} {'Akt':>4} {'Epis':>5} {'VaMed':>8} {'VaA':>8} {'VaEpA':>8} {'VaStkA':>8} {'<=-20':>8} {'Retain':>8} {'Verdict':>8}")
    for _,r in v.iterrows():
        loss="--" if pd.isna(r.Valid_Minus20_pct) else f"{r.Valid_Minus20_pct:.1f}%"
        retain="--" if pd.isna(r.Alpha_Retention) else f"{r.Alpha_Retention:.2f}x"
        print(f"{r.Kandidat:34} {int(r.Train_n):5d} {f(r.Train_Alpha):>8} {int(r.Valid_n):5d} {int(r.Valid_Aktien):4d} {int(r.Valid_Epis):5d} {f(r.Valid_Median):>8} {f(r.Valid_Alpha):>8} {f(r.Valid_EpAlpha):>8} {f(r.Valid_StockAlpha):>8} {loss:>8} {retain:>8} {r.Verdict:>8}")

    print("\nTRAIN vs VALID DETAIL")
    print("-"*154)
    for cand,g in a.groupby("Kandidat",sort=False):
        print(f"\n{cand}")
        for period in ["TRAIN_2023-06_to_2024-06","VALID_2024-09_to_2025-06","FULL_REFERENCE"]:
            r=g[g.Periode==period].iloc[0]
            loss="--" if pd.isna(r.loss20) else f"{r.loss20:.1f}%"
            print(f"  {period:27} n={int(r.n):4d} Akt={int(r.aktien):3d} Epis={int(r.epis):3d} | Med {f(r.med):>7} | Alpha {f(r.alpha):>7} | EpA {f(r.ep_alpha):>7} | StkA {f(r.stock_alpha):>7} | <=-20 {loss:>6}")

    print("\nDIREKTE BASELINE-VERGLEICHE")
    print("-"*154)
    if p.empty:
        print("Keine Vergleichsdaten.")
    else:
        print(f"{'Vergleich':12} {'Periode':27} {'n Base':>7} {'n Kand':>7} {'Δ Alpha':>9} {'Δ EpA':>9} {'Δ <=-20':>10}")
        for _,r in p.iterrows():
            print(f"{r.Vergleich:12} {r.Periode:27} {int(r.Baseline_n):7d} {int(r.Kandidat_n):7d} {f(r.Delta_Alpha):>9} {f(r.Delta_EpAlpha):>9} {f(r.Delta_Minus20):>10}")

def find_csv(here):
    folders=[
        here,
        here.parent/"TradePilot_0_8_9_CANDIDATE_SCORE_DESIGN",
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
    dates=pd.date_range("2023-06-30",periods=105,freq="7D")
    for i,d in enumerate(dates):
        for model in ["STANDARD","BANK","CAPITAL_MARKETS","ENERGY"]:
            dd=20+(i*7)%81
            trend=(i*13)%101
            q=(i*11)%101
            dev=(i*23)%101
            val=(i*17)%80
            trap=(i*19)%101
            u=(i*29)%101
            e=(i*31)%101
            alpha=(dd-50)*0.10
            if model=="STANDARD" and dd>=80 and val<=54:
                alpha += 12
            if model=="BANK":
                alpha += 6
            if model=="CAPITAL_MARKETS" and 20<=trap<=59 and 40<=dd<=59:
                alpha += 8
            rows.append({
                "\ufeffSymbol":f"{model[:2]}_{i%35:02d}","Modell":model,"Stichtag":d,
                "Rendite_12M":alpha+18,"Alpha_12M":alpha,"Sektor_Alpha_12M":alpha,
                "Qualitaet":q,"Entwicklung":dev,"Bewertung":val,"Value_Trap":trap,
                "Drawdown_Score":dd,"Trend":trend,"B061_Unternehmensscore":u,"B061_Einstiegsscore":e
            })
    df=prep(pd.DataFrame(rows))
    a=audit(df)
    v=verdicts(a)
    p=pairwise(a)
    assert len(v)==len(frozen_rules())
    assert "VALID_2024-09_to_2025-06" in set(a.Periode)
    assert len(p)==4
    print("TradePilot 0.8.10 WALK-FORWARD / OUT-OF-SAMPLE AUDIT SELFTEST: OK")
    print("Produktionsschema + UTF-8-BOM: OK")
    print("Frozen Rules: OK")
    print(f"Kandidaten: {len(v)} | Perioden: {a.Periode.nunique()}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",default="")
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    if args.selftest:
        selftest()
        return

    here=Path(__file__).resolve().parent
    csv=Path(args.csv) if args.csv else find_csv(here)
    if csv is None or not csv.exists():
        print("FEHLER: Keine Full-Beobachtungs-CSV gefunden.")
        sys.exit(2)

    raw=pd.read_csv(csv,sep=None,engine="python")
    df=prep(raw)
    print(f"Quelle: {csv}")
    a=audit(df)
    v=verdicts(a)
    p=pairwise(a)
    print_report(df,a,v,p)

    stamp=pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    f1=here/f"TradePilot_WalkForward_Detail_0.8.10_{stamp}.csv"
    f2=here/f"TradePilot_WalkForward_Verdicts_0.8.10_{stamp}.csv"
    f3=here/f"TradePilot_WalkForward_Comparisons_0.8.10_{stamp}.csv"
    a.to_csv(f1,index=False,encoding="utf-8-sig")
    v.to_csv(f2,index=False,encoding="utf-8-sig")
    p.to_csv(f3,index=False,encoding="utf-8-sig")

    print("\n"+"="*154)
    print(f"Detail gespeichert:      {f1.name}")
    print(f"Verdicts gespeichert:    {f2.name}")
    print(f"Vergleiche gespeichert:  {f3.name}")
    print("WICHTIG: 0.8.10 verändert KEINE Produktions-Scorelogik und optimiert KEINE Schwellen.")
    print("="*154)

if __name__=="__main__":
    main()
