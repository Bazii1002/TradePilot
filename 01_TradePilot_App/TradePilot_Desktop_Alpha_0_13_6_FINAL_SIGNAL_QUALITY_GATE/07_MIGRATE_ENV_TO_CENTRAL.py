from pathlib import Path
import shutil

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent.parent
CENTRAL = ROOT / ".env"

print("=" * 86)
print("TRADEPILOT 0.6.6.5 - ZENTRALE .env EINRICHTEN")
print("=" * 86)
print(f"Ziel: {CENTRAL}")
print("Es werden keine Schlüsselwerte angezeigt.\n")

if CENTRAL.exists() and CENTRAL.stat().st_size > 0:
    print("OK: Zentrale .env existiert bereits. Keine Änderung vorgenommen.")
    raise SystemExit(0)

candidates = [
    APP_DIR / ".env",
    ROOT / "01_TradePilot_App" / "TradePilot_Desktop_Alpha_0_10_0" / ".env",
]
for candidate in candidates:
    if candidate.exists() and candidate.stat().st_size > 120:
        shutil.copy2(candidate, CENTRAL)
        print(f"OK: Bestehende lokale .env wurde nach {CENTRAL} kopiert.")
        print("Die Quelldatei wurde nicht gelöscht.")
        raise SystemExit(0)

print("BLOCKIERT: Keine befüllte .env automatisch gefunden.")
print("Starte 03_SETUP_ETORO_KEYS.bat, um die Keys verborgen einzugeben.")
raise SystemExit(2)
