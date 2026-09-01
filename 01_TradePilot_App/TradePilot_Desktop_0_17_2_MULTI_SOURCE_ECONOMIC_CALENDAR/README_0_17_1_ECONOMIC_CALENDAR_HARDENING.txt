TradePilot 0.17.1 – Economic Calendar Hardening + Live Event Feed

Aufbauend auf 0.17.0. Trading-Strategie und REAL Execution POST bleiben unverändert.

Neu:
- Pure-Python EconomicCalendarProvider ohne Qt-Abhängigkeit
- 14-Tage Abrufhorizont statt nur 3 Tage
- mehrere Payload-Formate/Feldnamen normalisiert
- Dedupe: reichere Duplicate-Zeile gewinnt (Actual/Forecast/Previous)
- chronologische Sortierung
- frischer Calendar Cache als Fallback
- stale Cache wird erkannt und darf fail-closed nicht aggressiver handeln
- nahe Eventfreigabe wird alle 60 Sekunden aktualisiert, sonst alle 5 Minuten
- UI zeigt Feed-Quelle, Event-Anzahl und Event-Countdown
- Live-Diagnostic 62 erzeugt kein QObject/QTimer und damit keine Qt-Lifecycle-Warnung

Sicherheitsregel:
Fehlende/veraltete/unklare Daten können neue Trades blockieren oder begrenzen, aber niemals Risiko reduzieren oder aggressivere Trades freischalten.
Bestehende Positionen werden durch Macro weiterhin nicht hektisch zwangsgeschlossen.
REAL AUTO bleibt LOCKED/OFF.
