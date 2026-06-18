"""Live market dashboard — indices, movers, sectors, heatmap."""

import logging
from typing import Any, Optional

from features.symbols import NIFTY50, INDICES, SECTORS, to_fyers

log = logging.getLogger("MarketDashboard")


class MarketDashboardService:
    def __init__(self, broker):
        self.broker = broker

    def _quote_row(self, symbol: str, name: str = "") -> Optional[dict]:
        fy = to_fyers(symbol) if not symbol.startswith("NSE:") and not symbol.startswith("BSE:") else symbol
        q = self.broker.get_quote(fy)
        if not q or not q.get("ltp"):
            return None
        prev = q.get("close") or q.get("ltp")
        chg = q["ltp"] - prev if prev else 0
        pct = (chg / prev * 100) if prev else 0
        return {
            "symbol": symbol.replace("NSE:", "").replace("-EQ", "").replace("-INDEX", ""),
            "name": name or symbol,
            "ltp": round(q["ltp"], 2),
            "open": round(q.get("open", 0), 2),
            "high": round(q.get("high", 0), 2),
            "low": round(q.get("low", 0), 2),
            "change": round(chg, 2),
            "change_pct": round(pct, 2),
            "volume": q.get("volume", 0),
        }

    def get_indices(self) -> list[dict]:
        out = []
        labels = {"NIFTY50": "Nifty 50", "BANKNIFTY": "Bank Nifty", "SENSEX": "Sensex", "INDIAVIX": "India VIX"}
        for key, fy_sym in INDICES.items():
            row = self._quote_row(fy_sym, labels.get(key, key))
            if row:
                row["index_key"] = key
                out.append(row)
        return out

    def get_stock_quotes(self, symbols: list[str]) -> list[dict]:
        rows = []
        for sym in symbols:
            row = self._quote_row(sym)
            if row:
                rows.append(row)
        return rows

    def get_movers(self) -> dict[str, Any]:
        quotes = self.get_stock_quotes(NIFTY50)
        if not quotes:
            return {"gainers": [], "losers": [], "most_active": []}
        sorted_pct = sorted(quotes, key=lambda x: x["change_pct"], reverse=True)
        sorted_vol = sorted(quotes, key=lambda x: x["volume"], reverse=True)
        return {
            "gainers": sorted_pct[:10],
            "losers": sorted_pct[-10:][::-1],
            "most_active": sorted_vol[:10],
        }

    def get_sector_performance(self) -> list[dict]:
        sectors = []
        for name, stocks in SECTORS.items():
            quotes = self.get_stock_quotes(stocks)
            if not quotes:
                continue
            avg_chg = sum(q["change_pct"] for q in quotes) / len(quotes)
            sectors.append({
                "sector": name,
                "change_pct": round(avg_chg, 2),
                "stocks_count": len(quotes),
                "top_stock": max(quotes, key=lambda x: x["change_pct"])["symbol"],
            })
        return sorted(sectors, key=lambda x: x["change_pct"], reverse=True)

    def get_heatmap(self) -> list[dict]:
        quotes = self.get_stock_quotes(NIFTY50)
        return [{
            "symbol": q["symbol"],
            "change_pct": q["change_pct"],
            "intensity": min(abs(q["change_pct"]) / 3.0, 1.0),
            "direction": "up" if q["change_pct"] >= 0 else "down",
        } for q in quotes]

    def get_dashboard(self) -> dict:
        return {
            "indices": self.get_indices(),
            "movers": self.get_movers(),
            "sectors": self.get_sector_performance(),
            "heatmap": self.get_heatmap(),
        }
