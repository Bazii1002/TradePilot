from __future__ import annotations
from pathlib import Path
from typing import Any
from etoro_readonly import EtoroReadOnlyClient

SENSITIVE_NAME_PARTS = ("key", "token", "secret", "password", "accountid", "userid", "cid", "email", "phone", "address")

def typename(v: Any) -> str:
    if isinstance(v, dict): return f"object[{len(v)}]"
    if isinstance(v, list): return f"array[{len(v)}]"
    if isinstance(v, bool): return "bool"
    if isinstance(v, (int, float)): return "number"
    if v is None: return "null"
    return "string"

def walk(v: Any, path: str = "$", depth: int = 0, max_depth: int = 5):
    if depth > max_depth:
        return
    if isinstance(v, dict):
        for k in sorted(v.keys(), key=lambda x: str(x).lower()):
            ks = str(k)
            low = "".join(ch for ch in ks.lower() if ch.isalnum())
            child = v[k]
            # Print only path/name + type; never scalar values.
            if any(part in low for part in SENSITIVE_NAME_PARTS):
                print(f"{path}.{ks}: <sensitive-field-name; value hidden>")
            else:
                print(f"{path}.{ks}: {typename(child)}")
            if isinstance(child, dict):
                walk(child, f"{path}.{ks}", depth + 1, max_depth)
            elif isinstance(child, list) and child:
                # Inspect only the first element's schema, never values.
                first = child[0]
                if isinstance(first, (dict, list)):
                    walk(first, f"{path}.{ks}[0]", depth + 1, max_depth)
    elif isinstance(v, list) and v:
        first=v[0]
        if isinstance(first,(dict,list)):
            walk(first,f"{path}[0]",depth+1,max_depth)

app = Path(__file__).resolve().parent
client = EtoroReadOnlyClient(app)
print("="*92)
print("TRADEPILOT 0.6.4 - eToro REAL PAYLOAD SCHEMA (READ ONLY / VALUES HIDDEN)")
print("="*92)
if not client.has_credentials():
    raise SystemExit("STOP: Keine lokalen Keys. Zuerst 03_SETUP_ETORO_KEYS.bat ausführen.")

portfolio = client.portfolio()
pnl, warning = client.pnl_optional()
print("\nPORTFOLIO-SCHEMA (nur Feldpfade + Typen):")
walk(portfolio)
print("\nP/L-SCHEMA (nur Feldpfade + Typen):")
if pnl is None:
    print("<nicht verfügbar>")
    if warning: print("Hinweis:", warning[:300])
else:
    walk(pnl)
print("\nKeine Rohwerte, Account-IDs, Keys oder sonstige Feldwerte wurden ausgegeben.")
print("Keine Order wurde gesendet; nur GET-Lesezugriffe.")
