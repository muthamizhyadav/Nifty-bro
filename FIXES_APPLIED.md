# FIXES APPLIED — Read This First

## Issue 1: Candlesticks not showing — FIXED + ROOT CAUSE

### Root cause (from your bot.log):
```
[ERROR] WS error: code -300, 'Please provide valid token'
[INFO] Loaded 0 15m + 0 1H candles
```

**Your Fyers token was expired/invalid.** No valid token = no market data = empty chart.
This is the #1 thing to fix. The chart code was fine — it just had no data.

### What I fixed in the code:
- The chart now shows the **live forming candle** in real-time (every tick), not just
  closed candles every 15 minutes. Before, you'd see nothing for the first 15 min.
- Better "Connecting to market feed..." message when no data yet.

### What YOU must do — regenerate your Fyers token:
```cmd
cd backend
venv\Scripts\activate.bat
python fyers_auth.py
```
Token is valid 15 days. If candles still don't show after a fresh token AND
markets are open (9:15 AM–3:30 PM IST Mon-Fri), check your instrument_expiry
in config.py is the CURRENT month (e.g. "25MAY" not "25JAN").

---

## Issue 2: Bot now decides, NOT Claude — FIXED

### What changed:
- **Removed Claude API calls during live trading.** The bot now has its own brain.
- New file: `decision_engine.py` — pure Python rules-based decision system.
- It scores LONG vs SHORT on a points system (trend, momentum, volume, patterns,
  divergence, options, etc.) and only trades when score crosses your threshold.

### Why this is better:
- ✓ Zero API cost during trading (was paying per candle before)
- ✓ Instant decisions (no network round-trip to Claude)
- ✓ Works without internet for the decision logic
- ✓ Fully deterministic & testable — same input = same output

### Claude's new role (offline only):
Claude is now used to DESIGN and REFINE the rules in decision_engine.py.
You no longer need an Anthropic API key to run the bot. (Removed from requirements.)

### Tuning the bot:
In config.py:
```python
"min_signal_score": 55,   # Lower = more trades, Higher = fewer/higher-quality
```
- 50 = aggressive (more trades, more noise)
- 55 = balanced (default)
- 65 = conservative (only A+ setups)

---

## How the bot decides now (the scoring system)

Each direction scored out of ~100:
- Trend alignment: 25 pts (Strong trend) / 15 (trend) / 5 (sideways)
- Above/below VWAP: 10 pts
- RSI momentum with room: 15 pts
- MACD confirmation: 10 pts
- Volume surge: 10 pts
- Candlestick pattern: 15 pts (strong) / 8 (weak)
- RSI divergence: 8 pts
- Liquidity sweep: 7 pts
- Order block: 5 pts
- Fair value gap: 3 pts
- Options PCR: 8 pts
- ADX trend strength: 5 pts

VETOES (skip trade regardless of score):
- ADX < 15 (choppy market)
- RSI 47-53 with flat MACD (no momentum)
- VIX > 30 (extreme volatility)

Plus: won't go LONG if 1H trend is down, won't SHORT if 1H trend is up.

---

## To run after these fixes:

```cmd
cd backend
venv\Scripts\activate.bat
pip install -r requirements.txt
python fyers_auth.py
python bot.py
```

For the dashboard:
```cmd
uvicorn main:app --reload --port 8000
```
Then in another terminal:
```cmd
cd flutter_app
flutter run -d chrome
```
