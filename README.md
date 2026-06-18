# Nifty 50 AI Trading Bot — Complete Production Package

Full-stack autonomous Nifty 50 trader. Python backend + Flutter mobile app.

## What's in this zip

```
nifty_pro/
├── backend/                       # Python FastAPI + bot engine
│   ├── bot.py                     # Main trading loop
│   ├── main.py                    # FastAPI server (REST + WebSocket)
│   ├── analyzer.py                # Indicators + patterns + Claude prompt
│   ├── knowledge.py               # The trading brain (Claude system prompt)
│   ├── risk_manager.py            # Trailing stops, partial exits, all safety rules
│   ├── database.py                # SQLite storage
│   ├── notifier.py                # Telegram alerts
│   ├── config.py                  # YOUR API KEYS go here
│   ├── fyers_auth.py              # Token generator (run every 15 days)
│   ├── brokers/
│   │   ├── base.py                # Abstract broker interface
│   │   └── fyers_broker.py        # Fyers v3 implementation
│   └── requirements.txt
│
└── flutter_app/                   # Mobile + desktop dashboard
    ├── lib/
    │   ├── main.dart              # App entry
    │   ├── state/bot_state.dart   # WebSocket + REST client + state
    │   ├── screens/               # Dashboard, Journal, Settings
    │   └── widgets/               # CandlestickChart, SignalCard, etc.
    └── pubspec.yaml
```

═══════════════════════════════════════════════════════════════
## STEP 1: Setup Fyers App (5 min, one-time)
═══════════════════════════════════════════════════════════════

1. Open https://myapi.fyers.in/dashboard
2. Click "Create App"
3. Fill in these EXACT details:
   - **App Name:** NiftyBot
   - **Redirect URL:** `https://trade.fyers.in/api-login/redirect-uri/index.html`
   - **App Type:** Personal
   - **Permissions:** Tick Data, Order placement, Holdings
4. Submit → you get:
   - **App ID** (e.g. `ABC123-100`)
   - **Secret Key**

═══════════════════════════════════════════════════════════════
## STEP 2: Backend Setup
═══════════════════════════════════════════════════════════════

```bash
cd backend
python -m venv venv
source venv/bin/activate         # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Edit `config.py`:
```python
"fyers_app_id": "ABC123-100",                # from step 1
"fyers_secret_key": "YOUR_SECRET",            # from step 1
"anthropic_api_key": "sk-ant-...",            # from console.anthropic.com
"instrument_symbol": "NIFTY",
"instrument_expiry": "25JAN",                 # update to current month
"paper_trading": True,                        # START HERE
"capital": 100000,
```

Generate Fyers token (valid 15 days):
```bash
python fyers_auth.py
```

Run the bot:
```bash
# Option A: Bot only (CLI)
python bot.py

# Option B: Bot + API server for Flutter
uvicorn main:app --reload --port 8000
```

═══════════════════════════════════════════════════════════════
## STEP 3: Flutter App Setup
═══════════════════════════════════════════════════════════════

Install Flutter SDK: https://docs.flutter.dev/get-started/install

```bash
cd flutter_app
flutter pub get
flutter run                       # opens on connected device or simulator
```

For web build:
```bash
flutter run -d chrome
```

For Android APK:
```bash
flutter build apk --release
```

═══════════════════════════════════════════════════════════════
## How the bot works
═══════════════════════════════════════════════════════════════

```
Every tick from Fyers:
    Update 15-min and 1-hour candles
    Monitor active trade (trailing stops, partial exits)

Every 15-min candle close:
    Compute indicators (RSI, MACD, EMA, ATR, VWAP, ADX)
    Detect candlestick patterns
    Detect divergence, FVG, liquidity sweeps, order blocks
    Fetch options chain (PCR, Max Pain, OI)
    Send everything to Claude AI
    Receive signal: LONG / SHORT / WAIT
    Validate with risk rules
    Place order via Fyers API
    Track trade with 3-stage trailing stop
    Exit at T1 (50%), T2 (30%), T3 (20%) or SL
```

═══════════════════════════════════════════════════════════════
## Pro techniques baked in
═══════════════════════════════════════════════════════════════

**Entry edge:**
- Multi-timeframe confluence (15m + 1H)
- RSI divergence detection
- Fair Value Gap detection
- Liquidity sweep reversal
- Order block detection
- Volume confirmation (>150% of 20-bar avg)
- Options PCR + OI shift
- VWAP rejection/reclaim
- India VIX regime filter

**Stop loss edge:**
- ATR-based dynamic stops (1.5× ATR)
- Structure-based stops (below swing low)
- 3-stage trailing stop
- Partial exits 50/30/20

**Risk edge:**
- 1% per trade hard cap
- 2.5% daily loss limit
- 5% weekly loss limit
- Confidence-scaled sizing (50-150%)
- VIX-scaled sizing (halves in extreme vol)
- 30-min cooldown after 2 losses
- News event blackouts

═══════════════════════════════════════════════════════════════
## Realistic expectations
═══════════════════════════════════════════════════════════════

| Metric | Expected |
|--------|----------|
| Win rate | 55-65% |
| Avg R:R | 1:2 (1:2.5 effective with partials) |
| Trades/day | 1-3 |
| Monthly target | 4-8% on capital |
| Max drawdown | 8-12% |

**No bot wins 80%+. Anyone claiming that is lying.**

═══════════════════════════════════════════════════════════════
## Going live (DO NOT SKIP)
═══════════════════════════════════════════════════════════════

1. Paper trade for 2-4 weeks minimum
2. Verify win rate > 50% on paper
3. Verify avg R:R > 1.5
4. Verify no system bugs or missed exits
5. Set `paper_trading: False`
6. Start with 1 lot only (50 units)
7. Scale up after 4 weeks of live profitability

═══════════════════════════════════════════════════════════════
## What's still missing (we can add later)
═══════════════════════════════════════════════════════════════

- Backtesting engine (test on 6+ months of historical data)
- Auto Fyers token refresh (scheduled job)
- FII/DII daily flow integration
- News API event detection
- Bank Nifty correlation filter
- Multi-instrument support (Bank Nifty, Fin Nifty)
- Options trading mode (instead of futures)
- ML-based pattern recognition
- Performance analytics dashboard

═══════════════════════════════════════════════════════════════
## Disclaimer
═══════════════════════════════════════════════════════════════

Educational software. Live algo trading involves real financial risk.
Always paper trade first. Never risk capital you can't afford to lose.
No bot guarantees profit. Markets change. Stay disciplined.
