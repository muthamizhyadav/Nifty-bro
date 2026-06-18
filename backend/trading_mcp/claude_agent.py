"""Claude agent with MCP tool execution loop."""

import logging
import os
from typing import Any, Optional

from trading_mcp.tools import TOOL_DEFINITIONS, execute_tool

log = logging.getLogger("MCP.Agent")

SYSTEM_PROMPT = """You are the AI assistant for the Nifty 50 Trading Bot dashboard.
You help the trader understand bot status, signals, trades, market context, and configuration.

Rules:
- Use MCP tools to fetch real data before answering — never invent trade numbers or prices.
- Be concise and actionable. Use ₹ for Indian rupee amounts.
- For trading advice, reference the bot's actual signals and stats, not generic tips.
- Only start/stop the bot when the user explicitly asks.
- If data is unavailable (bot offline, no token), say so clearly.
"""


def _api_key() -> Optional[str]:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key in ("NOT_SET", "NOT_NEEDED_BOT_DECIDES_LOCALLY"):
        return None
    return key


def is_configured() -> bool:
    return _api_key() is not None


async def chat(
    user_message: str,
    history: Optional[list[dict]] = None,
    max_turns: int = 8,
) -> dict[str, Any]:
    """
    Run a Claude conversation with tool use.
    Returns {"reply": str, "tool_calls": list, "error": str|None}
    """
    api_key = _api_key()
    if not api_key:
        return {
            "reply": "Claude API key not configured. Set ANTHROPIC_API_KEY in backend/.env and restart.",
            "tool_calls": [],
            "error": "missing_api_key",
        }

    try:
        import anthropic
    except ImportError:
        return {
            "reply": "anthropic package not installed. Run: pip install anthropic",
            "tool_calls": [],
            "error": "missing_package",
        }

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict] = []
    if history:
        for h in history[-20:]:
            role = h.get("role", "user")
            if role in ("user", "assistant") and h.get("content"):
                messages.append({"role": role, "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    anthropic_tools = [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in TOOL_DEFINITIONS
    ]

    tool_calls_log: list[dict] = []
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    for _ in range(max_turns):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=anthropic_tools,
            messages=messages,
        )

        # Collect text and tool_use blocks
        text_parts = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        if response.stop_reason == "end_turn" or not tool_uses:
            return {
                "reply": "\n".join(text_parts) or "Done.",
                "tool_calls": tool_calls_log,
                "error": None,
            }

        # Execute tools and continue conversation
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tu in tool_uses:
            log.info("Tool call: %s(%s)", tu.name, tu.input)
            result = await execute_tool(tu.name, tu.input or {})
            tool_calls_log.append({"name": tu.name, "input": tu.input, "result_preview": result[:500]})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    return {
        "reply": "Reached maximum tool turns. Try a simpler question.",
        "tool_calls": tool_calls_log,
        "error": "max_turns",
    }
