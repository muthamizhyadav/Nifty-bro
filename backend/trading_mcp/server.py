"""FastMCP server exposing Nifty trading bot tools."""

from mcp.server.fastmcp import FastMCP

from trading_mcp.tools import (
    tool_get_bot_status,
    tool_get_trading_stats,
    tool_get_recent_trades,
    tool_get_recent_signals,
    tool_get_candles,
    tool_get_config_summary,
    tool_explain_latest_signal,
    tool_get_market_context,
    tool_start_bot,
    tool_stop_bot,
)

mcp = FastMCP(
    "nifty-trading-bot",
    instructions=(
        "You are connected to the Nifty 50 AI Trading Bot. "
        "Use tools to read bot status, trades, signals, candles, and market context. "
        "Only start/stop the bot when the user explicitly requests it."
    ),
    json_response=True,
    stateless_http=True,
)


@mcp.tool(annotations={"readOnlyHint": True})
def get_bot_status() -> str:
    """Get current bot status: running, uptime, active trade, paper/live mode."""
    return tool_get_bot_status()


@mcp.tool(annotations={"readOnlyHint": True})
def get_trading_stats() -> str:
    """Get trading performance: win rate, total PnL, today's PnL."""
    return tool_get_trading_stats()


@mcp.tool(annotations={"readOnlyHint": True})
def get_recent_trades(limit: int = 20) -> str:
    """Get recent closed trades from the journal."""
    return tool_get_recent_trades(limit=limit)


@mcp.tool(annotations={"readOnlyHint": True})
def get_recent_signals(limit: int = 10) -> str:
    """Get recent trading signals with confidence and reasoning."""
    return tool_get_recent_signals(limit=limit)


@mcp.tool(annotations={"readOnlyHint": True})
def get_candles(timeframe: str = "15m", limit: int = 50) -> str:
    """Fetch OHLCV candles (5m, 15m, 1h, 3h) for chart analysis."""
    return tool_get_candles(timeframe=timeframe, limit=limit)


@mcp.tool(annotations={"readOnlyHint": True})
def get_config_summary() -> str:
    """Get trading config: capital, risk limits, thresholds, session window."""
    return tool_get_config_summary()


@mcp.tool(annotations={"readOnlyHint": True})
def explain_latest_signal() -> str:
    """Explain the most recent signal with full decision-engine reasoning."""
    return tool_explain_latest_signal()


@mcp.tool(annotations={"readOnlyHint": True})
def get_market_context() -> str:
    """Get live market context: VIX, options PCR, candle counts."""
    return tool_get_market_context()


@mcp.tool(annotations={"destructiveHint": False})
async def start_bot() -> str:
    """Start the trading bot. Only when user explicitly requests."""
    return await tool_start_bot()


@mcp.tool(annotations={"destructiveHint": True})
async def stop_bot() -> str:
    """Stop the trading bot. Only when user explicitly requests."""
    return await tool_stop_bot()
