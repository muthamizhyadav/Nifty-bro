"""Claude-powered stock analysis."""

import json
import logging
from typing import Any, Optional

from features.technical_service import TechnicalService

log = logging.getLogger("AIAnalysis")


class AIStockAnalysis:
    def __init__(self, broker):
        self.tech = TechnicalService(broker)

    async def analyze_stock(self, symbol: str, question: str = "") -> dict[str, Any]:
        technical = self.tech.analyze(symbol)
        if technical.get("error"):
            return {"error": technical["error"], "symbol": symbol}

        prompt = question or f"Analyze {symbol} for an Indian retail trader."
        context = json.dumps(technical, indent=2, default=str)

        try:
            from trading_mcp.claude_agent import chat
            result = await chat(
                f"{prompt}\n\nUse this technical data (do not invent numbers):\n{context}\n\n"
                "Provide: 1) Simple movement explanation 2) Bullish/Bearish sentiment "
                "3) Support/resistance 4) Risk score 1-10 5) One-line summary.",
                history=[],
                max_turns=2,
            )
            return {
                "symbol": symbol.upper(),
                "technical": technical,
                "ai_analysis": result.get("reply", ""),
                "sentiment": self._extract_sentiment(result.get("reply", "")),
                "risk_score": self._extract_risk(result.get("reply", "")),
            }
        except Exception as e:
            log.error(f"AI analysis error: {e}")
            return {
                "symbol": symbol.upper(),
                "technical": technical,
                "ai_analysis": self._fallback_analysis(technical),
                "sentiment": self._local_sentiment(technical),
                "risk_score": 5,
            }

    async def explain_movement(self, symbol: str) -> dict:
        return await self.analyze_stock(symbol, f"Why is {symbol} moving today? Explain in simple language.")

    def _local_sentiment(self, tech: dict) -> str:
        trend = tech.get("trend", "")
        if "Uptrend" in trend:
            return "Bullish"
        if "Downtrend" in trend:
            return "Bearish"
        return "Neutral"

    def _fallback_analysis(self, tech: dict) -> str:
        ind = tech.get("indicators", {})
        return (
            f"{tech['symbol']} at ₹{tech['price']}. Trend: {tech.get('trend')}. "
            f"RSI {ind.get('rsi')}, MACD {ind.get('macd')}. "
            f"Support {tech.get('support_resistance', {}).get('support')}, "
            f"Resistance {tech.get('support_resistance', {}).get('resistance')}."
        )

    def _extract_sentiment(self, text: str) -> str:
        t = text.lower()
        if "bullish" in t:
            return "Bullish"
        if "bearish" in t:
            return "Bearish"
        return "Neutral"

    def _extract_risk(self, text: str) -> int:
        import re
        m = re.search(r"risk[^0-9]*(\d+)", text.lower())
        return int(m.group(1)) if m else 5
