"""
NIFTY 50 AI TRADING BOT — Main Engine
======================================
Full implementation with:
- Live Fyers WebSocket
- Advanced AI analysis (Claude with pro brain)
- 3-stage trailing stops
- Partial exits (50/30/20)
- Auto entry & exit
- Telegram alerts
- SQLite logging
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Callable, Optional

from config import CONFIG
from candle_utils import candle_bucket_ts, is_market_open
from brokers import get_broker
from analyzer import Analyzer
from risk_manager import RiskManager
from database import Database
from notifier import Notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
log = logging.getLogger("Bot")


class NiftyBot:
    def __init__(self, broadcast: Optional[Callable] = None):
        self.config = CONFIG
        self.broker = get_broker(CONFIG)
        self.analyzer = Analyzer(CONFIG)
        self.risk = RiskManager(CONFIG)
        self.db = Database()
        self.notifier = Notifier(CONFIG)
        self.broadcast_fn = broadcast or (lambda *a, **k: None)

        # Index = clean continuous data for chart, ticks, candles, signals, paper trades
        self.index_symbol = self.broker.format_instrument(CONFIG["instrument_symbol"])
        # Futures = only needed for LIVE order placement
        self.futures_symbol = self.broker.format_instrument(
            CONFIG["instrument_symbol"], CONFIG["instrument_expiry"]
        )
        # Use the index as the primary instrument (charting + paper trading).
        # For live trading, orders are routed to the futures contract.
        self.instrument = self.index_symbol

        self.candles_15m = []
        self.candles_1h = []
        self.current_15m = None
        self.current_1h = None
        self.t15_open = None
        self.t1h_open = None

        self.active_trade = None
        self.options_cache = None
        self.vix_cache = None
        self.last_refresh = 0
        self.running = False
        self.start_time = None
        self.last_ltp = 0.0
        self._forming_refresh_task = None

        log.info("=" * 60)
        log.info("NIFTY 50 AI BOT — Professional Edition")
        log.info(f"Broker: {CONFIG['broker'].upper()}")
        log.info(f"Mode: {'PAPER' if CONFIG['paper_trading'] else 'LIVE'}")
        log.info(f"Chart/Data: {self.index_symbol}")
        log.info(f"Orders (live): {self.futures_symbol}")
        log.info(f"Capital: ₹{CONFIG['capital']:,}")
        log.info(f"Risk/trade: {CONFIG['risk_per_trade_pct']}%")
        if not CONFIG['paper_trading']:
            log.warning(f"LIVE MODE: orders route to {self.futures_symbol} — "
                        f"verify this is the active monthly contract!")
        log.info("=" * 60)

    @property
    def uptime(self):
        return int(time.time() - self.start_time) if self.start_time else 0

    async def broadcast(self, event_type: str, data):
        try:
            await self.broadcast_fn({"type": event_type, "data": data, "ts": time.time()})
        except: pass

    # ─── Connection ───────────────────────────────────────────────────────
    async def start(self):
        if self.running: return
        self.running = True
        self.start_time = time.time()
        self.db.init()

        log.info("Loading historical candles...")
        await self._load_history()

        log.info("Connecting to Fyers WebSocket...")
        await self.broker.connect(self.on_tick)
        # Subscribe to INDEX for live chart ticks (continuous, always available).
        # Orders still go to the futures instrument.
        await self.broker.subscribe(self.index_symbol)
        await self.notifier.send(f"🟢 Bot STARTED\nMode: {'PAPER' if self.config['paper_trading'] else 'LIVE'}")
        await self.broadcast("bot_started", {"time": datetime.now().isoformat()})
        self._forming_refresh_task = asyncio.create_task(self._forming_candle_loop())
        log.info("Bot live — watching market")

    async def stop(self):
        self.running = False
        if self._forming_refresh_task:
            self._forming_refresh_task.cancel()
            self._forming_refresh_task = None
        await self.broker.disconnect()
        await self.notifier.send("🔴 Bot STOPPED")
        await self.broadcast("bot_stopped", {})

    async def _load_history(self):
        """
        Pre-load historical candles. Works 24/7 (even after market close)
        so the chart always shows the last session's candles.
        """
        from datetime import timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%d")
        try:
            # Index data — years of continuous candles, works 24/7
            c15 = self.broker.get_historical_candles(self.index_symbol, "15", from_date, today)
            c60 = self.broker.get_historical_candles(self.index_symbol, "60", from_date, today)
            self.candles_15m = c15[-500:] if c15 else []
            self.candles_1h = c60[-200:] if c60 else []
            log.info(f"Loaded {len(self.candles_15m)} 15m + {len(self.candles_1h)} 1H candles")

            self._seed_forming_candle(c15[-1] if c15 else None)

            if not self.candles_15m:
                log.warning("No historical candles. Check: (1) token valid? (2) instrument_expiry current month?")
            else:
                # Push to frontend so chart shows immediately, even after market close
                await self.broadcast("history_loaded", {"candles": self.candles_15m[-100:]})
        except Exception as e:
            log.error(f"History load error: {e}")

    def _seed_forming_candle(self, last_bar):
        """Align live bar with Fyers (TradingView) bucket."""
        if not last_bar:
            self.t15_open = None
            self.current_15m = None
            return
        last = dict(last_bar)
        now_bucket = candle_bucket_ts(time.time(), 15)
        if is_market_open() and last.get("time") == now_bucket:
            if self.candles_15m and self.candles_15m[-1].get("time") == now_bucket:
                self.candles_15m.pop()
            self.current_15m = last
            self.t15_open = now_bucket
            if last.get("close"):
                self.last_ltp = float(last["close"])
        else:
            self.t15_open = last.get("time")
            self.current_15m = None
            if last.get("close"):
                self.last_ltp = float(last["close"])

    async def _forming_candle_loop(self):
        """Refresh forming 15m bar from Fyers so OHLC matches TradingView."""
        while self.running:
            try:
                await asyncio.sleep(30)
                if is_market_open():
                    self._refresh_forming_candle_from_broker()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.debug(f"Forming candle refresh: {e}")

    def _refresh_forming_candle_from_broker(self):
        from datetime import timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        c15 = self.broker.get_historical_candles(self.index_symbol, "15", from_date, today)
        if not c15:
            return
        self._seed_forming_candle(c15[-1])

    def get_display_price(self) -> float:
        if self.last_ltp > 0:
            return self.last_ltp
        if self.current_15m and self.current_15m.get("close"):
            return float(self.current_15m["close"])
        if self.candles_15m:
            return float(self.candles_15m[-1].get("close", 0))
        return 0.0

    # ─── Tick handler ─────────────────────────────────────────────────────
    async def on_tick(self, message):
        try:
            ltp = float(message.get("ltp", 0))
            if ltp <= 0:
                return

            self.last_ltp = ltp

            # Build candle FIRST so we can include the live forming candle
            self._update_candle(ltp, 15)
            self._update_candle(ltp, 60)

            # Push tick + the live forming 15m candle so chart updates in real-time
            await self.broadcast("tick", {
                "price": ltp,
                "time": time.time(),
                "live_candle": self.current_15m,
            })

            # Refresh options + VIX every 10 min
            if time.time() - self.last_refresh > 600:
                self.last_refresh = time.time()
                asyncio.create_task(self._refresh_market_context())

            # Monitor active trade on every tick
            if self.active_trade:
                await self._monitor_trade(ltp)

        except Exception as e:
            log.debug(f"Tick error: {e}")

    async def _refresh_market_context(self):
        try:
            self.options_cache = self.broker.get_option_chain(self.index_symbol)
            vix = self.broker.get_vix()
            if vix:
                regime = self._vix_regime(vix)
                self.vix_cache = {"vix": vix, **regime}
                log.info(f"VIX: {vix} ({regime['regime']}) | PCR: {self.options_cache.get('pcr') if self.options_cache else 'N/A'}")
        except Exception as e:
            log.error(f"Context refresh: {e}")

    def _vix_regime(self, vix):
        if vix < 12: return {"regime": "Low", "action": "Reduce targets"}
        if vix < 18: return {"regime": "Normal", "action": "Standard"}
        if vix < 25: return {"regime": "High", "action": "Widen stops"}
        return {"regime": "Extreme", "action": "Halve position"}

    def _update_candle(self, price, minutes):
        if minutes == 15 and not is_market_open():
            return

        now = time.time()
        bucket = candle_bucket_ts(now, minutes)

        if minutes == 15:
            if self.t15_open is None:
                self.t15_open = bucket
                self.current_15m = {"open": price, "high": price, "low": price,
                                     "close": price, "volume": 0, "time": bucket}
                return
            if bucket > self.t15_open:
                if self.current_15m:
                    self.candles_15m.append(dict(self.current_15m))
                if len(self.candles_15m) > 500:
                    self.candles_15m = self.candles_15m[-500:]
                closed = dict(self.current_15m) if self.current_15m else None
                if closed:
                    self.db.save_candle("15m", closed)
                    log.info(f"15m close | C: {closed['close']:.2f}")
                    asyncio.create_task(self.broadcast("candle_close", {"tf": "15m", "candle": closed}))
                    asyncio.create_task(self._on_candle_close())
                self.t15_open = bucket
                self.current_15m = {"open": price, "high": price, "low": price,
                                     "close": price, "volume": 0, "time": bucket}
            elif self.current_15m:
                c = self.current_15m
                c["high"] = max(c["high"], price)
                c["low"] = min(c["low"], price)
                c["close"] = price
                # Keep Fyers volume on seeded bars; don't replace with tick count
        elif minutes == 60:
            if self.t1h_open is None:
                self.t1h_open = bucket
                self.current_1h = {"open": price, "high": price, "low": price,
                                    "close": price, "volume": 1, "time": bucket}
                return
            if bucket > self.t1h_open:
                self.candles_1h.append(dict(self.current_1h))
                if len(self.candles_1h) > 100:
                    self.candles_1h = self.candles_1h[-100:]
                self.t1h_open = bucket
                self.current_1h = {"open": price, "high": price, "low": price,
                                    "close": price, "volume": 1, "time": bucket}
            else:
                c = self.current_1h
                c["high"] = max(c["high"], price); c["low"] = min(c["low"], price)
                c["close"] = price; c["volume"] += 1

    # ─── On each 15m candle close — main decision ─────────────────────────
    async def _on_candle_close(self):
        if len(self.candles_15m) < 50:
            log.info(f"Building history... {len(self.candles_15m)}/50")
            return
        if not self.risk.is_trading_allowed() or self.active_trade:
            return

        # Compute everything
        indicators = self.analyzer.compute_indicators(self.candles_15m)
        pattern = self.analyzer.detect_pattern(self.candles_15m)

        await self.broadcast("analyzing", {"pattern": pattern, "indicators": indicators})

        # Send to Claude with all pro techniques
        signal = self.analyzer.get_signal(
            self.candles_15m, self.candles_1h, indicators, pattern,
            self.options_cache, self.vix_cache
        )
        if not signal:
            log.warning("Claude returned no signal")
            return

        log.info(f"Signal: {signal['signal']} | {signal.get('title', '')} | "
                 f"Conf: {signal.get('confidence', 0)}% | R:R {signal.get('risk_reward', 'N/A')}")
        self.db.save_signal(signal)
        await self.broadcast("signal", signal)

        if not self.risk.validate_signal(signal, indicators["atr"]):
            return

        await self._enter_trade(signal, indicators)

    # ─── Enter trade ──────────────────────────────────────────────────────
    async def _enter_trade(self, signal, indicators):
        if signal["signal"] == "WAIT":
            return

        try:
            entry_str = str(signal["entry_zone"])
            entry_price = float(entry_str.split("-")[0]) if "-" in entry_str else float(entry_str)
        except:
            entry_price = indicators["close"]

        sl = float(signal["stop_loss"])
        t1 = float(signal["target_1"])
        t2 = float(signal["target_2"])
        t3 = float(signal["target_3"])

        vix = self.vix_cache["vix"] if self.vix_cache else None
        qty = self.risk.calculate_quantity(entry_price, sl, signal["confidence"], vix)
        if qty <= 0:
            return

        direction = "BUY" if signal["signal"] == "LONG" else "SELL"

        # Place order (paper or live)
        if self.config["paper_trading"]:
            order_id = f"PAPER-{uuid.uuid4().hex[:8].upper()}"
            log.info(f"[PAPER] {direction} {qty}u @ ₹{entry_price:.2f}")
        else:
            order_id = self.broker.place_order(
                instrument=self.futures_symbol,  # live orders -> futures
                direction=direction, quantity=qty,
                order_type=self.config["order_type"],
                price=entry_price,
                product=self.config["product_type"]
            )
            if not order_id:
                log.error("Order placement failed")
                return

        self.active_trade = {
            "order_id": order_id, "direction": direction,
            "entry_price": entry_price, "stop_loss": sl, "original_sl": sl,
            "target_1": t1, "target_2": t2, "target_3": t3,
            "qty_initial": qty, "qty_remaining": qty,
            "atr": indicators["atr"], "trail_stage": 0,
            "partials_hit": [],
            "highest": entry_price, "lowest": entry_price,
            "entry_time": datetime.now().isoformat(),
            "signal": signal
        }
        self.risk.on_trade_opened()

        msg = (f"📈 TRADE OPENED\n{direction} {qty}u @ ₹{entry_price:.2f}\n"
               f"SL: {sl} | T1: {t1} | T2: {t2} | T3: {t3}\n"
               f"Confidence: {signal['confidence']}% | R:R {signal.get('risk_reward')}")
        await self.notifier.send(msg)
        await self.broadcast("trade_opened", self.active_trade)
        log.info("=" * 50)
        log.info(f"TRADE: {direction} {qty} @ {entry_price:.2f}")
        log.info(f"SL:{sl} | T1:{t1} | T2:{t2} | T3:{t3}")
        log.info("=" * 50)

    # ─── Monitor active trade ─────────────────────────────────────────────
    async def _monitor_trade(self, price):
        if not self.active_trade: return
        t = self.active_trade
        d = t["direction"]

        # Update trailing stop
        t = self.risk.update_trailing_stop(t, price)
        self.active_trade = t

        # Check SL hit (highest priority)
        sl_hit = (d == "BUY" and price <= t["stop_loss"]) or \
                 (d == "SELL" and price >= t["stop_loss"])
        if sl_hit:
            await self._exit_remaining(price, "STOPLOSS")
            return

        # T1 hit — partial exit 50%
        if "T1" not in t["partials_hit"]:
            t1_hit = (d == "BUY" and price >= t["target_1"]) or \
                     (d == "SELL" and price <= t["target_1"])
            if t1_hit:
                qty = max(50, int(t["qty_initial"] * 0.5 / 50) * 50)
                await self._partial_exit(qty, price, "T1")

        # T2 hit — partial exit 30%
        if "T1" in t["partials_hit"] and "T2" not in t["partials_hit"]:
            t2_hit = (d == "BUY" and price >= t["target_2"]) or \
                     (d == "SELL" and price <= t["target_2"])
            if t2_hit:
                qty = max(50, int(t["qty_initial"] * 0.3 / 50) * 50)
                await self._partial_exit(qty, price, "T2")

        # T3 hit — full exit
        if "T2" in t["partials_hit"]:
            t3_hit = (d == "BUY" and price >= t["target_3"]) or \
                     (d == "SELL" and price <= t["target_3"])
            if t3_hit:
                await self._exit_remaining(price, "T3")

    async def _partial_exit(self, qty, price, label):
        t = self.active_trade
        exit_dir = "SELL" if t["direction"] == "BUY" else "BUY"

        if not self.config["paper_trading"]:
            self.broker.place_order(
                instrument=self.futures_symbol, direction=exit_dir,
                quantity=qty, order_type="MARKET",
                product=self.config["product_type"]
            )

        pnl = ((price - t["entry_price"]) if t["direction"] == "BUY" else
               (t["entry_price"] - price)) * qty
        t["qty_remaining"] -= qty
        t["partials_hit"].append(label)

        log.info(f"PARTIAL [{label}]: {qty}u @ {price:.2f} | PnL: ₹{pnl:.2f}")
        await self.notifier.send(f"✅ {label} HIT @ ₹{price:.2f}\nPartial PnL: ₹{pnl:.0f}")
        await self.broadcast("partial_exit", {"label": label, "price": price, "pnl": pnl})

    async def _exit_remaining(self, price, reason):
        t = self.active_trade
        if t["qty_remaining"] <= 0:
            self.active_trade = None
            return

        exit_dir = "SELL" if t["direction"] == "BUY" else "BUY"
        if not self.config["paper_trading"]:
            self.broker.place_order(
                instrument=self.futures_symbol, direction=exit_dir,
                quantity=t["qty_remaining"], order_type="MARKET",
                product=self.config["product_type"]
            )

        pnl = ((price - t["entry_price"]) if t["direction"] == "BUY" else
               (t["entry_price"] - price)) * t["qty_remaining"]

        trade_record = {
            **t, "exit_price": price, "exit_reason": reason,
            "exit_time": datetime.now().isoformat(),
            "final_pnl": round(pnl, 2),
            "result": "WIN" if pnl > 0 else "LOSS"
        }
        self.db.save_trade(trade_record)
        self.risk.on_trade_closed(pnl)

        emoji = "🎯" if pnl > 0 else "🛑"
        await self.notifier.send(
            f"{emoji} TRADE CLOSED ({reason})\n"
            f"Exit: ₹{price:.2f}\nFinal PnL: ₹{pnl:.0f}"
        )
        await self.broadcast("trade_closed", trade_record)
        log.info("=" * 50)
        log.info(f"CLOSED [{reason}] @ {price:.2f} | PnL: ₹{pnl:.2f}")
        log.info("=" * 50)
        self.active_trade = None


if __name__ == "__main__":
    bot = NiftyBot()
    try:
        asyncio.run(bot.start())
        asyncio.run(asyncio.Event().wait())
    except KeyboardInterrupt:
        asyncio.run(bot.stop())