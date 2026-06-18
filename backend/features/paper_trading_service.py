"""Extended paper trading — virtual portfolio, leaderboard."""

import logging
from datetime import datetime
from typing import Any

from features.db_store import FeaturesDB
from features.symbols import to_fyers

log = logging.getLogger("PaperTrading")


class PaperTradingService:
    INITIAL_CASH = 1_000_000

    def __init__(self, broker, db: FeaturesDB):
        self.broker = broker
        self.db = db

    def _ltp(self, symbol: str) -> float:
        q = self.broker.get_quote(to_fyers(symbol))
        return q.get("ltp", 0) if q else 0

    def get_account(self) -> dict:
        cash = self.db.get_paper_cash()
        trades = self.db.get_paper_trades(500)
        open_trades = [t for t in trades if t["status"] == "OPEN"]
        closed = [t for t in trades if t["status"] == "CLOSED"]

        open_value = sum(t["qty"] * self._ltp(t["symbol"]) for t in open_trades)
        realized_pnl = sum(t.get("pnl", 0) or 0 for t in closed)

        return {
            "cash": round(cash, 2),
            "open_positions": len(open_trades),
            "open_value": round(open_value, 2),
            "total_equity": round(cash + open_value, 2),
            "realized_pnl": round(realized_pnl, 2),
            "total_trades": len(closed),
            "win_rate": round(sum(1 for t in closed if (t.get("pnl") or 0) > 0) / len(closed) * 100, 1) if closed else 0,
        }

    def buy(self, symbol: str, qty: int) -> dict:
        ltp = self._ltp(symbol)
        cost = ltp * qty
        cash = self.db.get_paper_cash()
        if cost > cash:
            return {"ok": False, "error": "Insufficient virtual cash"}
        self.db.update_paper_cash(cash - cost)
        self.db.save_paper_trade({
            "symbol": symbol.upper(), "direction": "BUY", "qty": qty,
            "entry_price": ltp, "exit_price": None,
            "entry_time": datetime.now().isoformat(), "exit_time": None,
            "pnl": 0, "status": "OPEN", "reason": "Paper buy",
        })
        return {"ok": True, "symbol": symbol, "qty": qty, "price": ltp}

    def sell(self, symbol: str, qty: int) -> dict:
        trades = [t for t in self.db.get_paper_trades(100) if t["symbol"] == symbol.upper() and t["status"] == "OPEN"]
        if not trades:
            return {"ok": False, "error": "No open position"}
        trade = trades[0]
        ltp = self._ltp(symbol)
        pnl = (ltp - trade["entry_price"]) * qty
        cash = self.db.get_paper_cash()
        self.db.update_paper_cash(cash + ltp * qty)
        self.db.save_paper_trade({
            "symbol": symbol.upper(), "direction": "SELL", "qty": qty,
            "entry_price": trade["entry_price"], "exit_price": ltp,
            "entry_time": trade["entry_time"], "exit_time": datetime.now().isoformat(),
            "pnl": pnl, "status": "CLOSED", "reason": "Paper sell",
        })
        return {"ok": True, "symbol": symbol, "pnl": round(pnl, 2)}

    def get_trades(self, limit: int = 50) -> list:
        return self.db.get_paper_trades(limit)

    def get_leaderboard(self) -> list[dict]:
        trades = self.db.get_paper_trades(500)
        closed = [t for t in trades if t["status"] == "CLOSED"]
        total_pnl = sum(t.get("pnl", 0) or 0 for t in closed)
        wins = sum(1 for t in closed if (t.get("pnl") or 0) > 0)
        return [{
            "trader": "You",
            "total_pnl": round(total_pnl, 2),
            "trades": len(closed),
            "win_rate": round(wins / len(closed) * 100, 1) if closed else 0,
            "rank": 1,
        }]
