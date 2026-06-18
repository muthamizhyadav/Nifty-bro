"""
ADVANCED ANALYZER
=================
All pro techniques: divergence, FVG, order blocks, liquidity sweeps,
volume confirmation, multi-timeframe confluence.
"""

import logging
import re
import json
from datetime import datetime
from decision_engine import DecisionEngine

log = logging.getLogger("Analyzer")


class Analyzer:
    def __init__(self, config):
        self.config = config
        self.engine = DecisionEngine(config)  # bot's own brain, no Claude API

    # ─── Indicators ───────────────────────────────────────────────────────
    def compute_indicators(self, candles):
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 1) for c in candles]
        n = len(closes) - 1

        ema20 = self._ema(closes, 20)
        ema50 = self._ema(closes, 50)
        ema200 = self._ema(closes, 200) if len(closes) >= 200 else self._ema(closes, len(closes))
        rsi = self._rsi(closes, 14)
        macd_line, macd_sig, macd_hist = self._macd(closes)
        bb_u, bb_m, bb_l = self._bollinger(closes)
        atr = self._atr(highs, lows, closes, 14)
        vwap = self._vwap(highs, lows, closes, volumes)
        adx = self._adx(highs, lows, closes, 14)

        recent = candles[-20:]
        swing_h = max(c["high"] for c in recent)
        swing_l = min(c["low"] for c in recent)

        # Trend strength
        if ema20[n] > ema50[n] > ema200[n]:
            trend = "Strong Uptrend"
        elif ema20[n] > ema50[n]:
            trend = "Uptrend"
        elif ema20[n] < ema50[n] < ema200[n]:
            trend = "Strong Downtrend"
        elif ema20[n] < ema50[n]:
            trend = "Downtrend"
        else:
            trend = "Sideways"

        # Volume context
        avg_vol_20 = sum(volumes[-20:]) / 20
        volume_surge = volumes[n] > avg_vol_20 * 1.5

        # Market regime via ADX
        regime = "Trending" if adx[n] > 25 else "Weak Trend" if adx[n] > 15 else "Ranging"

        return {
            "close": closes[n],
            "rsi": round(rsi[n], 2),
            "rsi_prev": round(rsi[n-1], 2),
            "macd_line": round(macd_line[n], 2),
            "macd_signal": round(macd_sig[n], 2),
            "macd_hist": round(macd_hist[n], 2),
            "macd_hist_prev": round(macd_hist[n-1], 2),
            "ema20": round(ema20[n], 2),
            "ema50": round(ema50[n], 2),
            "ema200": round(ema200[n], 2),
            "ema20_slope": "rising" if ema20[n] > ema20[n-5] else "falling",
            "bb_upper": round(bb_u[n], 2),
            "bb_lower": round(bb_l[n], 2),
            "atr": round(atr[n], 2),
            "vwap": round(vwap[n], 2),
            "adx": round(adx[n], 2),
            "regime": regime,
            "swing_high": round(swing_h, 2),
            "swing_low": round(swing_l, 2),
            "trend": trend,
            "above_vwap": closes[n] > vwap[n],
            "current_volume": volumes[n],
            "avg_volume_20": round(avg_vol_20, 0),
            "volume_surge": volume_surge,
        }

    # ─── Pattern detection (12 patterns) ──────────────────────────────────
    def detect_pattern(self, candles):
        if len(candles) < 3: return None
        c0, c1, c2 = candles[-1], candles[-2], candles[-3]
        body0 = abs(c0["close"] - c0["open"]); body1 = abs(c1["close"] - c1["open"])
        range0 = c0["high"] - c0["low"]; range1 = c1["high"] - c1["low"]
        bull0 = c0["close"] > c0["open"]; bull1 = c1["close"] > c1["open"]
        upper_sh = c0["high"] - max(c0["open"], c0["close"])
        lower_sh = min(c0["open"], c0["close"]) - c0["low"]

        if lower_sh > body0 * 2 and upper_sh < body0 * 0.4 and not bull1:
            return {"name": "Hammer", "bias": "LONG", "strength": "strong"}
        if upper_sh > body0 * 2 and lower_sh < body0 * 0.4 and bull1:
            return {"name": "Shooting Star", "bias": "SHORT", "strength": "strong"}
        if bull0 and not bull1 and c0["open"] < c1["close"] and c0["close"] > c1["open"] and body0 > body1 * 1.1:
            return {"name": "Bullish Engulfing", "bias": "LONG", "strength": "strong"}
        if not bull0 and bull1 and c0["open"] > c1["close"] and c0["close"] < c1["open"] and body0 > body1 * 1.1:
            return {"name": "Bearish Engulfing", "bias": "SHORT", "strength": "strong"}
        if bull0 and not bull1 and (c2["close"] > c2["open"]) is False and body1 < range1 * 0.25:
            return {"name": "Morning Star", "bias": "LONG", "strength": "strong"}
        if not bull0 and bull1 and (c2["close"] > c2["open"]) and body1 < range1 * 0.25:
            return {"name": "Evening Star", "bias": "SHORT", "strength": "strong"}
        if lower_sh > range0 * 0.6 and body0 < range0 * 0.25:
            return {"name": "Bullish Pin Bar", "bias": "LONG", "strength": "strong"}
        if upper_sh > range0 * 0.6 and body0 < range0 * 0.25:
            return {"name": "Bearish Pin Bar", "bias": "SHORT", "strength": "strong"}
        if body0 < range0 * 0.07 and range0 > 15:
            return {"name": "Doji", "bias": "WAIT", "strength": "weak"}
        if c0["high"] < c1["high"] and c0["low"] > c1["low"]:
            return {"name": "Inside Bar", "bias": "WAIT", "strength": "weak"}
        return None

    # ─── ADVANCED: RSI Divergence ─────────────────────────────────────────
    def detect_rsi_divergence(self, candles, rsi):
        """
        Bullish divergence: Price lower low + RSI higher low
        Bearish divergence: Price higher high + RSI lower high
        Adds 10 points to confidence when present.
        """
        if len(candles) < 20: return None
        recent = candles[-20:]
        recent_rsi = rsi[-20:]

        # Find swing lows in price and corresponding RSI
        price_lows = [(i, c["low"]) for i, c in enumerate(recent)
                      if 1 <= i <= 18 and c["low"] < recent[i-1]["low"] and c["low"] < recent[i+1]["low"]]
        price_highs = [(i, c["high"]) for i, c in enumerate(recent)
                       if 1 <= i <= 18 and c["high"] > recent[i-1]["high"] and c["high"] > recent[i+1]["high"]]

        # Bullish divergence
        if len(price_lows) >= 2:
            i1, p1 = price_lows[-2]; i2, p2 = price_lows[-1]
            if p2 < p1 and recent_rsi[i2] > recent_rsi[i1]:
                return {"type": "bullish_divergence", "bias": "LONG"}

        # Bearish divergence
        if len(price_highs) >= 2:
            i1, p1 = price_highs[-2]; i2, p2 = price_highs[-1]
            if p2 > p1 and recent_rsi[i2] < recent_rsi[i1]:
                return {"type": "bearish_divergence", "bias": "SHORT"}

        return None

    # ─── ADVANCED: Fair Value Gap detection ───────────────────────────────
    def detect_fvg(self, candles):
        """
        FVG: 3-candle gap where candle1 high < candle3 low (bullish)
        or candle1 low > candle3 high (bearish). Market often returns to fill.
        """
        if len(candles) < 3: return None
        c1 = candles[-3]; c3 = candles[-1]
        if c1["high"] < c3["low"]:
            return {"type": "bullish_fvg", "zone": (c1["high"], c3["low"]), "bias": "LONG"}
        if c1["low"] > c3["high"]:
            return {"type": "bearish_fvg", "zone": (c3["high"], c1["low"]), "bias": "SHORT"}
        return None

    # ─── ADVANCED: Liquidity sweep detection ──────────────────────────────
    def detect_liquidity_sweep(self, candles):
        """
        Detects: price spikes above swing high then closes below (bearish sweep)
        or below swing low then closes above (bullish sweep).
        Institutional reversal signal.
        """
        if len(candles) < 10: return None
        recent = candles[-10:]
        c = candles[-1]
        prior_high = max(x["high"] for x in recent[:-1])
        prior_low = min(x["low"] for x in recent[:-1])

        if c["high"] > prior_high and c["close"] < prior_high:
            return {"type": "bullish_sweep_reversal", "bias": "SHORT"}
        if c["low"] < prior_low and c["close"] > prior_low:
            return {"type": "bearish_sweep_reversal", "bias": "LONG"}
        return None

    # ─── ADVANCED: Order Block detection ──────────────────────────────────
    def detect_order_block(self, candles):
        """
        Order block: last opposite-color candle before strong move.
        Bullish OB: last bearish candle before strong up move (>1.5×ATR).
        Bearish OB: last bullish candle before strong down move.
        """
        if len(candles) < 5: return None
        atr_est = sum(abs(candles[i]["close"] - candles[i-1]["close"]) for i in range(-5, 0)) / 5
        for i in range(-4, -1):
            move = abs(candles[i+1]["close"] - candles[i]["close"])
            if move > atr_est * 1.5:
                bull_move = candles[i+1]["close"] > candles[i]["close"]
                # Check if the candle before the move is opposite color
                if bull_move and candles[i]["close"] < candles[i]["open"]:
                    return {"type": "bullish_ob", "zone": (candles[i]["low"], candles[i]["high"]), "bias": "LONG"}
                if not bull_move and candles[i]["close"] > candles[i]["open"]:
                    return {"type": "bearish_ob", "zone": (candles[i]["low"], candles[i]["high"]), "bias": "SHORT"}
        return None

    # ─── Main signal generator ────────────────────────────────────────────
    def get_signal(self, candles, candles_1h, indicators, pattern, options_data, vix_data):
        """
        BOT'S OWN DECISION — no Claude API call.
        Uses the local DecisionEngine (pure Python rules).
        Claude was used offline to design these rules; the bot runs them itself.
        """
        # Run all advanced detections
        rsi_arr = self._rsi([c["close"] for c in candles], 14)
        advanced = {
            "divergence": self.detect_rsi_divergence(candles, rsi_arr),
            "fvg": self.detect_fvg(candles),
            "sweep": self.detect_liquidity_sweep(candles),
            "order_block": self.detect_order_block(candles),
        }

        # Multi-timeframe filter: check 1H trend agrees
        if candles_1h and len(candles_1h) >= 20:
            h_closes = [c["close"] for c in candles_1h]
            h_ema_short = self._ema(h_closes, 9)[-1]
            h_ema_long = self._ema(h_closes, 21)[-1]
            indicators["htf_trend"] = "up" if h_ema_short > h_ema_long else "down"
        else:
            indicators["htf_trend"] = "unknown"

        # Let the bot's own engine decide
        signal = self.engine.decide(candles, indicators, pattern, advanced, options_data, vix_data)

        # Apply multi-timeframe veto: don't go against 1H trend
        if signal["signal"] == "LONG" and indicators["htf_trend"] == "down":
            signal = self.engine._wait_signal("1H trend down, skip LONG", signal["confidence"])
        elif signal["signal"] == "SHORT" and indicators["htf_trend"] == "up":
            signal = self.engine._wait_signal("1H trend up, skip SHORT", signal["confidence"])

        return signal

    # ─── Calculation helpers ──────────────────────────────────────────────
    def _ema(self, data, period):
        k = 2 / (period + 1); ema = [data[0]]
        for v in data[1:]: ema.append(v * k + ema[-1] * (1 - k))
        return ema

    def _rsi(self, data, period=14):
        if len(data) < period + 1: return [50] * len(data)
        gains, losses = [], []
        for i in range(1, len(data)):
            d = data[i] - data[i-1]; gains.append(max(d, 0)); losses.append(max(-d, 0))
        avg_g = sum(gains[:period]) / period; avg_l = sum(losses[:period]) / period
        rsi = [50] * period
        for i in range(period, len(gains)):
            avg_g = (avg_g * (period - 1) + gains[i]) / period
            avg_l = (avg_l * (period - 1) + losses[i]) / period
            rsi.append(100 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l))
        return [50] + rsi

    def _macd(self, data):
        e12 = self._ema(data, 12); e26 = self._ema(data, 26)
        line = [a - b for a, b in zip(e12, e26)]
        sig = self._ema(line, 9); hist = [a - b for a, b in zip(line, sig)]
        return line, sig, hist

    def _bollinger(self, data, period=20, std=2):
        u, m, l = [], [], []
        for i in range(len(data)):
            if i < period: u.append(data[i]); m.append(data[i]); l.append(data[i]); continue
            w = data[i-period:i]; mn = sum(w) / period
            s = (sum((x-mn)**2 for x in w) / period) ** 0.5
            u.append(mn + std*s); m.append(mn); l.append(mn - std*s)
        return u, m, l

    def _atr(self, highs, lows, closes, period=14):
        trs = [highs[0] - lows[0]]
        for i in range(1, len(closes)):
            trs.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        atr = [trs[0]]
        for i in range(1, len(trs)):
            atr.append((atr[-1] * (period-1) + trs[i]) / period)
        return atr

    def _vwap(self, highs, lows, closes, volumes):
        vwap = []; cum_pv = 0; cum_v = 0
        for i in range(len(closes)):
            typ = (highs[i] + lows[i] + closes[i]) / 3
            cum_pv += typ * volumes[i]; cum_v += volumes[i]
            vwap.append(cum_pv / max(cum_v, 1))
        return vwap

    def _adx(self, highs, lows, closes, period=14):
        if len(closes) < period * 2: return [0] * len(closes)
        plus_dm, minus_dm, tr_list = [0], [0], [highs[0] - lows[0]]
        for i in range(1, len(closes)):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0)
            minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0)
            tr_list.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))

        def smooth(data, p):
            if len(data) < p: return [0] * len(data)
            r = [sum(data[:p]) / p]
            for v in data[p:]: r.append((r[-1] * (p-1) + v) / p)
            return [0] * (p-1) + r

        atr = smooth(tr_list, period)
        plus_di = [100*a/b if b>0 else 0 for a, b in zip(smooth(plus_dm, period), atr)]
        minus_di = [100*a/b if b>0 else 0 for a, b in zip(smooth(minus_dm, period), atr)]
        dx = [100*abs(p-m)/max(p+m, 1) for p, m in zip(plus_di, minus_di)]
        return smooth(dx, period)
