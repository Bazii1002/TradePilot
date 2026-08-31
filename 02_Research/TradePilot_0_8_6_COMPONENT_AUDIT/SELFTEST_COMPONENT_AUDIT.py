import pandas as pd
from TradePilot_Component_Audit_0_8_6 import audit
rows=[]
for i in range(120):
    q=i%101
    rows.append({
        'Symbol':f'S{i%30:02d}','Modell':['STANDARD','BANK','CAPITAL_MARKETS','ENERGY'][i%4],
        'Stichtag':f'2024-{(i%12)+1:02d}-28','Rendite_12M':q-20,'Alpha_12M':q/2-20,'Sektor_Alpha_12M':q/2-18,
        'Qualitaet':q,'Entwicklung':100-q,'Bewertung':q,'Value_Trap':100-q,'Drawdown_Score':q,'Trend':q,
    })
df=pd.DataFrame(rows)
b,s=audit(df)
assert not b.empty and not s.empty
assert set(['Qualitaet','Entwicklung','Bewertung','Value_Trap','Drawdown_Score','Trend']).issubset(set(b.Komponente))
assert len(s[s.Modell=='ALLE'])==6
print('TradePilot 0.8.6 COMPONENT AUDIT SELFTEST: OK')
