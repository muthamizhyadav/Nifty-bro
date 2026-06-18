"""Shared references for MCP tools (set by main.py on startup)."""

from typing import Any, Optional


class AppRefs:
    bot: Any = None
    db: Any = None
    config: dict = {}
    ws_broadcast: Optional[Any] = None


refs = AppRefs()
