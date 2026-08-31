from __future__ import annotations
import json, hashlib
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
DATA=Path(r"C:\TradePilot\03_Research_Data")
LOCK_JSON=Path(r"C:\TradePilot\02_Research\TradePilot_0_8_18_1_THIRD_HOLDOUT_LOCK_HASH_FIX\TradePilot_0_8_18_THIRD_HOLDOUT_LOCK.json")
EXPECTED_THIRD_HASH="c8d73d22b9235e835f4567258dd01de716f3bd7231acb4ae853f0ea9d7c49953"

def latest_raw():
    fs=list(HERE.glob("TradePilot_Backtest_0.8.19_THIRD_HOLDOUT_RAW_*.csv"))
    return max(fs,key=lambda p:p.stat().st_mtime) if fs else None

def verify_lock():
    if not LOCK_JSON.exists(): raise FileNotFoundError(f"0.8.18 Lock fehlt: {LOCK_JSON}")
    lock=json.loads(LOCK_JSON.read_text(encoding="utf-8"))
    if lock.get("hashes",{}).get("third_holdout_symbol_hash")!=EXPECTED_THIRD_HASH: raise RuntimeError("Third-Holdout-Hash im Lock stimmt nicht.")
    h=lock.get("hypothesis",{})
    if h.get("name")!="H1_BASELINE_061_U70_E70" or h.get("company_min")!=70 or h.get("entry_min")!=70: raise RuntimeError("Frozen H1 stimmt nicht.")
    if lock.get("primary_endpoint")!="FIRST_SIGNAL_PER_STOCK_12M": raise RuntimeError("Primary Endpoint stimmt nicht.")
    return lock

def clean(df):
    x=df.copy(); x["_d"]=pd.to_datetime(x["Stichtag"],errors="coerce")
    for c in ["Rendite_12M","Alpha_12M","Sektor_Alpha_12M","B061_Unternehmensscore","B061_Einstiegsscore"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    return x

def first_signal_per_stock(h1):
    d=h1[h1["Rendite_12M"].notna() & h1["Alpha_12M"].notna()].copy()
    if d.empty: return d
    return d.sort_values(["Symbol","_d"]).groupby("Symbol",as_index=False,group_keys=False).head(1).copy()

def metrics(d):
    d=d[d["Rendite_12M"].notna() & d["Alpha_12M"].notna()].copy()
    if d.empty: return dict(n=0,Aktien=0,Median=None,Alpha=None,SektorAlpha=None,Positiv=None,Minus20=None,SPYBeat=None,SectorBeat=None)
    return dict(n=len(d),Aktien=d["Symbol"].nunique(),Median=float(d["Rendite_12M"].median()),Alpha=float(d["Alpha_12M"].median()),SektorAlpha=float(d["Sektor_Alpha_12M"].median()),Positiv=float((d["Rendite_12M"]>0).mean()*100),Minus20=float((d["Rendite_12M"]<=-20).mean()*100),SPYBeat=float((d["Alpha_12M"]>0).mean()*100),SectorBeat=float((d["Sektor_Alpha_12M"]>0).mean()*100))

def primary_verdict(m,rule,watch):
    if m["n"]>=rule["min_first_signal_cases"]:
        ok=(m["Median"] is not None and m["Median"]>rule["median_12m_gt"] and m["Alpha"] is not None and m["Alpha"]>rule["median_spy_alpha_gt"] and m["SektorAlpha"] is not None and m["SektorAlpha"]>rule["median_sector_alpha_gt"] and m["Positiv"] is not None and m["Positiv"]>=rule["positive_rate_gte_pct"] and m["Minus20"] is not None and m["Minus20"]<=rule["loss_le_minus20_rate_lte_pct"])
        return "PASS" if ok else "FAIL"
    if m["n"]>=watch["min_first_signal_cases"] and m["Alpha"] is not None and m["Alpha"]>watch["median_spy_alpha_gt"] and m["SektorAlpha"] is not None and m["SektorAlpha"]>watch["median_sector_alpha_gt"]: return "WATCH"
    return "FAIL"

def fmt(v): return "--" if v is None or pd.isna(v) else f"{v:+.1f}"
def pct(v): return "--" if v is None or pd.isna(v) else f"{v:.1f}%"

def run(path):
    lock=verify_lock(); x=clean(pd.read_csv(path,encoding="utf-8-sig"));
    h1=x[(x["B061_Unternehmensscore"]>=70)&(x["B061_Einstiegsscore"]>=70)].copy()
    first=first_signal_per_stock(h1)
    rows=[]
    # primary first; broad/raw refs secondary only
    for name,d,kind in [("PRIMARY_FIRST_SIGNAL_PER_STOCK_12M",first,"PRIMARY"),("SECONDARY_RAW_H1",h1,"SECONDARY"),("REFERENCE_ALL",x,"REFERENCE")]:
        m=metrics(d); verdict="REFERENCE" if kind=="REFERENCE" else (primary_verdict(m,lock["pass_rule"],lock["watch_rule"]) if kind=="PRIMARY" else "DIAGNOSTIC")
        rows.append({"Test":name,**m,"Verdict":verdict})
    # diagnostics by model, first signal only; no threshold search
    for model,g in first.groupby("Modell"):
        m=metrics(g); rows.append({"Test":f"DIAG_FIRST_{model}",**m,"Verdict":"DIAGNOSTIC"})
    r=pd.DataFrame(rows)
    print("\n"+"="*152); print("TRADEPILOT 0.8.19 THIRD TRUE HOLDOUT RESULTS"); print("="*152)
    print("Primärer Endpunkt wurde VOR diesem Holdout eingefroren: FIRST_SIGNAL_PER_STOCK_12M")
    print("H1 bleibt exakt U>=70 / E>=70. Keine alternative Schwelle wird ausgewertet.\n")
    print(f"{'Test':42} {'n':>6} {'Akt':>5} {'Med':>8} {'Alpha':>8} {'SektA':>8} {'SPY%':>7} {'Sekt%':>7} {'Pos%':>7} {'<=-20':>7} {'Verdict':>11}")
    for _,q in r.iterrows():
        print(f"{q.Test:<42} {int(q.n):6} {int(q.Aktien):5} {fmt(q.Median):>8} {fmt(q.Alpha):>8} {fmt(q.SektorAlpha):>8} {pct(q.SPYBeat):>7} {pct(q.SectorBeat):>7} {pct(q.Positiv):>7} {pct(q.Minus20):>7} {q.Verdict:>11}")
    print("\nVORAB EINGEFRORENE PASS-REGEL FÜR PRIMARY:")
    pr=lock['pass_rule']; wr=lock['watch_rule']
    print(f"PASS: n>={pr['min_first_signal_cases']}, Median12M>0, Median-SPY-Alpha>0, Median-Sektor-Alpha>0, Positiv>={pr['positive_rate_gte_pct']:.0f}%, <=-20%<={pr['loss_le_minus20_rate_lte_pct']:.0f}%")
    print(f"WATCH: n>={wr['min_first_signal_cases']} und Median-SPY-Alpha>0 und Median-Sektor-Alpha>0; sonst FAIL.")
    print("Raw-H1 und Modell-Splits sind nur diagnostisch und können den Primary-Verdict nicht ändern.")
    stamp=pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")
    rf=DATA/f"TradePilot_THIRD_HOLDOUT_Results_0.8.19_{stamp}.csv"; of=DATA/f"TradePilot_THIRD_HOLDOUT_Observations_0.8.19_{stamp}.csv"; af=DATA/f"TradePilot_THIRD_HOLDOUT_Audit_0.8.19_{stamp}.json"
    r.to_csv(rf,index=False,encoding="utf-8-sig"); x.drop(columns=["_d"],errors="ignore").to_csv(of,index=False,encoding="utf-8-sig")
    audit={"version":"0.8.19","third_holdout_symbol_hash":EXPECTED_THIRD_HASH,"primary_endpoint":"FIRST_SIGNAL_PER_STOCK_12M","h1":"U>=70/E>=70","primary_verdict":r.loc[r.Test=="PRIMARY_FIRST_SIGNAL_PER_STOCK_12M","Verdict"].iloc[0],"alternative_thresholds_tested":False,"production_score_changed":False,"raw_source":str(path)}
    af.write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding="utf-8")
    print(f"\nThird-Holdout-Ergebnis: {rf}\nBeobachtungen archiviert: {of}\nAudit: {af}\n"+"="*152)
    return r

def main():
    p=latest_raw()
    if p is None: raise FileNotFoundError("Keine 0.8.19 Third-Holdout Raw-CSV gefunden.")
    print(f"Quelle: {p}"); run(p)
if __name__=="__main__": main()
