"""
FYERS BROKER — Full API v3 Implementation
"""

import asyncio
import logging
import threading
from typing import Callable, Optional, Dict, Any

from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

from brokers.base import BrokerInterface

log = logging.getLogger("FyersBroker")


class FyersBroker(BrokerInterface):
    def __init__(self, config):
        self.config = config
        self.app_id = config["fyers_app_id"]
        self.access_token = config["fyers_access_token"]
        self.fyers_token = f"{self.app_id}:{self.access_token}"

        self.fyers = fyersModel.FyersModel(
            client_id=self.app_id,
            token=self.access_token,
            is_async=False,
            log_path=""
        )

        self.ws = None
        self.on_tick_callback = None
        self.subscribed = []
        self.loop = None
        log.info(f"Fyers initialized — App: {self.app_id}")

    def format_instrument(self, symbol: str, expiry: Optional[str] = None) -> str:
        if expiry:
            return f"NSE:{symbol}{expiry}FUT"
        if symbol in ("NIFTY50", "NIFTY"):
            return "NSE:NIFTY50-INDEX"
        if symbol == "BANKNIFTY":
            return "NSE:NIFTYBANK-INDEX"
        if symbol == "INDIAVIX":
            return "NSE:INDIAVIX-INDEX"
        return f"NSE:{symbol}"

    async def connect(self, on_tick: Callable):
        self.on_tick_callback = on_tick
        self.loop = asyncio.get_event_loop()

        def on_message(message):
            try:
                if self.on_tick_callback and self.loop:
                    asyncio.run_coroutine_threadsafe(
                        self.on_tick_callback(message), self.loop
                    )
            except Exception as e:
                log.debug(f"Tick error: {e}")

        def on_error(message): log.error(f"WS error: {message}")
        def on_close(message): log.warning(f"WS closed: {message}")
        def on_open():
            log.info("Fyers WS connected")
            for inst in self.subscribed:
                self.ws.subscribe(symbols=[inst], data_type="SymbolUpdate")

        self.ws = data_ws.FyersDataSocket(
            access_token=self.fyers_token,
            log_path="", litemode=False, write_to_file=False, reconnect=True,
            on_connect=on_open, on_close=on_close,
            on_error=on_error, on_message=on_message
        )
        threading.Thread(target=self.ws.connect, daemon=True).start()
        await asyncio.sleep(2)

    async def disconnect(self):
        if self.ws:
            try: self.ws.close_connection()
            except: pass

    async def subscribe(self, instrument: str):
        if instrument not in self.subscribed:
            self.subscribed.append(instrument)
        if self.ws:
            self.ws.subscribe(symbols=[instrument], data_type="SymbolUpdate")
            log.info(f"Subscribed: {instrument}")

    def get_quote(self, instrument: str) -> Dict[str, Any]:
        try:
            r = self.fyers.quotes({"symbols": instrument})
            if r.get("s") == "ok" and r.get("d"):
                d = r["d"][0]["v"]
                return {
                    "ltp": d.get("lp", 0),
                    "open": d.get("open_price", 0),
                    "high": d.get("high_price", 0),
                    "low": d.get("low_price", 0),
                    "close": d.get("prev_close_price", 0),
                    "volume": d.get("volume", 0),
                }
        except Exception as e:
            log.error(f"Quote error: {e}")
        return {}

    def get_historical_candles(self, instrument, timeframe, from_date, to_date):
        try:
            r = self.fyers.history({
                "symbol": instrument, "resolution": timeframe,
                "date_format": "1", "range_from": from_date,
                "range_to": to_date, "cont_flag": "1"
            })
            if r.get("s") == "ok":
                candles = r.get("candles", [])
                log.info(f"History {instrument} {timeframe}m: got {len(candles)} candles")
                return [{"time": c[0], "open": c[1], "high": c[2],
                         "low": c[3], "close": c[4], "volume": c[5]}
                        for c in candles]
            else:
                log.error(f"History fetch failed for {instrument}: {r}")
        except Exception as e:
            log.error(f"Historical error: {e}")
        return []

    def get_option_chain(self, underlying, expiry=None):
        try:
            data = {"symbol": underlying, "strikecount": 20}
            if expiry: data["timestamp"] = expiry
            r = self.fyers.optionchain(data=data)
            if r.get("s") == "ok":
                return self._parse_option_chain(r["data"]["optionsChain"], underlying)
        except Exception as e:
            log.error(f"Option chain error: {e}")
        return None

    def _parse_option_chain(self, chain, underlying):
        """Compute PCR, max pain, key levels from option chain."""
        try:
            spot_q = self.get_quote(underlying)
            spot = spot_q.get("ltp", 0) if spot_q else 0

            total_ce_oi = sum(c.get("oi", 0) for c in chain if c.get("option_type") == "CE")
            total_pe_oi = sum(c.get("oi", 0) for c in chain if c.get("option_type") == "PE")

            pcr = round(total_pe_oi / max(total_ce_oi, 1), 2)
            pcr_signal = ("Strongly bullish" if pcr > 1.4
                         else "Bullish" if pcr > 1.2
                         else "Strongly bearish" if pcr < 0.6
                         else "Bearish" if pcr < 0.8 else "Neutral")

            ce_strikes = sorted([c for c in chain if c.get("option_type") == "CE"],
                              key=lambda x: x.get("oi", 0), reverse=True)
            pe_strikes = sorted([c for c in chain if c.get("option_type") == "PE"],
                              key=lambda x: x.get("oi", 0), reverse=True)

            max_call_oi = ce_strikes[0]["strike_price"] if ce_strikes else 0
            max_put_oi = pe_strikes[0]["strike_price"] if pe_strikes else 0

            # Max pain calculation
            strikes = sorted(set(c["strike_price"] for c in chain))
            min_pain, max_pain = float("inf"), spot
            for strike in strikes:
                pain = 0
                for c in chain:
                    if c.get("option_type") == "CE" and c["strike_price"] < strike:
                        pain += (strike - c["strike_price"]) * c.get("oi", 0)
                    elif c.get("option_type") == "PE" and c["strike_price"] > strike:
                        pain += (c["strike_price"] - strike) * c.get("oi", 0)
                if pain < min_pain:
                    min_pain = pain; max_pain = strike

            return {
                "pcr": pcr, "pcr_signal": pcr_signal,
                "max_call_oi_strike": max_call_oi,
                "max_put_oi_strike": max_put_oi,
                "max_pain": max_pain,
                "spot": spot,
                "oi_signal": f"Call walls at {max_call_oi}, Put support at {max_put_oi}"
            }
        except Exception as e:
            log.error(f"Parse error: {e}")
            return None

    def get_vix(self):
        q = self.get_quote("NSE:INDIAVIX-INDEX")
        return q.get("ltp") if q else None

    def place_order(self, instrument, direction, quantity, order_type="LIMIT", price=0, product="INTRADAY"):
        side_map = {"BUY": 1, "SELL": -1}
        type_map = {"LIMIT": 1, "MARKET": 2, "SL": 3, "SL-M": 4}
        try:
            payload = {
                "symbol": instrument, "qty": quantity,
                "type": type_map.get(order_type, 1),
                "side": side_map.get(direction, 1),
                "productType": product,
                "limitPrice": price if order_type == "LIMIT" else 0,
                "stopPrice": 0, "validity": "DAY",
                "disclosedQty": 0, "offlineOrder": False
            }
            r = self.fyers.place_order(data=payload)
            if r.get("s") == "ok":
                log.info(f"Order: {direction} {quantity} @ {price} | {r.get('id')}")
                return r.get("id")
            log.error(f"Order rejected: {r.get('message')}")
        except Exception as e:
            log.error(f"Order error: {e}")
        return None

    def cancel_order(self, order_id):
        try:
            r = self.fyers.cancel_order(data={"id": order_id})
            return r.get("s") == "ok"
        except: return False

    def get_order_status(self, order_id):
        try:
            r = self.fyers.orderbook(data={"id": order_id})
            if r.get("s") == "ok" and r.get("orderBook"):
                s = r["orderBook"][0].get("status", 0)
                return {1: "cancelled", 2: "complete", 4: "transit",
                        5: "rejected", 6: "pending"}.get(s, "unknown")
        except: pass
        return "unknown"

    def get_positions(self):
        try:
            r = self.fyers.positions()
            if r.get("s") == "ok":
                return r.get("netPositions", [])
        except: pass
        return []

    def get_funds(self):
        try:
            r = self.fyers.funds()
            if r.get("s") == "ok" and r.get("fund_limit"):
                total = next((f["equityAmount"] for f in r["fund_limit"] if f.get("id") == 1), 0)
                avail = next((f["equityAmount"] for f in r["fund_limit"] if f.get("id") == 10), 0)
                return {"total": total, "available": avail, "used": total - avail}
        except: pass
        return {"total": 0, "available": 0, "used": 0}