"""AI trade journal — store entries and Claude performance analysis."""

import logging
from typing import Any

from features.db_store import FeaturesDB

log = logging.getLogger("JournalAI")


class JournalAIService:
    def __init__(self, db: FeaturesDB, bot_db=None):
        self.db = db
        self.bot_db = bot_db

    def add_entry(self, entry: dict) -> dict:
        self.db.save_journal_entry(entry)
        return {"ok": True}

    def get_entries(self, limit: int = 50) -> list:
        journal = self.db.get_journal_entries(limit)
        if self.bot_db:
            bot_trades = self.bot_db.get_trades(limit)
            for t in bot_trades:
                journal.append({
                    "symbol": "NIFTY",
                    "direction": t.get("direction"),
                    "entry_price": t.get("entry_price"),
                    "exit_price": t.get("exit_price"),
                    "pnl": t.get("pnl"),
                    "exit_reason": t.get("reason"),
                    "source": "bot",
                    "created_at": t.get("entry_time"),
                })
        return journal

    async def analyze_performance(self) -> dict[str, Any]:
        entries = self.get_entries(100)
        if not entries:
            return {"message": "No journal entries yet"}

        wins = [e for e in entries if (e.get("pnl") or 0) > 0]
        losses = [e for e in entries if (e.get("pnl") or 0) < 0]
        summary = {
            "total": len(entries),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(entries) * 100, 1) if entries else 0,
            "total_pnl": round(sum(e.get("pnl", 0) or 0 for e in entries), 2),
        }

        try:
            from trading_mcp.claude_agent import chat
            import json
            result = await chat(
                f"Analyze this trading journal. Identify mistakes, best strategy, and 3 improvement tips:\n"
                f"{json.dumps(summary, indent=2)}\n"
                f"Sample trades: {json.dumps(entries[:10], default=str)}",
                history=[],
                max_turns=2,
            )
            return {"summary": summary, "ai_insights": result.get("reply", "")}
        except Exception as e:
            return {
                "summary": summary,
                "ai_insights": f"Win rate {summary['win_rate']}%. Review losing trades for overtrading or tight stops.",
            }
