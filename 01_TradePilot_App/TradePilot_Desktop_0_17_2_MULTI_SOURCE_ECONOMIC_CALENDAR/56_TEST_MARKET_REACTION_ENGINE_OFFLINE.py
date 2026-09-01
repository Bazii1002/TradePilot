from macro_logic import market_regime_from_moves
print('='*108)
print('TRADEPILOT 0.17.0 - MARKET REACTION ENGINE OFFLINE')
print('='*108)
riskoff=market_regime_from_moves({'NASDAQ':-1.2,'S&P 500':-0.8,'VIX':9.0,'US10Y':12.0,'OIL':1.0})
riskon=market_regime_from_moves({'NASDAQ':0.9,'S&P 500':0.7,'VIX':-7.0,'US10Y':-7.0,'OIL':-0.5})
incomplete=market_regime_from_moves({'NASDAQ':1.0,'S&P 500':None,'VIX':None,'US10Y':None,'OIL':None})
assert riskoff['regime']=='RISK-OFF'
assert riskon['regime']=='RISK-ON'
assert incomplete['regime']=='NEUTRAL' and not incomplete['complete']
print('Nasdaq / S&P 500 / VIX / US10Y / Oil inputs: OK')
print('Confirmed negative reaction -> RISK-OFF: OK')
print('Confirmed positive reaction -> RISK-ON: OK')
print('Incomplete reaction data -> NEUTRAL, never synthetic RISK-ON: OK')
print('Broker POST: NICHT VERWENDET')
print('STATUS: MARKET REACTION ENGINE OFFLINE OK')
