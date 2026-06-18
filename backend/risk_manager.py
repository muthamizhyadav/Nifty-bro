"""
PROFESSIONAL RISK MANAGER
=========================
All rules baked in. Bot will not trade without passing every check.
"""

import logging
from datetime import datetime, timedelta

log = logging.getLogger("RiskManager")


class RiskManager:
    def __init__(self, config):
        self.config = config
        self.capital = config["capital"]
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.trades_today = 0
        self.consecutive_losses = 0
        self.last_loss_time = None
        self.trade_open = False
        self._last_date = None

    # ─── Daily reset ──────────────────────────────────────────────────────
    def _reset_if_new_day(self):
        now = datetime.now()
        if self._last_date != now.date():
            if self._last_date and now.weekday() == 0:
                self.weekly_pnl = 0.0
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.consecutive_losses = 0
            self._last_date = now.date()

    # ─── Pre-trade safety checks ──────────────────────────────────────────
    def is_trading_allowed(self):
        self._reset_if_new_day()
        now = datetime.now()

        # Session window
        s_h, s_m = map(int, self.config["trading_start"].split(":"))
        e_h, e_m = map(int, self.config["trading_end"].split(":"))
        start = now.replace(hour=s_h, minute=s_m, second=0)
        end = now.replace(hour=e_h, minute=e_m, second=0)
        if now < start or now > end: return False
        if now.weekday() >= 5: return False

        # Loss limits
        max_dl = -self.capital * self.config["max_daily_loss_pct"] / 100
        if self.daily_pnl <= max_dl:
            log.warning(f"Daily loss limit hit: ₹{self.daily_pnl:.2f}")
            return False
        max_wl = -self.capital * self.config["max_weekly_loss_pct"] / 100
        if self.weekly_pnl <= max_wl:
            log.warning(f"Weekly loss limit hit: ₹{self.weekly_pnl:.2f}")
            return False

        # Max trades
        if self.trades_today >= self.config["max_trades_per_day"]: return False

        # Cooldown after losses
        if self.consecutive_losses >= 2 and self.last_loss_time:
            if now < self.last_loss_time + timedelta(minutes=30):
                return False

        # News blackout
        if self._in_news_blackout():
            log.info("News blackout active")
            return False

        if self.trade_open: return False
        return True

    def _in_news_blackout(self):
        now = datetime.now()
        for ev in self.config.get("news_events", []):
            try:
                event = datetime.strptime(ev, "%Y-%m-%d %H:%M")
                if abs((now - event).total_seconds()) < 900:  # ±15 min
                    return True
            except: continue
        return False

    # ─── Signal validation ────────────────────────────────────────────────
    def validate_signal(self, signal, atr):
        if signal["signal"] == "WAIT": return False
        if signal["confidence"] < self.config["min_confidence"]:
            log.info(f"Rejected: conf {signal['confidence']}% < {self.config['min_confidence']}%")
            return False
        try:
            rr = float(str(signal.get("risk_reward", "1:1")).split(":")[1])
            if rr < self.config["min_risk_reward"]:
                log.info(f"Rejected: R:R {rr} < {self.config['min_risk_reward']}")
                return False
        except: return False

        try:
            entry = float(str(signal["entry_zone"]).split("-")[0])
            sl = float(signal["stop_loss"])
            sl_dist = abs(entry - sl)
            if sl_dist < self.config["min_sl_points"]: return False
            if sl_dist > self.config["max_sl_points"]: return False
            if sl_dist < atr * 0.8:
                log.info(f"Rejected: SL too tight vs ATR")
                return False
        except: return False
        return True

    # ─── Position sizing (the magic formula) ──────────────────────────────
    def calculate_quantity(self, entry, sl, confidence, vix=None):
        try:
            sl_f = float(sl)
            risk_rs = self.capital * self.config["risk_per_trade_pct"] / 100
            risk_per_unit = abs(entry - sl_f)
            if risk_per_unit <= 0: return 0

            units = risk_rs / risk_per_unit

            # Confidence multiplier
            if confidence >= 90: units *= 1.5
            elif confidence >= 75: units *= 1.0
            elif confidence >= 60: units *= 0.75
            else: units *= 0.5

            # VIX adjustment
            if vix:
                if vix > 25: units *= 0.5
                elif vix < 12: units *= 0.75

            # Loss streak penalty
            if self.consecutive_losses == 1: units *= 0.75
            elif self.consecutive_losses >= 2: units *= 0.5

            # Round to Nifty lot size (50)
            lot_size = 50
            lots = max(1, round(units / lot_size))
            qty = int(lots * lot_size)

            log.info(f"Position: {qty} units ({lots} lots) | Conf: {confidence}% | Risk: ₹{risk_rs:.0f}")
            return qty
        except Exception as e:
            log.error(f"Size error: {e}")
            return 0

    # ─── Trailing stop logic (3 stages) ───────────────────────────────────
    def update_trailing_stop(self, trade, current_price):
        d = trade["direction"]
        atr = trade["atr"]
        stage = trade.get("trail_stage", 0)
        current_sl = trade["stop_loss"]

        # Track extreme price
        if d == "BUY":
            trade["highest"] = max(trade.get("highest", trade["entry_price"]), current_price)
            t1, t2 = trade["target_1"], trade["target_2"]

            # Stage 0 → 1: breakeven after T1
            if stage == 0 and current_price >= t1:
                trade["stop_loss"] = trade["entry_price"] + 5
                trade["trail_stage"] = 1
                log.info(f"Trail 1: SL → breakeven+5 = {trade['stop_loss']:.2f}")
            # Stage 1 → 2: trail 2.5×ATR after T2
            elif stage == 1 and current_price >= t2:
                new_sl = trade["highest"] - (2.5 * atr)
                trade["stop_loss"] = max(current_sl, new_sl)
                trade["trail_stage"] = 2
                log.info(f"Trail 2: SL → {trade['stop_loss']:.2f}")
            # Stage 2: continuous trail
            elif stage == 2:
                new_sl = trade["highest"] - (2.5 * atr)
                if new_sl > current_sl:
                    trade["stop_loss"] = new_sl
        else:  # SELL
            trade["lowest"] = min(trade.get("lowest", trade["entry_price"]), current_price)
            t1, t2 = trade["target_1"], trade["target_2"]
            if stage == 0 and current_price <= t1:
                trade["stop_loss"] = trade["entry_price"] - 5
                trade["trail_stage"] = 1
            elif stage == 1 and current_price <= t2:
                new_sl = trade["lowest"] + (2.5 * atr)
                trade["stop_loss"] = min(current_sl, new_sl)
                trade["trail_stage"] = 2
            elif stage == 2:
                new_sl = trade["lowest"] + (2.5 * atr)
                if new_sl < current_sl:
                    trade["stop_loss"] = new_sl
        return trade

    # ─── Lifecycle ────────────────────────────────────────────────────────
    def on_trade_opened(self):
        self.trade_open = True
        self.trades_today += 1

    def on_trade_closed(self, pnl):
        self.trade_open = False
        self.daily_pnl += pnl
        self.weekly_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
            self.last_loss_time = datetime.now()
        else:
            self.consecutive_losses = 0
        log.info(f"PnL today: ₹{self.daily_pnl:.2f} | week: ₹{self.weekly_pnl:.2f}")
