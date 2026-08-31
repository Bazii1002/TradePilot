from __future__ import annotations
import hashlib, json, pickle, re, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf

VERSION = "0.8.19 THIRD TRUE HOLDOUT PREPARE"
DATA = Path(r"C:\TradePilot\03_Research_Data")
LOCK_DIR = Path(r"C:\TradePilot\02_Research\TradePilot_0_8_18_1_THIRD_HOLDOUT_LOCK_HASH_FIX")
THIRD_HOLDOUT = DATA / "TradePilot_Third_Holdout_Universe_0.8.18.csv"
LOCK_JSON = LOCK_DIR / "TradePilot_0_8_18_THIRD_HOLDOUT_LOCK.json"
EXPECTED_THIRD_HASH = "c8d73d22b9235e835f4567258dd01de716f3bd7231acb4ae853f0ea9d7c49953"
EXPECTED_THIRD_COUNT = 1500
META_CACHE = DATA / "holdout_cache_0_8_19" / "classification"

def norm(s):
    return str(s).strip().upper().replace(".", "-")

def symbol_hash(values):
    vals = sorted(set(norm(x) for x in values if str(x).strip()))
    return hashlib.sha256("\n".join(vals).encode("utf-8")).hexdigest()

def validate():
    for p in [THIRD_HOLDOUT, LOCK_JSON]:
        if not p.exists():
            raise FileNotFoundError(f"Pflichtdatei fehlt: {p}")
    df = pd.read_csv(THIRD_HOLDOUT, encoding="utf-8-sig")
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    if "Symbol" not in df.columns:
        raise RuntimeError("Third-Holdout-Datei hat keine Symbol-Spalte.")
    df["Symbol"] = df["Symbol"].map(norm)
    df = df[df["Symbol"].astype(bool)].drop_duplicates("Symbol").reset_index(drop=True)
    h = symbol_hash(df["Symbol"])
    if len(df) != EXPECTED_THIRD_COUNT:
        raise RuntimeError(f"Third Holdout: erwartet {EXPECTED_THIRD_COUNT}, gefunden {len(df)}")
    if h != EXPECTED_THIRD_HASH:
        raise RuntimeError(f"THIRD-HOLDOUT-HASH ABWEICHEND. Erwartet {EXPECTED_THIRD_HASH}, gefunden {h}")
    lock = json.loads(LOCK_JSON.read_text(encoding="utf-8"))
    if lock.get("hashes", {}).get("third_holdout_symbol_hash") != EXPECTED_THIRD_HASH:
        raise RuntimeError("0.8.18 Lock enthält nicht den erwarteten Third-Holdout-Hash.")
    hyp = lock.get("hypothesis", {})
    if hyp.get("name") != "H1_BASELINE_061_U70_E70" or hyp.get("company_min") != 70 or hyp.get("entry_min") != 70:
        raise RuntimeError("0.8.18 H1-Lock stimmt nicht.")
    if lock.get("primary_endpoint") != "FIRST_SIGNAL_PER_STOCK_12M":
        raise RuntimeError("0.8.18 Primary Endpoint stimmt nicht.")
    return df, lock

def model_from_info(info):
    sector = str(info.get("sector") or "").lower()
    industry = str(info.get("industry") or "").lower()
    banks = ["banks - diversified", "banks - regional", "regional banks", "diversified banks", "banking services"]
    cap = ["capital markets", "investment banking", "brokerage", "financial data", "financial exchanges", "asset management"]
    if any(x in industry for x in banks): return "BANK"
    if "financial services" in sector and any(x in industry for x in cap): return "CAPITAL_MARKETS"
    if "energy" in sector: return "ENERGY"
    return "STANDARD"

def cache_path(sym):
    return META_CACHE / f'{re.sub(r"[^A-Za-z0-9_.-]", "_", sym)}.pkl'

def get_meta(sym):
    p=cache_path(sym)
    if p.exists():
        try:
            with open(p,"rb") as f: return pickle.load(f)
        except Exception: pass
    err=None
    for i in range(3):
        try:
            t=yf.Ticker(sym)
            try: info=t.get_info()
            except Exception: info=t.info
            if not isinstance(info,dict): info={}
            out={"sector":str(info.get("sector") or ""),"industry":str(info.get("industry") or "")}
            META_CACHE.mkdir(parents=True,exist_ok=True)
            with open(p,"wb") as f: pickle.dump(out,f)
            return out
        except Exception as e:
            err=e; time.sleep(1+i)
    raise err or RuntimeError("Metadaten nicht verfügbar")

def classify(df):
    fixed=[]; todo=[]
    for _,r in df.iterrows():
        sym=norm(r["Symbol"]); sec=str(r.get("Sector","") or ""); sl=sec.lower().strip()
        if sl=="energy": fixed.append((sym,"ENERGY",sec,"Source-Sektor"))
        elif sl in ("financials","financial services","finance") or not sl: todo.append((sym,sec))
        else: fixed.append((sym,"STANDARD",sec,"Source-Sektor"))
    print(f"Financial/unklare Titel für Yahoo-Industrieklassifikation: {len(todo)}")
    if todo:
        with ThreadPoolExecutor(max_workers=min(8,len(todo))) as ex:
            fut={ex.submit(get_meta,s):(s,sec) for s,sec in todo}
            done=0
            for f in as_completed(fut):
                s,sec=fut[f]; done+=1
                try:
                    info=f.result(); m=model_from_info(info)
                    fixed.append((s,m,info.get("sector",""),info.get("industry","")))
                    print(f"  [{done:03}/{len(todo)}] {s:<7} -> {m:<15} | {info.get('industry','')}")
                except Exception:
                    fixed.append((s,"STANDARD",sec,"METADATA_FEHLER")); print(f"  [{done:03}/{len(todo)}] {s:<7} -> STANDARD fallback")
    return pd.DataFrame(fixed,columns=["Symbol","Modell","Sector_Metadata","Industry_Metadata"]).drop_duplicates("Symbol").sort_values("Symbol").reset_index(drop=True)

def write_universe(cls,here):
    models=["STANDARD","BANK","CAPITAL_MARKETS","ENERGY"]
    d={m:cls.loc[cls["Modell"]==m,"Symbol"].tolist() for m in models}
    py="UNIVERSES = "+repr({"third_holdout":d})+"\n\ndef universe_count(u):\n    return sum(len(v) for v in u.values())\n"
    (here/"universe_large.py").write_text(py,encoding="utf-8")
    cls.to_csv(here/"TradePilot_Third_Holdout_Classification_0.8.19.csv",index=False,encoding="utf-8-sig")
    return d

def main():
    here=Path(__file__).resolve().parent
    print("="*120); print("TRADEPILOT 0.8.19 THIRD TRUE HOLDOUT PREPARE"); print("="*120)
    print("H1 U>=70/E>=70 und PRIMARY ENDPOINT FIRST_SIGNAL_PER_STOCK_12M sind aus 0.8.18 eingefroren.")
    print("Keine alternative Score-Schwelle wird gesucht.\n")
    df,lock=validate()
    print(f"Third Holdout: {len(df)} Symbole")
    print(f"Third-Holdout-Hash: {EXPECTED_THIRD_HASH}")
    print("0.8.18 Frozen H1 + Primary Endpoint + PASS-Regel: OK\n")
    cls=classify(df); d=write_universe(cls,here)
    print("\nModellmix: "+" | ".join(f"{k}={len(v)}" for k,v in d.items()))
    print("PREPARE 0.8.19 abgeschlossen.")
if __name__=="__main__": main()
