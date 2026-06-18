"""Portfolio management — holdings, P&L, allocation, risk."""

import logging
from typing import Any

from features.db_store import FeaturesDB
from features.symbols import to_fyers

log = logging.getLogger("Portfolio")


class PortfolioService:
    def __init__(self, broker, db: FeaturesDB):
        self.broker = broker
        self.db = db

    def _live_price(self, symbol: str) -> float:
        q = self.broker.get_quote(to_fyers(symbol))
        return q.get("ltp", 0) if q else 0

    def get_portfolio(self) -> dict[str, Any]:
        holdings = self.db.get_holdings()
        items = []
        total_invested = 0
        total_current = 0
        for h in holdings:
            ltp = self._live_price(h["symbol"])
            invested = h["qty"] * h["avg_price"]
            current = h["qty"] * ltp
            pnl = current - invested
            pnl_pct = (pnl / invested * 100) if invested else 0
            total_invested += invested
            total_current += current
            items.append({
                "id": h["id"],
                "symbol": h["symbol"],
                "qty": h["qty"],
                "avg_price": h["avg_price"],
                "ltp": ltp,
                "invested": round(invested, 2),
                "current_value": round(current, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "weight": 0,
            })
        for item in items:
            item["weight"] = round(item["current_value"] / total_current * 100, 1) if total_current else 0

        total_pnl = total_current - total_invested
        diversification = self._diversification_score(items)
        risk = self._risk_score(items)

        return {
            "holdings": items,
            "summary": {
                "total_invested": round(total_invested, 2),
                "total_value": round(total_current, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_pct": round(total_pnl / total_invested * 100, 2) if total_invested else 0,
                "holdings_count": len(items),
            },
            "allocation": [{"symbol": i["symbol"], "weight": i["weight"]} for i in items],
            "diversification_score": diversification,
            "risk_score": risk,
            "health_score": round((diversification + (100 - risk)) / 2, 1),
        }

    def _diversification_score(self, items: list) -> float:
        if not items:
            return 0
        if len(items) >= 8:
            base = 80
        elif len(items) >= 4:
            base = 60
        else:
            base = 40
        max_weight = max(i["weight"] for i in items) if items else 100
        if max_weight > 40:
            base -= 20
        return max(0, min(100, base))

    def _risk_score(self, items: list) -> float:
        if not items:
            return 0
        max_weight = max(i["weight"] for i in items)
        volatile = sum(1 for i in items if abs(i["pnl_pct"]) > 5)
        score = min(100, max_weight * 1.5 + volatile * 10)
        return round(score, 1)

    def get_advisor_insights(self) -> dict:
        pf = self.get_portfolio()
        overweight = [i for i in pf["holdings"] if i["weight"] > 25]
        underperformers = [i for i in pf["holdings"] if i["pnl_pct"] < -3]
        suggestions = []
        for o in overweight:
            suggestions.append(f"Reduce {o['symbol']} — overweight at {o['weight']}%")
        for u in underperformers:
            suggestions.append(f"Review {u['symbol']} — down {u['pnl_pct']}%")
        if not pf["holdings"]:
            suggestions.append("Add 5-8 stocks across sectors for diversification")
        return {
            "health_score": pf["health_score"],
            "overweight": overweight,
            "underperformers": underperformers,
            "rebalance_suggestions": suggestions,
            "risk_exposure": pf["risk_score"],
        }

    def add_holding(self, symbol: str, qty: float, avg_price: float):
        self.db.add_holding(symbol, qty, avg_price)

    def remove_holding(self, holding_id: int):
        self.db.remove_holding(holding_id)
