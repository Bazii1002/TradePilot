from getpass import getpass
from pathlib import Path

from etoro_readonly import write_credentials

APP_DIR = Path(__file__).resolve().parent
print("=" * 72)
print("TRADEPILOT 1.0 UI 0.6 - eToro REAL READ-ONLY Zugangsdaten")
print("=" * 72)
print("Die Eingabe wird lokal in .env gespeichert und nicht auf GitHub geladen.")
print("0.6 besitzt KEINEN Order-Endpunkt und kann über eToro nur lesen.\n")
api_key = getpass("eToro API Key (Eingabe verborgen): ").strip()
user_key = getpass("eToro REAL User Key (Eingabe verborgen): ").strip()
write_credentials(APP_DIR / ".env", api_key, user_key)
print("\nOK: .env lokal gespeichert.")
print("Jetzt 04_TEST_ETORO_READONLY.bat ausführen.")
