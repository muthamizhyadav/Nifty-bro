"""Watchlist with buy/hold/sell scoring."""

import logging
from typing import Any

from features.db_store import FeaturesDB
from features.technical_service import TechnicalService

log = logging.getLogger("Watchlist")


class WatchlistService:
    def __init__(self, broker, db: FeaturesDB):
        self.db = db
        self.tech = TechnicalService(broker)

    def _score_stock(self, analysis: dict) -> dict:
        if analysis.get("error"):
            return {"buy": 33, "hold": 34, "sell": 33, "trend": "unknown", "signal": "HOLD"}

        ind = analysis.get("indicators", {})
        rsi = ind.get("rsi", 50)
        macd = ind.get("macd", 0)
        trend = analysis.get("trend", "Sideways")

        buy, hold, sell = 33, 34, 33
        if "Uptrend" in trend:
            buy += 25
            sell -= 15
        elif "Downtrend" in trend:
            sell += 25
            buy -= 15
        if rsi < 35:
            buy += 15
        elif rsi > 65:
            sell += 15
        elif 45 <= rsi <= 55:
            hold += 10
        if macd > 0:
            buy += 10
        else:
            sell += 10

        total = buy + hold + sell
        return {
            "buy": round(buy / total * 100),
            "hold": round(hold / total * 100),
            "sell": round(sell / total * 100),
            "trend": trend,
            "signal": "BUY" if buy > sell and buy > hold else "SELL" if sell > buy else "HOLD",
            "rsi": rsi,
        }

    def get_watchlist(self) -> list[dict[str, Any]]:
        items = self.db.get_watchlist()
        out = []
        for w in items:
            sym = w["symbol"]
            analysis = self.tech.analyze(sym)
            scores = self._score_stock(analysis)
            out.append({
                "symbol": sym,
                "price": analysis.get("price", 0),
                "scores": scores,
                "pattern": analysis.get("pattern"),
                "support": analysis.get("support_resistance", {}).get("support"),
                "resistance": analysis.get("support_resistance", {}).get("resistance"),
            })
        return out

    def add(self, symbol: str):
        self.db.add_watchlist(symbol)

    def remove(self, symbol: str):
        self.db.remove_watchlist(symbol)
