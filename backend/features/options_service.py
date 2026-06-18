"""Options dashboard — chain, PCR, max pain, OI."""

import logging
from typing import Any, Optional

log = logging.getLogger("Options")


class OptionsService:
    def __init__(self, broker):
        self.broker = broker

    def get_dashboard(self, underlying: str = "NSE:NIFTY50-INDEX") -> dict[str, Any]:
        chain_data = self.broker.get_option_chain(underlying)
        vix = self.broker.get_vix()
        if not chain_data:
            return {"error": "Option chain unavailable", "vix": vix}

        return {
            "underlying": underlying,
            "spot": chain_data.get("spot", 0),
            "pcr": chain_data.get("pcr", 0),
            "pcr_signal": chain_data.get("pcr_signal", "Neutral"),
            "max_pain": chain_data.get("max_pain", 0),
            "max_call_oi_strike": chain_data.get("max_call_oi_strike", 0),
            "max_put_oi_strike": chain_data.get("max_put_oi_strike", 0),
            "oi_signal": chain_data.get("oi_signal", ""),
            "vix": vix,
            "vix_regime": self._vix_regime(vix),
            "greeks_note": "Greeks require per-strike option quotes from broker",
        }

    def _vix_regime(self, vix: Optional[float]) -> str:
        if not vix:
            return "Unknown"
        if vix < 12:
            return "Low volatility"
        if vix < 18:
            return "Normal"
        if vix < 25:
            return "High"
        return "Extreme"
