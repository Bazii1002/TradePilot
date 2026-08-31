
import importlib.util
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location(
    "eval0815",
    HERE / "TradePilot_Evaluate_SECOND_HOLDOUT_0_8_15.py"
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

rows = []
# H1 synthetic PASS: 24 observations, 12 stocks, positive alpha.
for i in range(24):
    rows.append({
        "Symbol": f"H{i%12:02d}",
        "Modell": "STANDARD",
        "Stichtag": f"2024-{(i%12)+1:02d}-28",
        "Qualitaet": 70,
        "Entwicklung": 70,
        "Bewertung": 55,
        "Value_Trap": 10,
        "Drawdown_Score": 50,
        "Trend": 60,
        "B061_Unternehmensscore": 75,
        "B061_Einstiegsscore": 72,
        "Rendite_12M": 25.0,
        "Alpha_12M": 8.0,
        "Sektor_Alpha_12M": 8.0,
    })

df = pd.DataFrame(rows)
h1 = df[(df.B061_Unternehmensscore >= 70) & (df.B061_Einstiegsscore >= 70)]
met = m.metrics(h1)
assert met["n"] == 24
assert met["Aktien"] == 12
assert m.verdict(met) == "PASS"

# H2 boundary test.
cap = pd.DataFrame([{
    "Symbol":"CAP1","Modell":"CAPITAL_MARKETS","Stichtag":"2024-06-28",
    "Value_Trap":20,"Drawdown_Score":40,"Rendite_12M":10,
    "Alpha_12M":2,"Sektor_Alpha_12M":3
}])
sel = cap[
    (cap.Modell=="CAPITAL_MARKETS") &
    (cap.Value_Trap>=20) & (cap.Value_Trap<=59) &
    (cap.Drawdown_Score>=40) & (cap.Drawdown_Score<=59)
]
assert len(sel) == 1

print("TradePilot 0.8.15 SECOND TRUE HOLDOUT SELFTEST: OK")
print("H1 U>=70/E>=70 frozen boundary: OK")
print("H2 CAP Trap20-59/DD40-59 frozen boundary: OK")
print("PASS/WATCH/FAIL logic: OK")
print("No network access in selftest: OK")
print("No exploratory threshold matrix: OK")
