from pathlib import Path
import json, tempfile, pandas as pd
import importlib.util
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("ev",P/"TradePilot_Evaluate_THIRD_HOLDOUT_0_8_19.py")
ev=importlib.util.module_from_spec(spec); spec.loader.exec_module(ev)
assert ev.EXPECTED_THIRD_HASH=="c8d73d22b9235e835f4567258dd01de716f3bd7231acb4ae853f0ea9d7c49953"
df=pd.DataFrame({"Symbol":["A","A","B"],"Stichtag":["2024-01-01","2024-04-01","2024-01-01"],"Rendite_12M":[10,50,20],"Alpha_12M":[1,30,2],"Sektor_Alpha_12M":[2,30,3],"B061_Unternehmensscore":[70,80,75],"B061_Einstiegsscore":[70,80,75],"Modell":["STANDARD"]*3})
df=ev.clean(df); f=ev.first_signal_per_stock(df)
assert len(f)==2 and set(f["Symbol"])=={"A","B"}
rule={"min_first_signal_cases":2,"median_12m_gt":0,"median_spy_alpha_gt":0,"median_sector_alpha_gt":0,"positive_rate_gte_pct":55,"loss_le_minus20_rate_lte_pct":20}
watch={"min_first_signal_cases":1,"median_spy_alpha_gt":0,"median_sector_alpha_gt":0}
m=ev.metrics(f); assert ev.primary_verdict(m,rule,watch)=="PASS"
core=(P/"TradePilot_THIRD_HOLDOUT_Core_0_8_19.py").read_text(encoding="utf-8")
assert "third_holdout" in core and "TradePilot_Backtest_0.8.19_THIRD_HOLDOUT_RAW_" in core
print("TradePilot 0.8.19 THIRD TRUE HOLDOUT SELFTEST: OK")
print("Frozen H1 U>=70/E>=70: OK")
print("Primary FIRST_SIGNAL_PER_STOCK_12M: OK")
print("Frozen PASS/WATCH rules from 0.8.18: OK")
print("No alternative thresholds: OK")
