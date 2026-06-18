"""Extended technical analysis service."""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from analyzer import Analyzer
from config import CONFIG
from features.symbols import to_fyers

log = logging.getLogger("TechnicalService")


class TechnicalService:
    def __init__(self, broker):
        self.broker = broker
        self.analyzer = Analyzer(CONFIG)

    def _fetch_candles(self, symbol: str, days: int = 60) -> list:
        fy = to_fyers(symbol)
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return self.broker.get_historical_candles(fy, "15", from_date, to_date)

    def _sma(self, values: list, period: int) -> float:
        if len(values) < period:
            return values[-1] if values else 0
        return sum(values[-period:]) / period

    def _fibonacci_levels(self, high: float, low: float) -> dict:
        diff = high - low
        return {
            "0.0": round(high, 2),
            "0.236": round(high - diff * 0.236, 2),
            "0.382": round(high - diff * 0.382, 2),
            "0.5": round(high - diff * 0.5, 2),
            "0.618": round(high - diff * 0.618, 2),
            "1.0": round(low, 2),
        }

    def analyze(self, symbol: str) -> dict[str, Any]:
        candles = self._fetch_candles(symbol)
        if len(candles) < 20:
            return {"error": "Insufficient candle data", "symbol": symbol}

        indicators = self.analyzer.compute_indicators(candles)
        pattern = self.analyzer.detect_pattern(candles)
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        swing_h = max(highs[-20:])
        swing_l = min(lows[-20:])

        return {
            "symbol": symbol.upper(),
            "price": indicators["close"],
            "trend": indicators["trend"],
            "regime": indicators["regime"],
            "indicators": {
                "rsi": indicators["rsi"],
                "macd": indicators["macd_hist"],
                "ema20": indicators["ema20"],
                "ema50": indicators["ema50"],
                "sma20": round(self._sma(closes, 20), 2),
                "sma50": round(self._sma(closes, 50), 2),
                "bb_upper": indicators["bb_upper"],
                "bb_lower": indicators["bb_lower"],
                "vwap": indicators["vwap"],
                "atr": indicators["atr"],
                "adx": indicators["adx"],
            },
            "support_resistance": {
                "support": round(swing_l, 2),
                "resistance": round(swing_h, 2),
                "vwap": indicators["vwap"],
            },
            "fibonacci": self._fibonacci_levels(swing_h, swing_l),
            "pattern": pattern,
            "volume_surge": indicators["volume_surge"],
        }

    def detect_patterns(self, symbol: str) -> dict:
        candles = self._fetch_candles(symbol, days=30)
        if len(candles) < 5:
            return {"patterns": [], "symbol": symbol}
        patterns_found = []
        # Scan last 5 candles for patterns
        for i in range(-5, 0):
            subset = candles[:len(candles) + i] if i < -1 else candles
            if len(subset) < 3:
                continue
            p = self.analyzer.detect_pattern(subset)
            if p:
                patterns_found.append(p)
        return {"symbol": symbol, "patterns": patterns_found}
