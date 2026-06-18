"""MCP tool implementations — shared by FastMCP server and Claude agent."""

import json
from datetime import datetime, timedelta
from typing import Any, Optional

from trading_mcp.context import refs

TF_MAP = {"5m": "5", "15m": "15", "1h": "60", "3h": "60_RESAMPLE3"}


def _resample(candles: list, factor: int) -> list:
    out = []
    for i in range(0, len(candles) - factor + 1, factor):
        chunk = candles[i : i + factor]
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


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


# ── Read-only tools ──────────────────────────────────────────────────────────

def tool_get_bot_status() -> str:
    """Return bot running state, uptime, active trade, and auth status."""
    bot = refs.bot
    cfg = refs.config
    token = cfg.get("fyers_access_token", "")
    authenticated = bool(token and "FILLED" not in token and "YOUR_" not in token)
    if not bot:
        return _json({
            "running": False,
            "uptime_seconds": 0,
            "active_trade": None,
            "authenticated": authenticated,
            "paper_trading": cfg.get("paper_trading", True),
            "instrument": cfg.get("instrument_symbol", "NIFTY"),
        })
    return _json({
        "running": bot.running,
        "uptime_seconds": bot.uptime,
        "active_trade": bot.active_trade,
        "authenticated": authenticated,
        "paper_trading": cfg.get("paper_trading", True),
        "instrument": cfg.get("instrument_symbol", "NIFTY"),
        "index_symbol": getattr(bot, "index_symbol", None),
        "current_price": getattr(bot, "current_price", None) if hasattr(bot, "current_price") else None,
    })


def tool_get_trading_stats() -> str:
    """Return win rate, PnL, trade counts from the database."""
    if not refs.db:
        return _json({"error": "Database not initialized"})
    return _json(refs.db.get_stats())


def tool_get_recent_trades(limit: int = 20) -> str:
    """Return recent closed trades from the journal."""
    if not refs.db:
        return _json({"error": "Database not initialized"})
    limit = max(1, min(limit, 100))
    return _json(refs.db.get_trades(limit=limit))


def tool_get_recent_signals(limit: int = 10) -> str:
    """Return recent trading signals with reasoning."""
    if not refs.db:
        return _json({"error": "Database not initialized"})
    limit = max(1, min(limit, 50))
    return _json(refs.db.get_signals(limit=limit))


def tool_get_candles(timeframe: str = "15m", limit: int = 50) -> str:
    """Fetch OHLCV candles for a timeframe (5m, 15m, 1h, 3h)."""
    bot = refs.bot
    if not bot or not bot.running:
        if refs.db:
            rows = refs.db.get_candles(limit=limit, tf=timeframe)
            return _json({"source": "database", "timeframe": timeframe, "count": len(rows), "candles": rows})
        return _json({"error": "Bot not running and no database candles available"})

    today = datetime.now().strftime("%Y-%m-%d")
    days_back = {"5m": 10, "15m": 30, "1h": 90, "3h": 120}.get(timeframe, 30)
    from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    res = TF_MAP.get(timeframe, "15")
    try:
        if res == "60_RESAMPLE3":
            hourly = bot.broker.get_historical_candles(bot.index_symbol, "60", from_date, today)
            candles = _resample(hourly, 3)
        else:
            candles = bot.broker.get_historical_candles(bot.index_symbol, res, from_date, today)
        result = candles[-limit:] if candles else []
        return _json({"source": "broker", "timeframe": timeframe, "count": len(result), "candles": result})
    except Exception as e:
        return _json({"error": str(e)})


def tool_get_config_summary() -> str:
    """Return non-sensitive trading configuration."""
    cfg = refs.config
    return _json({
        "instrument": cfg.get("instrument_symbol"),
        "expiry": cfg.get("instrument_expiry"),
        "paper_trading": cfg.get("paper_trading"),
        "capital": cfg.get("capital"),
        "risk_per_trade_pct": cfg.get("risk_per_trade_pct"),
        "max_trades_per_day": cfg.get("max_trades_per_day"),
        "max_daily_loss_pct": cfg.get("max_daily_loss_pct"),
        "min_signal_score": cfg.get("min_signal_score"),
        "min_confidence": cfg.get("min_confidence"),
        "min_risk_reward": cfg.get("min_risk_reward"),
        "trading_window": f"{cfg.get('trading_start')} - {cfg.get('trading_end')} IST",
        "primary_timeframe": cfg.get("primary_timeframe"),
    })


def tool_explain_latest_signal() -> str:
    """Explain the most recent signal with full reasoning from the decision engine."""
    if not refs.db:
        return _json({"error": "Database not initialized"})
    signals = refs.db.get_signals(limit=1)
    if not signals:
        return _json({"message": "No signals recorded yet. Wait for a 15m candle close."})
    return _json(signals[0])


def tool_get_market_context() -> str:
    """Return VIX, options PCR, and higher-timeframe trend if bot is live."""
    bot = refs.bot
    if not bot:
        return _json({"error": "Bot not initialized"})
    ctx = {
        "vix": bot.vix_cache,
        "options": bot.options_cache,
        "candles_15m_count": len(bot.candles_15m),
        "candles_1h_count": len(bot.candles_1h),
        "active_trade": bot.active_trade,
    }
    if bot.candles_15m:
        last = bot.candles_15m[-1]
        ctx["last_close"] = last.get("close")
        ctx["last_candle_time"] = last.get("time")
    return _json(ctx)


# ── Action tools (guarded) ───────────────────────────────────────────────────

async def tool_start_bot() -> str:
    """Start the trading bot engine."""
    bot = refs.bot
    if not bot:
        return _json({"error": "Bot not initialized"})
    if bot.running:
        return _json({"ok": True, "message": "Bot already running"})
    import asyncio
    asyncio.create_task(bot.start())
    return _json({"ok": True, "message": "Bot start requested"})


async def tool_stop_bot() -> str:
    """Stop the trading bot engine."""
    bot = refs.bot
    if not bot:
        return _json({"error": "Bot not initialized"})
    if not bot.running:
        return _json({"ok": True, "message": "Bot already stopped"})
    await bot.stop()
    return _json({"ok": True, "message": "Bot stopped"})


# ── Tool registry for Claude agent ───────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "get_bot_status",
        "description": "Get current bot status: running state, uptime, active trade, paper/live mode, authentication.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_trading_stats",
        "description": "Get trading performance stats: win rate, total PnL, today's PnL, trade counts.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_recent_trades",
        "description": "Get recent closed trades from the journal.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max trades to return (1-100)", "default": 20}},
            "required": [],
        },
    },
    {
        "name": "get_recent_signals",
        "description": "Get recent trading signals with confidence and reasoning.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "description": "Max signals (1-50)", "default": 10}},
            "required": [],
        },
    },
    {
        "name": "get_candles",
        "description": "Fetch OHLCV candle data for chart analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeframe": {"type": "string", "enum": ["5m", "15m", "1h", "3h"], "default": "15m"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": [],
        },
    },
    {
        "name": "get_config_summary",
        "description": "Get trading configuration: capital, risk limits, thresholds, session window.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "explain_latest_signal",
        "description": "Explain the most recent signal with full reasoning from the decision engine.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_market_context",
        "description": "Get live market context: VIX, options PCR, candle counts, active trade.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "start_bot",
        "description": "Start the trading bot. Only use when user explicitly asks to start trading.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "stop_bot",
        "description": "Stop the trading bot. Only use when user explicitly asks to stop trading.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

TOOL_HANDLERS = {
    "get_bot_status": lambda **_: tool_get_bot_status(),
    "get_trading_stats": lambda **_: tool_get_trading_stats(),
    "get_recent_trades": lambda limit=20, **_: tool_get_recent_trades(limit=limit),
    "get_recent_signals": lambda limit=10, **_: tool_get_recent_signals(limit=limit),
    "get_candles": lambda timeframe="15m", limit=50, **_: tool_get_candles(timeframe=timeframe, limit=limit),
    "get_config_summary": lambda **_: tool_get_config_summary(),
    "explain_latest_signal": lambda **_: tool_explain_latest_signal(),
    "get_market_context": lambda **_: tool_get_market_context(),
    "start_bot": tool_start_bot,
    "stop_bot": tool_stop_bot,
}


async def execute_tool(name: str, arguments: Optional[dict] = None) -> str:
    """Execute a tool by name with optional arguments."""
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return _json({"error": f"Unknown tool: {name}"})
    args = arguments or {}
    import asyncio
    if asyncio.iscoroutinefunction(handler):
        return await handler(**args)
    return handler(**args)
