
from __future__ import annotations
import hashlib, json, pickle, re, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import yfinance as yf

VERSION = "0.8.15 SECOND TRUE HOLDOUT PREPARE"

DATA = Path(r"C:\TradePilot\03_Research_Data")
LOCK_DIR = Path(r"C:\TradePilot\02_Research\TradePilot_0_8_14_SECOND_HOLDOUT_LOCK_UNIVERSE")
SECOND_HOLDOUT = DATA / "TradePilot_Second_Holdout_Universe_0.8.14.csv"
LOCK_JSON = LOCK_DIR / "TradePilot_0_8_14_SECOND_HOLDOUT_LOCK.json"

SEEN_0811 = Path(r"C:\TradePilot\02_Research\TradePilot_0_8_11_TRUE_HOLDOUT_LOCK\TradePilot_0_8_11_SEEN_SYMBOLS.csv")
FIRST_HOLDOUT = DATA / "TradePilot_True_Holdout_Universe_0.8.12.1.csv"

EXPECTED_SECOND_HASH = "63e1f6ca1d5a37bf2ef9ca0fe32134b69896bb52ec9c91f0cb6739fe3b458604"
EXPECTED_SECOND_COUNT = 1339
EXPECTED_FIRST_HASH = "34b38c903865506f8cfb1d80560a6717abf9b33c73ed8c6a2432c52e16fc310c"
EXPECTED_FIRST_COUNT = 999
EXPECTED_DISCOVERY_COUNT = 494

META_CACHE = DATA / "holdout_cache_0_8_15" / "classification"

def norm(s):
    return str(s).strip().upper().replace(".", "-")

def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def load_symbols(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    c = "Symbol" if "Symbol" in df.columns else ("Ticker" if "Ticker" in df.columns else df.columns[0])
    return sorted(set(norm(x) for x in df[c].dropna() if str(x).strip()))

def validate():
    for p in [SECOND_HOLDOUT, LOCK_JSON, SEEN_0811, FIRST_HOLDOUT]:
        if not p.exists():
            raise FileNotFoundError(f"Pflichtdatei fehlt: {p}")

    if sha_file(SECOND_HOLDOUT) != EXPECTED_SECOND_HASH:
        raise RuntimeError(
            "SECOND-HOLDOUT-HASH ABWEICHEND.\n"
            f"Erwartet: {EXPECTED_SECOND_HASH}\n"
            f"Gefunden: {sha_file(SECOND_HOLDOUT)}"
        )

    if sha_file(FIRST_HOLDOUT) != EXPECTED_FIRST_HASH:
        raise RuntimeError("First-Holdout-Hash 0.8.12.1 stimmt nicht mehr.")

    second = load_symbols(SECOND_HOLDOUT)
    first = load_symbols(FIRST_HOLDOUT)
    discovery = load_symbols(SEEN_0811)

    if len(second) != EXPECTED_SECOND_COUNT:
        raise RuntimeError(f"Second Holdout: erwartet {EXPECTED_SECOND_COUNT}, gefunden {len(second)}")
    if len(first) != EXPECTED_FIRST_COUNT:
        raise RuntimeError(f"First Holdout: erwartet {EXPECTED_FIRST_COUNT}, gefunden {len(first)}")
    if len(discovery) != EXPECTED_DISCOVERY_COUNT:
        raise RuntimeError(f"Discovery: erwartet {EXPECTED_DISCOVERY_COUNT}, gefunden {len(discovery)}")

    previous = set(first).union(discovery)
    overlap = sorted(set(second).intersection(previous))
    if overlap:
        raise RuntimeError(f"Second Holdout enthält {len(overlap)} bereits verwendete Symbole: {overlap[:20]}")

    lock = json.loads(LOCK_JSON.read_text(encoding="utf-8"))
    locked_hash = lock.get("second_holdout", {}).get("csv_sha256")
    if locked_hash != EXPECTED_SECOND_HASH:
        raise RuntimeError("0.8.14 Lock enthält nicht den erwarteten Second-Holdout-Hash.")

    frozen = lock.get("frozen_hypotheses", {})
    if set(frozen.keys()) != {"H1_BASELINE_061_U70_E70", "H2_CAP_TRAP20_59_DD40_59"}:
        raise RuntimeError("0.8.14 Frozen Hypotheses stimmen nicht.")

    df = pd.read_csv(SECOND_HOLDOUT, encoding="utf-8-sig")
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    df["Symbol"] = df["Symbol"].map(norm)
    return df, lock

def model_from_info(info):
    sector = str(info.get("sector") or "").lower()
    industry = str(info.get("industry") or "").lower()

    banks = [
        "banks - diversified", "banks - regional", "regional banks",
        "diversified banks", "banking services"
    ]
    cap = [
        "capital markets", "investment banking", "brokerage",
        "financial data", "financial exchanges", "asset management"
    ]

    if any(x in industry for x in banks):
        return "BANK"
    if "financial services" in sector and any(x in industry for x in cap):
        return "CAPITAL_MARKETS"
    if "energy" in sector:
        return "ENERGY"
    return "STANDARD"

def cache_path(sym):
    return META_CACHE / f'{re.sub(r"[^A-Za-z0-9_.-]", "_", sym)}.pkl'

def get_meta(sym):
    p = cache_path(sym)
    if p.exists():
        try:
            with open(p, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass

    err = None
    for i in range(3):
        try:
            t = yf.Ticker(sym)
            try:
                info = t.get_info()
            except Exception:
                info = t.info
            if not isinstance(info, dict):
                info = {}
            out = {
                "sector": str(info.get("sector") or ""),
                "industry": str(info.get("industry") or ""),
            }
            META_CACHE.mkdir(parents=True, exist_ok=True)
            with open(p, "wb") as f:
                pickle.dump(out, f)
            return out
        except Exception as e:
            err = e
            time.sleep(1 + i)
    raise err or RuntimeError("Metadaten nicht verfügbar")

def classify(df):
    fixed = []
    todo = []

    for _, r in df.iterrows():
        sym = norm(r["Symbol"])
        sec = str(r.get("Sector", "") or "")
        sl = sec.lower().strip()

        if sl == "energy":
            fixed.append((sym, "ENERGY", sec, "IWM-Sektor"))
        elif sl in ("financials", "financial services", "finance") or not sl:
            todo.append((sym, sec))
        else:
            fixed.append((sym, "STANDARD", sec, "IWM-Sektor"))

    print(f"Financial/unklare Titel für Yahoo-Industrieklassifikation: {len(todo)}")

    if todo:
        with ThreadPoolExecutor(max_workers=min(8, len(todo))) as ex:
            fut = {ex.submit(get_meta, s): (s, sec) for s, sec in todo}
            done = 0
            for f in as_completed(fut):
                s, sec = fut[f]
                done += 1
                try:
                    info = f.result()
                    m = model_from_info(info)
                    fixed.append((s, m, info.get("sector", ""), info.get("industry", "")))
                    print(f"  [{done:03}/{len(todo)}] {s:<7} -> {m:<15} | {info.get('industry','')}")
                except Exception:
                    fixed.append((s, "STANDARD", sec, "METADATA_FEHLER"))
                    print(f"  [{done:03}/{len(todo)}] {s:<7} -> STANDARD fallback")

    return (
        pd.DataFrame(
            fixed,
            columns=["Symbol", "Modell", "Sector_Metadata", "Industry_Metadata"]
        )
        .drop_duplicates("Symbol")
        .sort_values("Symbol")
        .reset_index(drop=True)
    )

def write_universe(cls, here):
    models = ["STANDARD", "BANK", "CAPITAL_MARKETS", "ENERGY"]
    d = {m: cls.loc[cls["Modell"] == m, "Symbol"].tolist() for m in models}
    py = "UNIVERSES = " + repr({"second_holdout": d}) + "\n\ndef universe_count(u):\n    return sum(len(v) for v in u.values())\n"
    (here / "universe_large.py").write_text(py, encoding="utf-8")
    cls.to_csv(
        here / "TradePilot_Second_Holdout_Classification_0.8.15.csv",
        index=False, encoding="utf-8-sig"
    )
    return d

def main():
    here = Path(__file__).resolve().parent
    print("=" * 118)
    print("TRADEPILOT 0.8.15 SECOND TRUE HOLDOUT PREPARE")
    print("=" * 118)
    print("Nur H1 und H2 sind eingefroren. Keine neue Schwelle wird gesucht.")
    print("H1: 0.6.1 U>=70 / E>=70")
    print("H2: CAPITAL_MARKETS Trap20-59 + DD40-59")
    print()

    df, lock = validate()
    print(f"Second Holdout: {len(df)} Symbole")
    print(f"Second-Holdout-Hash: {EXPECTED_SECOND_HASH}")
    print("Overlap mit Discovery + First Holdout: 0")
    print("0.8.14 Frozen Hypotheses: OK")
    print()

    cls = classify(df)
    d = write_universe(cls, here)

    print()
    print("Modellmix: " + " | ".join(f"{k}={len(v)}" for k, v in d.items()))

    audit = {
        "version": VERSION,
        "second_holdout_hash": EXPECTED_SECOND_HASH,
        "second_holdout_symbols": len(df),
        "overlap_previous": 0,
        "frozen_hypotheses": [
            "H1_BASELINE_061_U70_E70",
            "H2_CAP_TRAP20_59_DD40_59",
        ],
        "rule_blind_model_classification": True,
        "threshold_optimization": False,
    }
    (here / "TradePilot_Second_Holdout_Prepare_Audit_0.8.15.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("universe_large.py erzeugt. PREPARE: OK")
    print("=" * 118)

if __name__ == "__main__":
    main()
