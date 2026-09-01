from pathlib import Path

from etoro_readonly import EtoroReadOnlyClient

app = Path(__file__).resolve().parent
client = EtoroReadOnlyClient(app)
print("=" * 88)
print("TRADEPILOT 1.0 UI 0.6.5 - eToro REAL READ-ONLY TEST")
print("=" * 88)
if not client.has_credentials():
    raise SystemExit("STOP: Keine lokalen Keys. Zuerst 03_SETUP_ETORO_KEYS.bat ausführen.")

snap = client.snapshot()
print("Verbindung:              OK")
print("Umgebung:                REAL / READ ONLY")
print("Währung:                 ", snap.get("currency"))
print("Cash/Buying Power:        ", snap.get("cash"))
print("Bonus Credit erkannt:      ", snap.get("bonus_credit"))
print("Invested erkannt:         ", snap.get("invested"))
print("Portfolio Value erkannt:  ", snap.get("equity"))
print("Open P/L erkannt:         ", snap.get("open_pnl"))
print("Account Currency ID:       ", snap.get("account_currency_id"))
print("Today P/L erkannt:        ", snap.get("today_pnl"))
print("Offene Positionen:        ", snap.get("position_count"))
print("Portfolio Envelope:       ", snap.get("portfolio_envelope"))
print("Portfolio Top-Level Keys: ", ", ".join(snap.get("portfolio_top_keys") or []))
print("Portfolio Data Keys:      ", ", ".join(snap.get("data_keys") or []))
print("P/L Data Keys:            ", ", ".join(snap.get("pnl_keys") or []))
if snap.get("pnl_warning"):
    print("P/L Hinweis:              ", snap.get("pnl_warning"))
print("\nKeine Rohdaten, Account-IDs oder Zugangsdaten wurden ausgegeben.")
print("Keine Order wurde gesendet. 0.6.5 enthält ausschließlich GET-Lesezugriffe.")
