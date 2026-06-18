"""AI stock screener — filter Nifty 50 by technical/fundamental proxies."""

import logging
from typing import Any

from features.symbols import NIFTY50
from features.technical_service import TechnicalService

log = logging.getLogger("Screener")


class ScreenerService:
    def __init__(self, broker):
        self.tech = TechnicalService(broker)

    def screen(self, filters: dict) -> list[dict]:
        results = []
        for sym in NIFTY50:
            analysis = self.tech.analyze(sym)
            if analysis.get("error"):
                continue
            ind = analysis.get("indicators", {})
            if not self._passes(sym, analysis, ind, filters):
                continue
            results.append({
                "symbol": sym,
                "price": analysis["price"],
                "rsi": ind.get("rsi"),
                "trend": analysis.get("trend"),
                "volume_surge": analysis.get("volume_surge"),
                "pattern": (analysis.get("pattern") or {}).get("name"),
                "change_signal": self._signal(ind, analysis),
            })
        return sorted(results, key=lambda x: x.get("rsi", 50), reverse=filters.get("sort") == "rsi_desc")

    def _passes(self, sym, analysis, ind, f) -> bool:
        rsi = ind.get("rsi", 50)
        if f.get("rsi_min") and rsi < f["rsi_min"]:
            return False
        if f.get("rsi_max") and rsi > f["rsi_max"]:
            return False
        if f.get("trend") and f["trend"] not in analysis.get("trend", ""):
            return False
        if f.get("volume_surge") and not analysis.get("volume_surge"):
            return False
        if f.get("breakout"):
            res = analysis.get("support_resistance", {}).get("resistance", 0)
            if analysis.get("price", 0) <= res:
                return False
        return True

    def _signal(self, ind, analysis) -> str:
        rsi = ind.get("rsi", 50)
        if rsi < 35 and "Uptrend" in analysis.get("trend", ""):
            return "Oversold in uptrend"
        if rsi > 65 and "Downtrend" in analysis.get("trend", ""):
            return "Overbought in downtrend"
        if analysis.get("volume_surge"):
            return "Volume breakout"
        return "Neutral"

    def presets(self) -> dict:
        return {
            "oversold": {"rsi_max": 35, "label": "Oversold (RSI < 35)"},
            "overbought": {"rsi_min": 65, "label": "Overbought (RSI > 65)"},
            "breakout": {"breakout": True, "volume_surge": True, "label": "Breakout + Volume"},
            "uptrend": {"trend": "Uptrend", "label": "Uptrend stocks"},
            "downtrend": {"trend": "Downtrend", "label": "Downtrend stocks"},
        }
