# Nifty AI Bot — Simple Setup (v2)

## What changed (your 3 requests, all done)

1. **One command runs everything** — backend + frontend together
2. **Integrated Fyers login** — click a button, no copy-paste tokens
3. **Candles show 24/7** — historical candles load even after market close

---

## ONE-TIME SETUP

### Step 1: Fyers App — set the NEW redirect URL

Go to https://myapi.fyers.in/dashboard → your app → Edit.

**Change the Redirect URL to EXACTLY this:**
```
http://127.0.0.1:8000/api/auth/callback
```

This lets the bot catch your login automatically. Save.

### Step 2: Put your App ID + Secret in config

Open `backend/config.py`, fill in:
```python
"fyers_app_id": "YOUR_APP_ID-100",
"fyers_secret_key": "YOUR_SECRET_KEY",
```
(Leave `fyers_access_token` as-is — it fills automatically now.)

Also set the current month:
```python
"instrument_expiry": "25MAY",   # whatever the current month is
```

---

## RUNNING IT

### Easiest — double-click `START.bat` (Windows)

That's it. It installs everything on first run, starts the server,
and opens your browser to http://localhost:8000.

### Or — one command (any OS):
```
python run.py
```

### Or — manual:
```
cd backend
venv\Scripts\activate.bat        (Windows)
python main.py
```
Then open http://localhost:8000

---

## CONNECTING FYERS (in-app, no copy-paste)

1. Open the app → go to **Settings** tab
2. Click **"Connect Fyers"**
3. A login link appears — click it (or it opens automatically)
4. Login to Fyers + 2FA
5. Browser shows "Connected to Fyers ✓" and auto-closes
6. Bot starts automatically with your token

The token is saved and valid for 15 days. When it expires, just click
"Connect Fyers" again.

---

## CANDLES AFTER MARKET HOURS

Now the chart loads the last session's candles on startup — so you see
candlesticks even when the market is closed (evenings, weekends).

Live ticks only flow during market hours (9:15 AM–3:30 PM IST, Mon–Fri),
but the historical chart is always visible.

If the chart is still empty:
- Make sure you connected Fyers (Settings → Connect Fyers)
- Make sure `instrument_expiry` in config.py is the CURRENT month

---

## ONE PROCESS, NO SEPARATE FRONTEND

When you run `python run.py` (or START.bat), it builds the Flutter web app
and the backend SERVES it. So http://localhost:8000 shows the full dashboard.
No need to run Flutter separately.

(If Flutter isn't installed, the backend still runs the bot — you just won't
have the bundled UI. You can install Flutter later.)

---

## DAILY USE

Just double-click `START.bat` (or `python run.py`).
- If token still valid (within 15 days): bot auto-starts, trades.
- If token expired: open Settings → Connect Fyers → done.

Stop: close the terminal window or press Ctrl+C.
