"""
FASTAPI SERVER — All-in-one
============================
Runs everything from ONE process at http://localhost:8000:
  - Bot engine, REST API, WebSocket
  - MCP server (streamable HTTP at /mcp-trading/mcp)
  - Claude AI assistant (POST /api/mcp/chat)
  - Integrated Fyers login (no copy-paste tokens)
  - Serves the Flutter web frontend (if built)

Run:  python main.py
"""

import asyncio
import contextlib
import json
import hashlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv(Path(__file__).parent / ".env")

from bot import NiftyBot
from database import Database
from config import CONFIG
from candle_utils import is_market_open
from trading_mcp.context import refs as mcp_refs
from trading_mcp import claude_agent
from trading_mcp.tools import TOOL_DEFINITIONS, execute_tool

try:
    from api_features import router as features_router, init_features
    FEATURES_AVAILABLE = True
except ImportError:
    features_router = None
    init_features = None
    FEATURES_AVAILABLE = False

try:
    from trading_mcp.server import mcp as trading_mcp_server
    MCP_SERVER_AVAILABLE = True
except ImportError:
    trading_mcp_server = None
    MCP_SERVER_AVAILABLE = False

# Force UTF-8 output so Windows console can print rupee symbol + emojis
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("API")

_LAN = CONFIG.get("backend_lan_host", "192.168.1.2")
_PORT = CONFIG.get("backend_port", 8000)
FYERS_REDIRECT = os.getenv(
    "FYERS_REDIRECT_URI",
    f"http://{_LAN}:{_PORT}/api/auth/callback",
)


class WSManager:
    def __init__(self):
        self.active = []
    async def connect(self, ws):
        await ws.accept()
        self.active.append(ws)
    def disconnect(self, ws):
        if ws in self.active:
            self.active.remove(ws)
    async def broadcast(self, message):
        dead = []
        for c in self.active:
            try: await c.send_json(message)
            except: dead.append(c)
        for d in dead: self.disconnect(d)


manager = WSManager()
db = Database()
bot: Optional[NiftyBot] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot
    db.init()
    bot = NiftyBot(broadcast=manager.broadcast)

    # Wire MCP tool context
    mcp_refs.bot = bot
    mcp_refs.db = db
    mcp_refs.config = CONFIG
    mcp_refs.ws_broadcast = manager.broadcast

    if FEATURES_AVAILABLE and init_features:
        init_features(bot, db)

    async with contextlib.AsyncExitStack() as stack:
        if MCP_SERVER_AVAILABLE and trading_mcp_server:
            await stack.enter_async_context(trading_mcp_server.session_manager.run())
        if CONFIG.get("fyers_access_token") and "FILLED" not in CONFIG["fyers_access_token"]:
            asyncio.create_task(bot.start())
        yield
        if bot and bot.running:
            await bot.stop()


app = FastAPI(title="Nifty AI Bot", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── FYERS AUTH (integrated, no copy-paste) ──
@app.get("/api/auth/url")
async def get_auth_url(mobile: bool = False):
    app_id = CONFIG.get("fyers_app_id", "").strip()
    if not app_id or "YOUR_" in app_id:
        raise HTTPException(400, "Set fyers_app_id in config.py first")
    # USB dev (adb reverse): phone browser must use 127.0.0.1, not LAN IP
    redirect = FYERS_REDIRECT
    if mobile and not os.getenv("FYERS_REDIRECT_URI"):
        redirect = f"http://127.0.0.1:{_PORT}/api/auth/callback"
    url = (f"https://api-t1.fyers.in/api/v3/generate-authcode"
           f"?client_id={app_id}&redirect_uri={redirect}"
           f"&response_type=code&state=niftybot")
    return {"auth_url": url, "redirect_uri": redirect}


@app.get("/api/auth/callback")
async def auth_callback(auth_code: str = "", code: str = "", state: str = ""):
    try:
        received = auth_code or code
        if not received:
            return HTMLResponse("<h2>No auth code received. Try again.</h2>")

        app_id = CONFIG.get("fyers_app_id", "").strip()
        secret = CONFIG.get("fyers_secret_key", "").strip()

        if not app_id or "YOUR_" in app_id:
            return _err_page("App ID not set in config.py")
        if not secret or "YOUR_" in secret:
            return _err_page("Secret Key not set in config.py")

        app_hash = hashlib.sha256(f"{app_id}:{secret}".encode()).hexdigest()
        log.info(f"Auth attempt — app_id='{app_id}' secret_len={len(secret)} secret_starts='{secret[:4]}...'")

        try:
            r = requests.post(
                "https://api-t1.fyers.in/api/v3/validate-authcode",
                json={"grant_type": "authorization_code", "appIdHash": app_hash, "code": received},
                headers={"Content-Type": "application/json"}, timeout=15)
            data = r.json()
        except Exception as e:
            log.error(f"Token exchange network error: {e}")
            return _err_page(f"Network error talking to Fyers: {e}")

        log.info(f"Fyers response: {data}")

        if data.get("s") != "ok":
            return _err_page(f"Fyers rejected: {data.get('message', 'unknown')}<br><br>Check your App ID and Secret Key in config.py")

        token = data.get("access_token")
        if not token:
            return _err_page(f"No token in response: {data}")

        try:
            _save_token(token)
            CONFIG["fyers_access_token"] = token
        except Exception as e:
            log.error(f"Token save error: {e}")
            return _err_page(f"Got token but couldn't save it: {e}")

        # Restart bot with new token (don't let this crash the callback)
        try:
            global bot
            if bot:
                if bot.running:
                    await bot.stop()
                bot = NiftyBot(broadcast=manager.broadcast)
                asyncio.create_task(bot.start())
        except Exception as e:
            log.error(f"Bot restart error: {e}")
            # Token still saved, so report success anyway

        return HTMLResponse("""
            <html><body style="background:#0a0c10;color:#dde1ec;font-family:monospace;text-align:center;padding-top:80px">
            <h1 style="color:#00d97e">Connected to Fyers</h1>
            <p>Token saved. Bot is starting...</p>
            <p style="color:#4a4f62">Close this tab and return to the app.</p>
            <script>setTimeout(()=>window.close(),3000)</script>
            </body></html>""")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        log.error(f"Callback crashed: {tb}")
        return _err_page(f"Unexpected error: {e}")


def _err_page(msg):
    return HTMLResponse(f"""
        <html><body style="background:#0a0c10;color:#dde1ec;font-family:monospace;text-align:center;padding-top:80px">
        <h1 style="color:#ff4757">Connection Failed</h1>
        <p style="color:#f5a623;max-width:600px;margin:0 auto">{msg}</p>
        <p style="color:#4a4f62;margin-top:20px">Check the backend terminal for details, then try again.</p>
        </body></html>""")


@app.post("/api/auth/logout")
async def auth_logout():
    """Clear the saved token and stop the bot so user can reconnect fresh."""
    global bot
    try:
        if bot and bot.running:
            await bot.stop()
    except Exception as e:
        log.error(f"Stop on logout: {e}")
    _save_token("FILLED_AUTOMATICALLY")  # clear token
    CONFIG["fyers_access_token"] = "FILLED_AUTOMATICALLY"
    log.info("Logged out — token cleared")
    return {"ok": True}


@app.get("/api/auth/status")
async def auth_status():
    token = CONFIG.get("fyers_access_token", "")
    valid = bool(token and "FILLED" not in token and "YOUR_" not in token)
    configured = bool(CONFIG.get("fyers_app_id") and "YOUR_" not in CONFIG["fyers_app_id"])
    return {"authenticated": valid, "app_configured": configured}


def _save_token(token):
    import re
    path = Path(__file__).parent / "config.py"
    content = path.read_text(encoding="utf-8")
    content = re.sub(r'"fyers_access_token":\s*"[^"]*"',
                     f'"fyers_access_token": "{token}"', content)
    path.write_text(content, encoding="utf-8")
    log.info("Token saved to config.py")


# ── BOT CONTROL & DATA ──
@app.get("/api/status")
async def status():
    token = CONFIG.get("fyers_access_token", "")
    has_token = bool(token and "FILLED" not in token and "YOUR_" not in token)
    candle_count = len(bot.candles_15m) if bot else 0
    return {
        "running": bot.running if bot else False,
        "uptime": bot.uptime if bot else 0,
        "active_trade": bot.active_trade if bot else None,
        "authenticated": has_token,
        "market_data_ok": candle_count > 0,
        "candle_count": candle_count,
        "current_price": bot.get_display_price() if bot else 0,
        "market_open": is_market_open(),
        "message": (
            "Fyers token expired — reconnect in Settings"
            if has_token and candle_count == 0 and (bot and bot.running)
            else ("Connect Fyers in Settings" if not has_token else None)
        ),
    }

@app.post("/api/bot/start")
async def start_bot():
    if not bot: raise HTTPException(500, "Bot not initialized")
    asyncio.create_task(bot.start())
    return {"ok": True}

@app.post("/api/bot/stop")
async def stop_bot():
    if not bot: raise HTTPException(500, "Bot not initialized")
    await bot.stop()
    return {"ok": True}

@app.get("/api/trades")
async def get_trades(limit: int = 100):
    return db.get_trades(limit=limit)

@app.get("/api/signals")
async def get_signals(limit: int = 50):
    return db.get_signals(limit=limit)

@app.get("/api/stats")
async def get_stats():
    return db.get_stats()

# Timeframe -> Fyers resolution. 3h is resampled from 1h (not native to Fyers).
TF_MAP = {"5m": "5", "15m": "15", "1h": "60", "3h": "60_RESAMPLE3"}

def _resample(candles, factor):
    """Group `factor` candles into one (e.g. 3x 1h -> 1x 3h)."""
    out = []
    for i in range(0, len(candles) - factor + 1, factor):
        chunk = candles[i:i + factor]
        if len(chunk) < factor:
            break
        out.append({
            "time": chunk[0]["time"],
            "open": chunk[0]["open"],
            "high": max(c["high"] for c in chunk),
            "low": min(c["low"] for c in chunk),
            "close": chunk[-1]["close"],
            "volume": sum(c.get("volume", 0) for c in chunk),
        })
    return out

TF_MAP = {"5m": "5", "15m": "15", "1h": "60", "3h": "60_RESAMPLE3"}
_candle_cache: dict = {}  # tf -> {"ts": float, "data": list}


def _merge_forming_bar(candles: list, forming) -> list:
    """Replace last bar with live forming candle when same 15m bucket."""
    if not forming or not candles:
        return candles
    out = list(candles)
    if out and out[-1].get("time") == forming.get("time"):
        broker = out[-1]
        out[-1] = {
            "time": forming["time"],
            "open": broker["open"],
            "high": max(broker["high"], forming.get("high", broker["high"])),
            "low": min(broker["low"], forming.get("low", broker["low"])),
            "close": forming.get("close", broker["close"]),
            "volume": broker.get("volume") or forming.get("volume", 0),
        }
    elif is_market_open() and forming.get("time"):
        out.append(forming)
    return out


@app.get("/api/candles")
async def get_candles(tf: str = "15m", limit: int = 500):
    """Fetch candles for a given timeframe (5m, 15m, 1h, 3h)."""
    if not bot:
        return []

    import time as _time
    from datetime import datetime, timedelta

    limit = min(max(limit, 10), 1000)
    cache_ttl = 45 if tf != "15m" else 15
    cached = _candle_cache.get(tf)
    if cached and (_time.time() - cached["ts"]) < cache_ttl:
        result = cached["data"]
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        days_back = {"5m": 10, "15m": 30, "1h": 90, "3h": 120}.get(tf, 30)
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        res = TF_MAP.get(tf, "15")
        log.info(f"/api/candles tf={tf} symbol={bot.index_symbol} from={from_date} to={today}")
        try:
            if res == "60_RESAMPLE3":
                hourly = bot.broker.get_historical_candles(bot.index_symbol, "60", from_date, today)
                result = _resample(hourly, 3)
            else:
                result = bot.broker.get_historical_candles(bot.index_symbol, res, from_date, today)
            if result is None:
                result = []
            _candle_cache[tf] = {"ts": _time.time(), "data": result}
            log.info(f"/api/candles tf={tf} -> returning {len(result)} candles")
        except Exception as e:
            log.error(f"Candle fetch error ({tf}): {e}")
            if cached:
                result = cached["data"]
            else:
                return []

    if tf == "15m" and bot.current_15m and is_market_open():
        result = _merge_forming_bar(result, bot.current_15m)
    return result[-limit:] if result else []


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        init_candles = bot.candles_15m[-50:] if (bot and bot.candles_15m) else db.get_candles(50)
        await ws.send_json({"type": "init", "data": {
            "candles": init_candles,
            "stats": db.get_stats(),
            "active_trade": bot.active_trade if bot else None,
            "running": bot.running if bot else False,
            "authenticated": bool(CONFIG.get("fyers_access_token") and "FILLED" not in CONFIG.get("fyers_access_token", "")),
            "mcp_configured": claude_agent.is_configured(),
            "current_price": bot.get_display_price() if bot else 0,
            "live_candle": bot.current_15m if bot else None,
            "market_open": is_market_open(),
        }})
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ── MCP / CLAUDE AI ASSISTANT ────────────────────────────────────────────────
class McpChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class McpToolRequest(BaseModel):
    name: str
    arguments: dict = {}


@app.get("/api/mcp/status")
async def mcp_status():
    return {
        "configured": claude_agent.is_configured(),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        "tools_count": len(TOOL_DEFINITIONS),
        "mcp_endpoint": "/mcp-trading/mcp" if MCP_SERVER_AVAILABLE else None,
        "mcp_server_available": MCP_SERVER_AVAILABLE,
    }


@app.get("/api/mcp/tools")
async def mcp_list_tools():
    return {"tools": TOOL_DEFINITIONS}


@app.post("/api/mcp/tools/call")
async def mcp_call_tool(req: McpToolRequest):
    result = await execute_tool(req.name, req.arguments)
    return {"name": req.name, "result": result}


@app.post("/api/mcp/chat")
async def mcp_chat(req: McpChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    result = await claude_agent.chat(req.message.strip(), history=req.history)
    # Broadcast MCP reply to connected dashboards
    await manager.broadcast({
        "type": "mcp_reply",
        "data": {"message": req.message, "reply": result.get("reply"), "tool_calls": result.get("tool_calls", [])},
    })
    return result


# ── EXTENDED FEATURES API (additive — does not modify core bot) ──
if FEATURES_AVAILABLE and features_router:
    app.include_router(features_router, prefix="/api/features")
    log.info("Extended features API mounted at /api/features")


# Mount MCP streamable HTTP server (for external MCP clients: Claude Desktop, Cursor)
if MCP_SERVER_AVAILABLE and trading_mcp_server:
    app.mount("/mcp-trading", trading_mcp_server.streamable_http_app())
    log.info("MCP server mounted at /mcp-trading/mcp")
else:
    log.warning("MCP SDK not installed — pip install 'mcp>=1.27,<2' (requires Python 3.10+)")


# ── SERVE FLUTTER WEB (if built) ──
_web_dir = Path(__file__).parent.parent / "flutter_app" / "build" / "web"
if _web_dir.exists():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="frontend")
    log.info(f"Serving Flutter web from {_web_dir}")
else:
    @app.get("/")
    async def root():
        return HTMLResponse("""
            <html><body style="background:#0a0c10;color:#dde1ec;font-family:monospace;padding:40px">
            <h1 style="color:#00d97e">Nifty AI Bot — Backend Running</h1>
            <p>API live at http://localhost:8000/api/status</p>
            <p style="color:#4a4f62">To see dashboard, build Flutter web:</p>
            <pre style="background:#13161d;padding:14px;border-radius:6px">cd flutter_app
flutter build web</pre>
            <p style="color:#4a4f62">Then refresh. Or run flutter run -d chrome separately.</p>
            </body></html>""")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 55)
    print("  NIFTY AI BOT — all-in-one server")
    print("  Open: http://localhost:8000")
    print("=" * 55 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)