import pandas as pd
import numpy as np
from TradePilot_Interaction_Audit_0_8_7 import interaction_audit, sweet_spot_audit, candidate_shortlist

rows=[]
# 40 Aktien, je 4 Quartale. Bewusst: DD>=80 + Trend 55-79 ist besser.
for i in range(40):
    model=["STANDARD","BANK","CAPITAL_MARKETS","ENERGY"][i%4]
    for q in range(4):
        good=(i%2==0)
        dd=90 if good else 45
        trend=72 if good else 45
        qual=75 if good else 55
        bew=65 if good else 45
        entw=60
        trap=10 if good else 50
        ret=(35 + (i%5)) if good else (-5 + (i%5))
        alpha=ret-12
        rows.append({"Symbol":f"T{i:02d}","Modell":model,"Stichtag":pd.Timestamp(2024,1,1)+pd.Timedelta(days=92*q),
                     "Rendite_12M":ret,"Alpha_12M":alpha,"Sektor_Alpha_12M":alpha+1,
                     "Qualitaet":qual,"Entwicklung":entw,"Bewertung":bew,"Value_Trap":trap,
                     "Drawdown_Score":dd,"Trend":trend})
df=pd.DataFrame(rows)
inter=interaction_audit(df)
sweet=sweet_spot_audit(df)
short=candidate_shortlist(inter,sweet)
r=sweet[(sweet.Modell=="ALLE")&(sweet.Filter=="DD80 + Trend55-79")].iloc[0]
assert r["12M_n"]==80, r
assert r["Alpha_Median"]>10, r
assert bool(r["Stichprobe_OK"]), r
assert len(inter)>0 and len(short)>0
print("TradePilot 0.8.7 INTERACTION AUDIT SELFTEST: OK")
print(f"DD80 + Trend55-79: n={int(r['12M_n'])} | Alpha Med {r['Alpha_Median']:+.1f} | <=-20 {r['Minus20_pct']:.1f}%")
