"""
═══════════════════════════════════════════════════════════════
NIFTY 50 AI BOT — CONFIGURATION
═══════════════════════════════════════════════════════════════

Fill in your keys below. Start in PAPER trading mode.
Run paper for 2-4 weeks before switching to LIVE.

Claude API key: set ANTHROPIC_API_KEY in backend/.env (not here).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

CONFIG = {
    # ═══ BROKER ═══════════════════════════════════════════════════════
    "broker": "fyers",   # currently only Fyers supported, add Upstox/Zerodha later

    # ═══ FYERS API ════════════════════════════════════════════════════
    # 1. Register app at https://myapi.fyers.in/dashboard
    # 2. Redirect URLs (add BOTH in Fyers app dashboard):
    #    http://127.0.0.1:8000/api/auth/callback  (desktop)
    #    http://192.168.1.2:8000/api/auth/callback  (mobile on same Wi‑Fi)
    # 3. Run: python fyers_auth.py (refreshes every 15 days)
    "fyers_app_id": "5LITWFWCEU-100",          # e.g. "ABC123-100"
    "fyers_secret_key": "EWTZ6L9L9C",       # 32-char string
    "fyers_access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiZDoxIiwiZDoyIiwieDowIiwieDoxIiwieDoyIl0sImF0X2hhc2giOiJnQUFBQUFCcUpQOGJzTkNoYXhjQ0o5QzBWa2VfdnBaVkkwOWpIT0xHcVBkbGZjTVk2WEJuVmJzcVdKSUxKN3R0SDJPUzIySFpwUHFnTDJ5N09ETjA0clNQTDdYNm0yTEI5OGJ0Z3pjNGw0RGhrU0RtcGRpUUtjMD0iLCJkaXNwbGF5X25hbWUiOiIiLCJvbXMiOiJLMSIsImhzbV9rZXkiOiJlNTk5M2JiNWMxMGU0MTM3YjU0YzIyNTdkODg2NTljZGZlMTE2YmRiMjkwNmNjZjI4YjI4YmY1YSIsImlzRGRwaUVuYWJsZWQiOiJOIiwiaXNNdGZFbmFibGVkIjoiWSIsImZ5X2lkIjoiRkFGOTUyNTAiLCJhcHBUeXBlIjoxMDAsImV4cCI6MTc4MDg3ODYwMCwiaWF0IjoxNzgwODA5NDk5LCJpc3MiOiJhcGkuZnllcnMuaW4iLCJuYmYiOjE3ODA4MDk0OTksInN1YiI6ImFjY2Vzc190b2tlbiJ9.Zt6PUPBkWWXCLC_0zdHAquV481l-2RW7BSgzFEZZGzU",

    # ═══ CLAUDE AI (MCP assistant) ═══════════════════════════════════
    # Set ANTHROPIC_API_KEY in backend/.env — never commit the key.
    "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),

    # ═══ INSTRUMENT ══════════════════════════════════════════════════
    "instrument_symbol": "NIFTY",     # NIFTY / BANKNIFTY / FINNIFTY
    "instrument_expiry": "26JUN",     # Update monthly: 26JUN / 26JUL / 26AUG

    # ═══ NETWORK (for mobile app + Fyers OAuth from phone) ═══════════
    # Your Mac's LAN IP — phone must reach this. Run: ipconfig getifaddr en0
    "backend_lan_host": os.getenv("BACKEND_LAN_HOST", "192.168.1.2"),
    "backend_port": 8000,

    # ═══ TRADING MODE ════════════════════════════════════════════════
    "paper_trading": True,            # ← START HERE. Real money: set False
    "product_type": "INTRADAY",       # INTRADAY / CNC / MARGIN
    "order_type": "LIMIT",            # LIMIT / MARKET
    "limit_offset_pts": 2,            # Points above/below LTP for limit orders

    # ═══ CAPITAL & RISK ══════════════════════════════════════════════
    "capital": 100000,                # ₹1 lakh starting capital
    "risk_per_trade_pct": 1.0,        # Max 1% capital at risk per trade
    "max_trades_per_day": 3,          # Hard cap
    "max_daily_loss_pct": 2.5,        # Stops trading at -2.5%
    "max_weekly_loss_pct": 5.0,       # Pauses for week at -5%
    "min_confidence": 75,
    "min_signal_score": 55,    # Bot decision threshold (lower=more trades, higher=fewer/better)             # Skip signals below 75%
    "min_risk_reward": 1.5,           # Skip R:R below 1:1.5
    "min_sl_points": 20,              # Reject SL tighter than 20pts
    "max_sl_points": 60,              # Reject SL wider than 60pts

    # ═══ SESSION WINDOW (IST) ════════════════════════════════════════
    "trading_start": "09:30",         # Skip 9:15-9:30 chaos
    "trading_end": "14:30",           # No new trades after 2:30 PM

    # ═══ STRATEGY ════════════════════════════════════════════════════
    "primary_timeframe": "15",        # 15-min candles
    "higher_timeframe": "60",         # 1-hour for confluence

    # ═══ NEWS BLACKOUTS (±15 min around scheduled events) ════════════
    "news_events": [
        # Add upcoming events here:
        # "2025-02-07 14:30",  # RBI policy
        # "2025-02-01 11:00",  # Budget speech
    ],

    # ═══ NOTIFICATIONS (Telegram) ═════════════════════════════════════
    # Optional. Setup:
    # 1. Message @BotFather on Telegram → /newbot → get token
    # 2. Message your bot once, then visit:
    #    https://api.telegram.org/bot<TOKEN>/getUpdates → get chat_id
    "telegram_bot_token": "",
    "telegram_chat_id": "",
}
