"""Smart alerts — price, volume, RSI, breakout, portfolio."""

import logging
from datetime import datetime
from typing import Any

from features.db_store import FeaturesDB
from features.symbols import to_fyers
from features.technical_service import TechnicalService

log = logging.getLogger("Alerts")


class AlertsService:
    def __init__(self, broker, db: FeaturesDB):
        self.broker = broker
        self.db = db
        self.tech = TechnicalService(broker)

    def create_alert(self, symbol: str, alert_type: str, condition: dict, message: str = "") -> int:
        return self.db.add_alert(symbol, alert_type, condition, message)

    def list_alerts(self) -> list[dict]:
        return self.db.get_alerts()

    def delete_alert(self, alert_id: int):
        self.db.delete_alert(alert_id)

    def check_alerts(self) -> list[dict]:
        triggered = []
        for alert in self.db.get_alerts():
            sym = alert["symbol"]
            cond = alert.get("condition_json", "{}")
            import json
            try:
                cond = json.loads(cond) if isinstance(cond, str) else cond
            except Exception:
                continue

            atype = alert["alert_type"]
            hit = False
            msg = alert.get("message", "")

            if atype == "price_above":
                ltp = self._ltp(sym)
                hit = ltp >= cond.get("value", 0)
                msg = msg or f"{sym} crossed above {cond.get('value')}"
            elif atype == "price_below":
                ltp = self._ltp(sym)
                hit = ltp <= cond.get("value", 999999)
                msg = msg or f"{sym} fell below {cond.get('value')}"
            elif atype == "rsi_above":
                analysis = self.tech.analyze(sym)
                rsi = analysis.get("indicators", {}).get("rsi", 50)
                hit = rsi >= cond.get("value", 70)
                msg = msg or f"{sym} RSI above {cond.get('value')} (now {rsi})"
            elif atype == "rsi_below":
                analysis = self.tech.analyze(sym)
                rsi = analysis.get("indicators", {}).get("rsi", 50)
                hit = rsi <= cond.get("value", 30)
                msg = msg or f"{sym} RSI below {cond.get('value')} (now {rsi})"
            elif atype == "breakout":
                analysis = self.tech.analyze(sym)
                res = analysis.get("support_resistance", {}).get("resistance", 0)
                hit = analysis.get("price", 0) > res
                msg = msg or f"{sym} broke resistance at {res}"

            if hit:
                triggered.append({
                    "alert_id": alert["id"],
                    "symbol": sym,
                    "type": atype,
                    "message": msg,
                    "time": datetime.now().isoformat(),
                })
        return triggered

    def _ltp(self, symbol: str) -> float:
        q = self.broker.get_quote(to_fyers(symbol))
        return q.get("ltp", 0) if q else 0
