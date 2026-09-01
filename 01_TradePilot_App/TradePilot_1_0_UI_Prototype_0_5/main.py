import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, QDateTime, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

VERSION = "1.0 UI Prototype 0.5"


class Backend(QObject):
    timeChanged = Signal()

    def __init__(self):
        super().__init__()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.timeChanged)
        self._timer.start(1000)

    @Property(str, notify=timeChanged)
    def marketTime(self):
        return QDateTime.currentDateTime().toString("h:mm:ss AP")

    @Property(str, notify=timeChanged)
    def dateText(self):
        return QDateTime.currentDateTime().toString("MMM d, yyyy")

    @Property(str, constant=True)
    def version(self):
        return VERSION

    @Slot(str)
    def navigationClicked(self, page):
        print(f"[UI PROTOTYPE 0.5] navigation -> {page}")


def main():
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("TradePilot")
    app.setOrganizationName("TradePilot")

    engine = QQmlApplicationEngine()
    backend = Backend()
    engine.rootContext().setContextProperty("backend", backend)

    qml = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(str(qml))
    if not engine.rootObjects():
        raise SystemExit("QML konnte nicht geladen werden.")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
