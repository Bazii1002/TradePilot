from getpass import getpass
from pathlib import Path

from etoro_readonly import write_credentials

APP_DIR = Path(__file__).resolve().parent
print("=" * 72)
print("TRADEPILOT 1.0 UI 0.6.6.2 - eToro REAL Zugangsdaten")
print("=" * 72)
print("Die Eingabe wird lokal in .env gespeichert und nicht auf GitHub geladen.")
print("Zuordnung: API Key = Öffentlicher Key | User-Key = Privater Key.\n")
public_key = getpass("eToro Öffentlicher Key (API Key, Eingabe verborgen): ").strip()
private_key = getpass("eToro Privater Key (User-Key, Eingabe verborgen): ").strip()
write_credentials(APP_DIR / ".env", public_key, private_key)
print("\nOK: .env lokal gespeichert.")
print("OK: x-api-key <- Öffentlicher Key | x-user-key <- Privater Key")
