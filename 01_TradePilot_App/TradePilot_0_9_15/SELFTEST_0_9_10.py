"""Offline core self-test for TradePilot 0.9.10."""
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from exchange_status import get_exchange_status
from order_engine import validate_pending_execution
from paper_broker import PaperBroker
from performance_engine import performance_metrics, risk_overview
from risk_manager import calculate_position


def quote(price, fresh=True, session_open=True):
    return {
        "price": float(price), "fresh": bool(fresh), "session_open": bool(session_open),
        "quote_time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "provider": "SELFTEST",
    }


def analysis(price=100.0, company=90, entry=80, trap=0, volatile=False):
    if volatile:
        vals=[100,120,85,130,80,140,75,145,90,135,82,142,88,150,91,145,84,151,90,149,95,148,92,152,94,150,96,151,98,150]
    else:
        vals=[95+i*0.2 for i in range(30)]
    idx=pd.date_range("2026-07-01", periods=len(vals), freq="B")
    return {
        "symbol":"TEST","name":"Test Inc.","sector":"Technology",
        "unternehmensscore":company,"einstieg_score":entry,"trap_score":trap,
        "trend":{"kurs":price},"historie":pd.DataFrame({"Close":vals}, index=idx),
    }


def main():
    # Saturday: all displayed exchanges must be closed and have a next-open countdown.
    saturday=datetime(2026,8,29,8,0,tzinfo=timezone.utc)
    for code in ("NYSE","NASDAQ","XETRA","VIE"):
        st=get_exchange_status(code,saturday)
        assert st["is_open"] is False and st["seconds"] > 0

    low=calculate_position(analysis(),"balanced",10000,0,10000,max_trade_value=500)
    assert low["planned_value"] <= 500 + 1e-9
    assert low["signal_multiplier"] <= 1.0
    highvol=calculate_position(analysis(volatile=True),"balanced",10000,0,10000,max_trade_value=1000)
    assert highvol["volatility_multiplier"] <= 1.0

    with TemporaryDirectory() as td:
        broker=PaperBroker(Path(td)/"paper.json",10000,"USD")
        ok,_,oid=broker.queue_buy("TEST","Test Inc.",5,100,"balanced",analysis(),requires_autotrader=False)
        assert ok and oid
        closed=validate_pending_execution(broker,broker._order(oid),quote(100,True,False),max_trade_value=500)
        assert not closed["allowed"] and "MARKET_CLOSED" in closed["blocks"]
        fill=validate_pending_execution(broker,broker._order(oid),quote(100,True,True),slippage_bps=5,max_trade_value=500)
        # Slippage makes 5 x fill slightly greater than 500, therefore the hard cap must block it.
        assert not fill["allowed"] and "MAX_TRADE_VALUE" in fill["blocks"]
        broker.mark_order(oid,"CANCELLED","SELFTEST")

        ok,_,oid=broker.queue_buy("TEST","Test Inc.",4,100,"balanced",analysis(),requires_autotrader=False)
        fill=validate_pending_execution(broker,broker._order(oid),quote(100,True,True),slippage_bps=5,max_trade_value=500)
        assert fill["allowed"]
        ok,_,_=broker.execute_pending(oid,fill["fill_price"],market_price=100,slippage_bps=5)
        assert ok and broker.has_position("TEST")
        broker.update_price("TEST",105,quote_fresh=True)
        broker.record_equity_snapshot("SELFTEST",0)
        m=performance_metrics(broker)
        assert m["equity"] > 10000 and len(m["history"]) >= 2
        ro=risk_overview(broker,"balanced",500)
        assert ro["effective_trade_limit"] <= 500 + 1e-9

    print("TradePilot 0.9.10 CORE SELFTEST: OK")


if __name__ == "__main__":
    main()
