TradePilot 1.0 UI Prototype 0.1
================================

Zweck
-----
Dieser Ordner ist bewusst NUR der neue QML-Frontend-Prototyp.
Er sendet KEINE Broker-Orders und greift NICHT auf eToro-Keys zu.
Die bestehende TradePilot-Python-/Research-/Brokerlogik bleibt getrennt und unverändert.

Warum QML?
----------
Qt Quick/QML ist für die gewünschte moderne Oberfläche besser geeignet als das bisherige klassische QWidget-Layout:
- flexible Cards und Layouts
- weiche Farbverläufe
- moderne Hover-/Animationsmöglichkeiten
- Canvas/Charts
- wiederverwendbare UI-Komponenten

Start
-----
1. 01_SELFTEST_UI.bat
2. Falls PySide6 fehlt: 03_INSTALL_PYSIDE6_IF_NEEDED.bat
3. 02_START_UI_PROTOTYPE.bat

Wichtig
-------
Das Dashboard arbeitet aktuell mit festen Demodaten. Genau das ist Absicht.
Zuerst wird das Design freigegeben. Danach werden echte Backend-Daten angeschlossen.

Referenz
--------
docs\TradePilot_UI_Reference.png
Das Bild dient ausschließlich als visuelle Referenz. Es wird NICHT als Hintergrundbild verwendet.
