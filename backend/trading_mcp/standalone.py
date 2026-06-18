"""
Standalone MCP server (stdio transport) for Claude Desktop / Cursor.

Run from backend/:
    python -m trading_mcp.standalone

Add to Claude Desktop config (~/.config/claude/claude_desktop_config.json):
{
  "mcpServers": {
    "nifty-trading-bot": {
      "command": "python",
      "args": ["-m", "trading_mcp.standalone"],
      "cwd": "/path/to/nifty_pro/backend",
      "env": {
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
"""

import os
import sys
from pathlib import Path

# Ensure backend/ is on path
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from dotenv import load_dotenv
load_dotenv(_backend / ".env")

from config import CONFIG
from database import Database
from trading_mcp.context import refs
from trading_mcp.server import mcp

# Initialize minimal context for standalone mode (no live bot)
refs.config = CONFIG
refs.db = Database()
refs.db.init()
refs.bot = None

if __name__ == "__main__":
    mcp.run(transport="stdio")
