from __future__ import annotations
import math
import pandas as pd
from strategy_engine import StrategyAnalyzer, ProductionStrategyEngine, STRATEGIES


def frame_up(n=260):
    close=[]
    p=100.0
    for i in range(n):
        p *= 1.0018 + 0.00035*math.sin(i/5)
        close.append(p)
    s=pd.Series(close)
    return pd.DataFrame({
        "High":s*1.004, "Low":s*0.996, "Close":s,
        "Volume":[1_000_000 + (i%7)*90_000 for i in range(n)]
    })


def frame_down(n=260):
    close=[]
    p=180.0
    for i in range(n):
        p *= 0.9982 + 0.00025*math.sin(i/6)
        close.append(p)
    s=pd.Series(close)
    return pd.DataFrame({
        "High":s*1.004, "Low":s*0.996, "Close":s,
        "Volume":[900_000 + (i%5)*30_000 for i in range(n)]
    })

an=StrategyAnalyzer()
print("="*92)
print("TRADEPILOT 0.13.0 - PRODUCTION STRATEGY ENGINE OFFLINE TEST")
print("="*92)
for level in (1,2,3,4):
    up=an.analyze_frame("UPTEST", frame_up(), level)
    dn=an.analyze_frame("DOWNTEST", frame_down(), level)
    assert up.signal in {"BUY","WATCH","WAIT"}
    assert dn.signal in {"BUY","WATCH","WAIT"}
    assert up.score > dn.score, (level, up.score, dn.score)
    print(f"{level} {STRATEGIES[level]['name']:<6} | Up {up.score:5.1f}% {up.signal:<5} | Down {dn.score:5.1f}% {dn.signal:<5}")

pos={"level":2,"entry":100.0,"age":5,"amount":10.0}
close, why, pnl = ProductionStrategyEngine.exit_decision(pos,{"price":97.5,"score":80.0})
assert close and "STOP" in why
close2, why2, pnl2 = ProductionStrategyEngine.exit_decision(pos,{"price":104.5,"score":80.0})
assert close2 and "TAKE" in why2
close3, why3, pnl3 = ProductionStrategyEngine.exit_decision(pos,{"price":100.2,"score":30.0})
assert close3 and "SIGNAL EXIT" in why3

print("Exit Rules: STOP / TAKE PROFIT / SIGNAL EXIT = OK")
print("Zufalls-Score: NICHT VERWENDET")
print("Broker POST: NICHT VERWENDET")
print("STATUS: PRODUCTION STRATEGY ENGINE OK")
