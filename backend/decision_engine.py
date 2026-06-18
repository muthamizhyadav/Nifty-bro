"""
DECISION ENGINE — THE BOT'S OWN BRAIN
======================================
This is a pure-Python, rules-based trading engine. NO Claude API calls.
It makes instant decisions using deterministic logic.

Claude was used to DESIGN these rules (offline). The bot now runs them itself.

How it works:
  - Takes indicators + patterns + advanced signals
  - Scores each direction (LONG vs SHORT) on a points system
  - Only signals when score crosses a confidence threshold
  - Returns the same signal format the old Claude analyzer returned

This means:
  ✓ Zero API cost during live trading
  ✓ Instant decisions (no network latency)
  ✓ Works offline / no internet dependency for decisions
  ✓ Fully deterministic — same input always gives same output (testable)
"""

import logging

log = logging.getLogger("DecisionEngine")


class DecisionEngine:
    """
    Scores LONG and SHORT setups independently using a weighted points system.
    The direction with the higher score wins — IF it crosses min threshold.
    Otherwise: WAIT.
    """

    def __init__(self, config):
        self.config = config
        # Points needed to take a trade (out of ~100 possible)
        # Configurable: lower = more trades, higher = fewer/higher-quality
        self.min_score = config.get("min_signal_score", 55)

    def decide(self, candles, indicators, pattern, advanced, options_data, vix_data):
        """
        Main decision function. Returns signal dict (same format as before).

        advanced = dict with keys: divergence, fvg, sweep, order_block
        """
        ind = indicators
        c = candles[-1]
        price = c["close"]

        # Score both directions
        long_score, long_reasons = self._score_long(ind, pattern, advanced, options_data)
        short_score, short_reasons = self._score_short(ind, pattern, advanced, options_data)

        # ─── Apply hard filters (these can VETO a trade) ───
        veto = self._check_vetoes(ind, vix_data)
        if veto:
            return self._wait_signal(f"Vetoed: {veto}", max(long_score, short_score))

        # ─── Pick winner ───
        if long_score >= self.min_score and long_score > short_score:
            return self._build_signal("LONG", price, ind, long_score, long_reasons, vix_data)
        elif short_score >= self.min_score and short_score > long_score:
            return self._build_signal("SHORT", price, ind, short_score, short_reasons, vix_data)
        else:
            best = max(long_score, short_score)
            return self._wait_signal(
                f"No setup (L:{long_score} S:{short_score}, need {self.min_score})", best
            )

    # ─── LONG scoring ─────────────────────────────────────────────────────
    def _score_long(self, ind, pattern, adv, options):
        score = 0
        reasons = []

        # 1. Trend alignment (max 25 pts)
        if ind["trend"] == "Strong Uptrend":
            score += 25; reasons.append("Strong uptrend (EMA20>50>200)")
        elif ind["trend"] == "Uptrend":
            score += 15; reasons.append("Uptrend (EMA20>50)")
        elif ind["trend"] == "Sideways":
            score += 5

        # 2. Price above VWAP (max 10 pts)
        if ind["above_vwap"]:
            score += 10; reasons.append("Above VWAP")

        # 3. RSI momentum (max 15 pts)
        rsi = ind["rsi"]
        if 50 < rsi < 65 and rsi > ind["rsi_prev"]:
            score += 15; reasons.append(f"RSI {rsi:.0f} rising, room to run")
        elif 50 < rsi < 70:
            score += 8; reasons.append(f"RSI {rsi:.0f} bullish")
        elif rsi >= 70:
            score -= 5  # overbought, risky

        # 4. MACD confirmation (max 10 pts)
        if ind["macd_hist"] > 0 and ind["macd_hist"] > ind["macd_hist_prev"]:
            score += 10; reasons.append("MACD expanding bullish")
        elif ind["macd_hist"] > 0:
            score += 5

        # 5. Volume confirmation (max 10 pts)
        if ind["volume_surge"]:
            score += 10; reasons.append("Volume surge confirms")

        # 6. Pattern (max 15 pts)
        if pattern and pattern["bias"] == "LONG":
            pts = 15 if pattern["strength"] == "strong" else 8
            score += pts; reasons.append(f"{pattern['name']} pattern")

        # 7. Advanced signals (max 15 pts combined)
        if adv.get("divergence") and adv["divergence"]["bias"] == "LONG":
            score += 8; reasons.append("Bullish RSI divergence")
        if adv.get("sweep") and adv["sweep"]["bias"] == "LONG":
            score += 7; reasons.append("Liquidity sweep reversal")
        if adv.get("order_block") and adv["order_block"]["bias"] == "LONG":
            score += 5; reasons.append("At bullish order block")
        if adv.get("fvg") and adv["fvg"]["bias"] == "LONG":
            score += 3; reasons.append("Bullish FVG")

        # 8. Options chain (max 10 pts)
        if options and options.get("pcr"):
            if options["pcr"] > 1.3:
                score += 8; reasons.append(f"PCR {options['pcr']} bullish")
            elif options["pcr"] > 1.1:
                score += 4

        # 9. ADX trend strength (max 5 pts)
        if ind["adx"] > 25:
            score += 5; reasons.append(f"Strong trend (ADX {ind['adx']:.0f})")

        return min(score, 100), reasons

    # ─── SHORT scoring ────────────────────────────────────────────────────
    def _score_short(self, ind, pattern, adv, options):
        score = 0
        reasons = []

        if ind["trend"] == "Strong Downtrend":
            score += 25; reasons.append("Strong downtrend (EMA20<50<200)")
        elif ind["trend"] == "Downtrend":
            score += 15; reasons.append("Downtrend (EMA20<50)")
        elif ind["trend"] == "Sideways":
            score += 5

        if not ind["above_vwap"]:
            score += 10; reasons.append("Below VWAP")

        rsi = ind["rsi"]
        if 35 < rsi < 50 and rsi < ind["rsi_prev"]:
            score += 15; reasons.append(f"RSI {rsi:.0f} falling, room to drop")
        elif 30 < rsi < 50:
            score += 8; reasons.append(f"RSI {rsi:.0f} bearish")
        elif rsi <= 30:
            score -= 5  # oversold, risky

        if ind["macd_hist"] < 0 and ind["macd_hist"] < ind["macd_hist_prev"]:
            score += 10; reasons.append("MACD expanding bearish")
        elif ind["macd_hist"] < 0:
            score += 5

        if ind["volume_surge"]:
            score += 10; reasons.append("Volume surge confirms")

        if pattern and pattern["bias"] == "SHORT":
            pts = 15 if pattern["strength"] == "strong" else 8
            score += pts; reasons.append(f"{pattern['name']} pattern")

        if adv.get("divergence") and adv["divergence"]["bias"] == "SHORT":
            score += 8; reasons.append("Bearish RSI divergence")
        if adv.get("sweep") and adv["sweep"]["bias"] == "SHORT":
            score += 7; reasons.append("Liquidity sweep reversal")
        if adv.get("order_block") and adv["order_block"]["bias"] == "SHORT":
            score += 5; reasons.append("At bearish order block")
        if adv.get("fvg") and adv["fvg"]["bias"] == "SHORT":
            score += 3; reasons.append("Bearish FVG")

        if options and options.get("pcr"):
            if options["pcr"] < 0.7:
                score += 8; reasons.append(f"PCR {options['pcr']} bearish")
            elif options["pcr"] < 0.9:
                score += 4

        if ind["adx"] > 25:
            score += 5; reasons.append(f"Strong trend (ADX {ind['adx']:.0f})")

        return min(score, 100), reasons

    # ─── Hard vetoes (skip trade regardless of score) ─────────────────────
    def _check_vetoes(self, ind, vix_data):
        # Choppy market — ADX too low
        if ind["adx"] < 15:
            return "choppy market (ADX<15)"
        # RSI dead zone
        if 47 <= ind["rsi"] <= 53 and abs(ind["macd_hist"]) < 1:
            return "no momentum (RSI neutral)"
        # Extreme VIX
        if vix_data and vix_data.get("vix") and vix_data["vix"] > 30:
            return f"VIX too high ({vix_data['vix']})"
        return None

    # ─── Build the actual signal with SL/targets ──────────────────────────
    def _build_signal(self, direction, price, ind, score, reasons, vix_data):
        atr = ind["atr"]

        # ATR-based stop distance (1.5x ATR, clamped 20-60 pts)
        sl_dist = max(20, min(60, atr * 1.5))

        if direction == "LONG":
            # Use structure (swing low) if it's tighter than ATR
            struct_sl = ind["swing_low"] - 5
            atr_sl = price - sl_dist
            sl = max(struct_sl, atr_sl)  # whichever is closer to price (higher)
            actual_dist = abs(price - sl)
            t1 = price + actual_dist * 1.5
            t2 = price + actual_dist * 2.5
            t3 = price + actual_dist * 4.0
        else:  # SHORT
            struct_sl = ind["swing_high"] + 5
            atr_sl = price + sl_dist
            sl = min(struct_sl, atr_sl)  # whichever is closer (lower)
            actual_dist = abs(price - sl)
            t1 = price - actual_dist * 1.5
            t2 = price - actual_dist * 2.5
            t3 = price - actual_dist * 4.0

        rr = round(abs(t2 - price) / max(abs(price - sl), 1), 1)

        return {
            "signal": direction,
            "title": reasons[0] if reasons else f"{direction} setup",
            "entry_zone": f"{price:.2f}",
            "stop_loss": f"{sl:.2f}",
            "target_1": f"{t1:.2f}",
            "target_2": f"{t2:.2f}",
            "target_3": f"{t3:.2f}",
            "risk_reward": f"1:{rr}",
            "confidence": int(score),
            "reasoning": ". ".join(reasons[:4]) + ".",
            "invalidation": f"Price {'below' if direction=='LONG' else 'above'} {sl:.2f}"
        }

    def _wait_signal(self, reason, score):
        return {
            "signal": "WAIT",
            "title": "No high-conviction setup",
            "entry_zone": "0", "stop_loss": "0",
            "target_1": "0", "target_2": "0", "target_3": "0",
            "risk_reward": "0",
            "confidence": int(score),
            "reasoning": reason,
            "invalidation": ""
        }
