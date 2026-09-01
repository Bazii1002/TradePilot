from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from etoro_readonly import EtoroReadOnlyClient
from etoro_live_manual import EtoroManualLiveBroker
from exchange_status import get_exchange_status, format_countdown
from history_store import PortfolioHistoryStore

VERSION = "1.0 UI Prototype 0.6.6 · Manual LIVE Execution Bridge"
APP_DIR = Path(__file__).resolve().parent


def _money(value, currency="USD", signed=False):
    if value is None:
        return "—"
    try:
        value = float(value)
    except Exception:
        return "—"
    sign = "+" if signed and value > 0 else ""
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(str(currency).upper(), "")
    suffix = "" if symbol else f" {str(currency).upper()}"
    return f"{sign}{symbol}{value:,.2f}{suffix}"


def _pct(value, signed=True):
    if value is None:
        return "—"
    try:
        value = float(value)
    except Exception:
        return "—"
    # APIs vary between 0.0141 and 1.41. Keep plausible percent values readable.
    if abs(value) <= 0.25:
        value *= 100.0
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.2f}%"


def _position_activity(rows: list[dict], currency: str) -> list[dict]:
    out = []
    for row in rows[:5]:
        pnl = row.get("pnl")
        units = row.get("units")
        details = []
        if units is not None:
            try:
                details.append(f"{float(units):g} Units")
            except Exception:
                pass
        if pnl is not None:
            details.append(f"P/L {_money(pnl, currency, signed=True)}")
        out.append({
            "symbol": str(row.get("symbol") or "POSITION"),
            "company": str(row.get("company") or ""),
            "side": "OPEN",
            "amount": _money(row.get("value"), currency),
            "shares": " · ".join(details) if details else "Offene Position",
            "time": "",
        })
    return out


class Backend(QObject):
    clockChanged = Signal()
    dataChanged = Signal()
    refreshResult = Signal(object, str)
    liveChanged = Signal()

    def __init__(self):
        super().__init__()
        self.client = EtoroReadOnlyClient(APP_DIR)
        self.live = EtoroManualLiveBroker(APP_DIR)
        self.history = PortfolioHistoryStore(APP_DIR)
        self._refreshing = False
        self._connected = False
        self._status = "eToro nicht konfiguriert" if not self.client.has_credentials() else "eToro wird verbunden …"
        self._last_refresh = "Noch nicht aktualisiert"
        self._last_error = ""
        self._last_success_utc = None
        self._refresh_interval_seconds = 60
        self._currency = "USD"
        self._cash = None
        self._invested = None
        self._equity = None
        self._today_pnl = None
        self._today_pct = None
        self._positions: list[dict] = []
        self._chart_points: list[float] = []
        self._prepared_live: dict | None = None
        self._live_status = "Manueller LIVE-Test bereit · max. 10 €"
        self._live_busy = False

        self.refreshResult.connect(self._apply_refresh_result)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(1000)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refreshData)
        self._refresh_timer.start(self._refresh_interval_seconds * 1000)

        if self.client.has_credentials():
            QTimer.singleShot(350, self.refreshData)

    def _tick(self):
        # Clock changes also update freshness/stale indicators in QML.
        self.clockChanged.emit()
        self.dataChanged.emit()

    def _age_seconds(self):
        if self._last_success_utc is None:
            return None
        return max(0.0, (datetime.now(ZoneInfo("UTC")) - self._last_success_utc).total_seconds())

    @Property(str, constant=True)
    def version(self):
        return VERSION

    @Property(str, notify=clockChanged)
    def marketTime(self):
        return datetime.now(ZoneInfo("America/New_York")).strftime("%-I:%M:%S %p") if os.name != "nt" else datetime.now(ZoneInfo("America/New_York")).strftime("%I:%M:%S %p").lstrip("0")

    @Property(str, notify=clockChanged)
    def dateText(self):
        return datetime.now(ZoneInfo("America/New_York")).strftime("%b %d, %Y").replace(" 0", " ")

    def _market(self, code: str) -> dict:
        try:
            return get_exchange_status(code)
        except Exception:
            return {"is_open": False, "event": "OPEN", "seconds": 0}

    @Property(bool, notify=clockChanged)
    def nyseOpen(self): return bool(self._market("NYSE").get("is_open"))

    @Property(bool, notify=clockChanged)
    def nasdaqOpen(self): return bool(self._market("NASDAQ").get("is_open"))

    @Property(bool, notify=clockChanged)
    def xetraOpen(self): return bool(self._market("XETRA").get("is_open"))

    def _market_state(self, code: str) -> str:
        return "Open" if self._market(code).get("is_open") else "Closed"

    def _market_sub(self, code: str) -> str:
        status = self._market(code)
        event = "schließt" if status.get("is_open") else "öffnet"
        return f"{event} in {format_countdown(status.get('seconds', 0), 'de')}"

    @Property(str, notify=clockChanged)
    def nyseState(self): return self._market_state("NYSE")
    @Property(str, notify=clockChanged)
    def nasdaqState(self): return self._market_state("NASDAQ")
    @Property(str, notify=clockChanged)
    def xetraState(self): return self._market_state("XETRA")
    @Property(str, notify=clockChanged)
    def nyseSub(self): return self._market_sub("NYSE")
    @Property(str, notify=clockChanged)
    def nasdaqSub(self): return self._market_sub("NASDAQ")
    @Property(str, notify=clockChanged)
    def xetraSub(self): return self._market_sub("XETRA")

    @Property(bool, notify=dataChanged)
    def brokerConnected(self): return self._connected

    @Property(str, notify=dataChanged)
    def brokerStatusText(self):
        age = self._age_seconds()
        if self._connected and age is not None and age <= 120:
            return "eToro REAL · LIVE"
        if self._equity is not None:
            return "eToro REAL · STALE"
        return self._status

    @Property(bool, notify=dataChanged)
    def dataFresh(self):
        age = self._age_seconds()
        return bool(self._connected and age is not None and age <= 120)

    @Property(str, notify=dataChanged)
    def freshnessText(self):
        age = self._age_seconds()
        if age is None:
            return "Noch keine Live-Daten"
        if self._connected and age <= 120:
            return "LIVE · vor " + (f"{int(age)} Sek." if age < 60 else f"{int(age//60)} Min.")
        return "STALE · letzter Erfolg vor " + (f"{int(age//60)} Min." if age < 3600 else f"{int(age//3600)} Std.")

    @Property(str, notify=dataChanged)
    def lastRefreshText(self): return self._last_refresh

    @Property(str, notify=dataChanged)
    def lastErrorText(self): return self._last_error

    @Property(str, notify=dataChanged)
    def cashText(self): return _money(self._cash, self._currency)

    @Property(str, notify=dataChanged)
    def investedText(self): return _money(self._invested, self._currency)

    @Property(str, notify=dataChanged)
    def portfolioText(self): return _money(self._equity, self._currency)

    @Property(str, notify=dataChanged)
    def todayText(self): return _money(self._today_pnl, self._currency, signed=True)

    @Property(str, notify=dataChanged)
    def todayPctText(self): return _pct(self._today_pct)

    @Property(bool, notify=dataChanged)
    def todayAvailable(self): return self._today_pnl is not None

    @Property(str, notify=dataChanged)
    def investedPctText(self):
        if self._equity not in (None, 0) and self._invested is not None:
            return f"{max(0.0, self._invested / self._equity * 100):.1f}% of Portfolio"
        return "—"

    @Property(str, notify=dataChanged)
    def openPositionCountText(self):
        n = len(self._positions)
        return f"{n} offene Position" + ("" if n == 1 else "en")

    @Property(str, notify=dataChanged)
    def activityTitle(self): return "Open Positions"

    @Property(str, notify=dataChanged)
    def activityRowsJson(self):
        return json.dumps(_position_activity(self._positions, self._currency), ensure_ascii=False)

    @Property(bool, notify=dataChanged)
    def chartReady(self): return len(self._chart_points) >= 2

    @Property(str, notify=dataChanged)
    def portfolioChartJson(self): return json.dumps(self._chart_points)

    @Property(str, notify=dataChanged)
    def allocationInvestedValue(self): return _money(self._invested, self._currency)

    @Property(str, notify=dataChanged)
    def allocationCashValue(self): return _money(self._cash, self._currency)

    @Property(str, notify=dataChanged)
    def allocationInvestedPct(self):
        if self._equity not in (None, 0) and self._invested is not None:
            return f"{max(0.0, self._invested / self._equity * 100):.1f}%"
        return "—"

    @Property(str, notify=dataChanged)
    def allocationCashPct(self):
        if self._equity not in (None, 0) and self._cash is not None:
            return f"{max(0.0, self._cash / self._equity * 100):.1f}%"
        return "—"

    @Property(float, notify=dataChanged)
    def allocationInvestedFraction(self):
        if self._equity not in (None, 0) and self._invested is not None:
            return min(1.0, max(0.0, self._invested / self._equity))
        return 0.0

    @Property(str, notify=liveChanged)
    def liveStatusText(self):
        return self._live_status

    @Property(bool, notify=liveChanged)
    def liveBusy(self):
        return self._live_busy

    @Property(bool, notify=liveChanged)
    def livePrepared(self):
        return isinstance(self._prepared_live, dict)

    @Property(str, notify=liveChanged)
    def liveReviewText(self):
        p = self._prepared_live
        if not isinstance(p, dict):
            return "Noch keine LIVE-Order vorbereitet."
        return (
            f"eToro REAL\n\n"
            f"Ticker: {p['symbol']}\n"
            f"Instrument-ID: {p['instrument_id']}\n"
            f"Aktion: BUY · Market\n"
            f"Hebel: 1x\n\n"
            f"TradePilot-Budget: {p['budget_eur']:.2f} EUR\n"
            f"EUR/USD: {p['eurusd']:.5f}\n"
            f"eToro-Orderbetrag: {p['amount_usd']:.2f} USD\n\n"
            "TradePilot erhöht den Betrag NICHT automatisch.\n"
            "AutoTrader → REAL bleibt gesperrt."
        )

    @Slot(str, float, result=bool)
    def prepareLiveBuy(self, symbol, amount_eur):
        if self._live_busy:
            return False
        self._live_busy = True
        self._live_status = "LIVE-Order wird vorbereitet …"
        self._prepared_live = None
        self.liveChanged.emit()
        try:
            self._prepared_live = self.live.prepare_market_buy(symbol, amount_eur)
            self._live_status = "Vorbereitet · bitte Daten prüfen und LIVE eingeben"
            return True
        except Exception as exc:
            self._live_status = "BLOCKIERT: " + str(exc)
            return False
        finally:
            self._live_busy = False
            self.liveChanged.emit()

    @Slot(str, result=bool)
    def executePreparedLiveBuy(self, confirmation):
        if self._live_busy:
            return False
        if str(confirmation or "").strip().upper() != "LIVE":
            self._live_status = "Nicht gesendet: Bestätigung muss exakt LIVE lauten."
            self.liveChanged.emit()
            return False
        if not isinstance(self._prepared_live, dict):
            self._live_status = "Nicht gesendet: Keine vorbereitete LIVE-Order."
            self.liveChanged.emit()
            return False
        self._live_busy = True
        self._live_status = "ECHTGELD-Order wird an eToro gesendet …"
        self.liveChanged.emit()
        prepared = dict(self._prepared_live)
        self._prepared_live = None
        try:
            result = self.live.place_prepared(prepared)
            response = result.get("response") if isinstance(result, dict) else None
            order_id = None
            if isinstance(response, dict):
                order_id = response.get("orderId") or (response.get("data") or {}).get("orderId") if isinstance(response.get("data"), dict) else response.get("orderId")
            self._live_status = f"GESENDET: {result['symbol']} · {result['budget_eur']:.2f} EUR" + (f" · Order {order_id}" if order_id else "")
            # Pull broker state shortly after submission; actual fill/position is authoritative.
            QTimer.singleShot(2500, self.refreshData)
            return True
        except Exception as exc:
            self._live_status = "FEHLER/ABGELEHNT: " + str(exc)
            return False
        finally:
            self._live_busy = False
            self.liveChanged.emit()

    @Slot()
    def cancelPreparedLiveBuy(self):
        self._prepared_live = None
        self._live_status = "LIVE-Vorbereitung verworfen."
        self.liveChanged.emit()

    @Slot(str)
    def navigationClicked(self, page):
        print(f"[TradePilot 0.6.6] navigation -> {page}")

    @Slot()
    def refreshData(self):
        if self._refreshing:
            return
        if not self.client.has_credentials():
            self._connected = False
            self._status = "eToro nicht konfiguriert"
            self._last_error = "03_SETUP_ETORO_KEYS.bat ausführen"
            self.dataChanged.emit()
            return
        self._refreshing = True
        self._status = "eToro wird aktualisiert …"
        self.dataChanged.emit()

        def worker():
            try:
                snapshot = self.client.snapshot()
                self.refreshResult.emit(snapshot, "")
            except Exception as exc:
                self.refreshResult.emit({}, str(exc))

        threading.Thread(target=worker, daemon=True, name="etoro-readonly-refresh").start()

    @Slot(object, str)
    def _apply_refresh_result(self, snapshot, error):
        self._refreshing = False
        if error:
            self._connected = False
            self._status = "eToro REAL · OFFLINE"
            self._last_error = error
            self._last_refresh = datetime.now().strftime("%H:%M:%S") + " · Fehler"
            self.dataChanged.emit()
            return
        self._connected = True
        self._status = "eToro REAL · LIVE"
        self._last_success_utc = datetime.now(ZoneInfo("UTC"))
        self._last_error = snapshot.get("pnl_warning") or ""
        self._currency = str(snapshot.get("currency") or "USD").upper()
        self._cash = snapshot.get("cash")
        self._invested = snapshot.get("invested")
        self._equity = snapshot.get("equity")
        self._today_pnl = snapshot.get("today_pnl")
        self._today_pct = snapshot.get("today_pct")
        self._positions = list(snapshot.get("positions") or [])
        rows = self.history.append(self._equity, self._cash, self._invested, snapshot.get("open_pnl"), self._today_pnl, len(self._positions))
        self._chart_points = self.history.normalized_points(rows)
        self._last_refresh = datetime.now().strftime("%H:%M:%S")
        self.dataChanged.emit()


def main():
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    if os.name == "nt" and Path(r"C:\Windows\Fonts").exists():
        os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("TradePilot")
    app.setOrganizationName("TradePilot")

    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)

    qml = APP_DIR / "qml" / "Main.qml"
    engine.load(str(qml))
    if not engine.rootObjects():
        raise SystemExit("QML konnte nicht geladen werden.")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
