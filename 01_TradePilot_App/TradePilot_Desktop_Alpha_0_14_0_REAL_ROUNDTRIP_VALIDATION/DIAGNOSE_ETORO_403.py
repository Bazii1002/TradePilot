from pathlib import Path
import json, uuid, requests
from etoro_readonly import EtoroReadOnlyClient, BASE_V1, REAL_PORTFOLIO_URL

root=Path(__file__).resolve().parent
c=EtoroReadOnlyClient(root)
api,user=c.credentials()
print('='*84)
print('TRADEPILOT 0.6.2 - eToro 403 DIAGNOSE (READ ONLY)')
print('='*84)
print('Credentials vorhanden: ', bool(api and user))
print('Öffentlicher Key Länge:         ', len(api))
print('Privater Key Länge:        ', len(user))
print('Basis-URL:              ', BASE_V1)
print('Portfolio-URL:          ', REAL_PORTFOLIO_URL)
print('Es werden KEINE Keys ausgegeben und KEINE Orders gesendet.\n')

headers=c._headers()
try:
    r=c.session.get(REAL_PORTFOLIO_URL, headers=headers, timeout=20, allow_redirects=False)
    print('HTTP Status:            ', r.status_code)
    print('Content-Type:           ', r.headers.get('content-type','-'))
    print('Server:                 ', r.headers.get('server','-'))
    print('CF-Ray:                 ', r.headers.get('cf-ray','-'))
    print('Location/Redirect:      ', r.headers.get('location','-'))
    print('Antwortformat:           ', 'JSON' if 'json' in r.headers.get('content-type','').lower() else 'nicht JSON')
    if r.ok:
        print('\nERGEBNIS: API erreichbar. Der 403 war vermutlich temporaer bzw. Header-bezogen.')
    elif r.status_code == 403 and ('cloudflare' in r.headers.get('server','').lower() or 'html' in r.headers.get('content-type','').lower()):
        print('\nERGEBNIS: Cloudflare blockiert die Anfrage VOR der eToro-API.')
        print('Das spricht gegen einen normalen Credential-Fehler.')
        print('Nicht mehrfach schnell wiederholen; CF-Ray fuer eToro-Support notieren.')
    elif r.status_code in (401,403):
        print('\nERGEBNIS: eToro/API lehnt Authentifizierung oder Berechtigung ab.')
        print('Öffentlichen Key und Privaten Key und API-Portal-Berechtigungen pruefen.')
    else:
        print('\nERGEBNIS: Unerwarteter HTTP-Status; bitte komplette Ausgabe schicken.')
except Exception as e:
    print('NETZWERKFEHLER:', type(e).__name__, str(e))
