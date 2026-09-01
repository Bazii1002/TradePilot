TradePilot 1.0 UI Prototype 0.5.1 - Runtime Fix

Fixes gegenüber 0.5:
- SVG/Icon-Pfade werden in Main.qml eindeutig aufgelöst.
- QML-Komponenten verwenden URL-Properties statt String-Pfade.
- Backend-Bindings sind beim QML-Shutdown null-sicher.
- Windows-Fontordner wird Qt als Fallback mitgegeben.
- Selftest schlägt jetzt bei Cannot-open/TypeError/ReferenceError-Warnungen fehl.

Weiterhin reiner UI-Prototyp: keine Broker-Order-Ausführung.
