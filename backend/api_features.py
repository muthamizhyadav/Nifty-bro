"""REST API for extended trading features — mounted at /api/features."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from features.db_store import FeaturesDB
from features.market_dashboard import MarketDashboardService
from features.technical_service import TechnicalService
from features.portfolio_service import PortfolioService
from features.watchlist_service import WatchlistService
from features.news_service import NewsService
from features.alerts_service import AlertsService
from features.paper_trading_service import PaperTradingService
from features.options_service import OptionsService
from features.screener_service import ScreenerService
from features.ai_analysis import AIStockAnalysis
from features.journal_ai import JournalAIService

log = logging.getLogger("FeaturesAPI")

router = APIRouter(tags=["features"])

_features_db: Optional[FeaturesDB] = None
_bot = None
_db = None


def init_features(bot, db):
    global _features_db, _bot, _db
    _bot = bot
    _db = db
    _features_db = FeaturesDB()
    _features_db.init()


def _broker():
    if not _bot:
        raise HTTPException(503, "Bot not initialized")
    return _bot.broker


# ── Pydantic models ──
class HoldingRequest(BaseModel):
    symbol: str
    qty: float
    avg_price: float

class WatchlistRequest(BaseModel):
    symbol: str

class AlertRequest(BaseModel):
    symbol: str
    alert_type: str
    condition: dict = {}
    message: str = ""

class PaperTradeRequest(BaseModel):
    symbol: str
    qty: int = 1

class JournalEntryRequest(BaseModel):
    symbol: str
    direction: str = "BUY"
    entry_price: float = 0
    exit_price: float = 0
    entry_reason: str = ""
    exit_reason: str = ""
    pnl: float = 0

class ScreenerRequest(BaseModel):
    rsi_min: Optional[float] = None
    rsi_max: Optional[float] = None
    trend: Optional[str] = None
    volume_surge: bool = False
    breakout: bool = False

class AIAnalysisRequest(BaseModel):
    symbol: str
    question: str = ""


# ── 1. Live Market Dashboard ──
@router.get("/market/dashboard")
async def market_dashboard():
    return MarketDashboardService(_broker()).get_dashboard()

@router.get("/market/indices")
async def market_indices():
    return MarketDashboardService(_broker()).get_indices()

@router.get("/market/movers")
async def market_movers():
    return MarketDashboardService(_broker()).get_movers()

@router.get("/market/sectors")
async def market_sectors():
    return MarketDashboardService(_broker()).get_sector_performance()

@router.get("/market/heatmap")
async def market_heatmap():
    return MarketDashboardService(_broker()).get_heatmap()

@router.get("/market/quote/{symbol}")
async def market_quote(symbol: str):
    rows = MarketDashboardService(_broker()).get_stock_quotes([symbol.upper()])
    if not rows:
        raise HTTPException(404, f"No quote for {symbol}")
    return rows[0]


# ── 2. AI Stock Analysis ──
@router.post("/ai/analyze")
async def ai_analyze(req: AIAnalysisRequest):
    return await AIStockAnalysis(_broker()).analyze_stock(req.symbol, req.question)

@router.get("/ai/explain/{symbol}")
async def ai_explain(symbol: str):
    return await AIStockAnalysis(_broker()).explain_movement(symbol.upper())


# ── 3. Portfolio ──
@router.get("/portfolio")
async def get_portfolio():
    return PortfolioService(_broker(), _features_db).get_portfolio()

@router.get("/portfolio/advisor")
async def portfolio_advisor():
    return PortfolioService(_broker(), _features_db).get_advisor_insights()

@router.post("/portfolio/holdings")
async def add_holding(req: HoldingRequest):
    PortfolioService(_broker(), _features_db).add_holding(req.symbol, req.qty, req.avg_price)
    return {"ok": True}

@router.delete("/portfolio/holdings/{holding_id}")
async def remove_holding(holding_id: int):
    PortfolioService(_broker(), _features_db).remove_holding(holding_id)
    return {"ok": True}


# ── 5. Watchlist ──
@router.get("/watchlist")
async def get_watchlist():
    return WatchlistService(_broker(), _features_db).get_watchlist()

@router.post("/watchlist")
async def add_watchlist(req: WatchlistRequest):
    WatchlistService(_broker(), _features_db).add(req.symbol)
    return {"ok": True}

@router.delete("/watchlist/{symbol}")
async def remove_watchlist(symbol: str):
    WatchlistService(_broker(), _features_db).remove(symbol)
    return {"ok": True}


# ── 6. News ──
@router.get("/news")
async def get_news(limit: int = 20):
    return NewsService(_features_db).get_news_with_analysis(limit)

@router.post("/news/analyze")
async def analyze_news_headline(headline: str):
    result = await NewsService(_features_db).analyze_with_claude(headline)
    return {"analysis": result}


# ── 7. Technical Analysis ──
@router.get("/technical/{symbol}")
async def technical_analysis(symbol: str):
    return TechnicalService(_broker()).analyze(symbol.upper())

@router.get("/technical/{symbol}/patterns")
async def candlestick_patterns(symbol: str):
    return TechnicalService(_broker()).detect_patterns(symbol.upper())


# ── 9. Alerts ──
@router.get("/alerts")
async def list_alerts():
    return AlertsService(_broker(), _features_db).list_alerts()

@router.post("/alerts")
async def create_alert(req: AlertRequest):
    aid = AlertsService(_broker(), _features_db).create_alert(
        req.symbol, req.alert_type, req.condition, req.message)
    return {"ok": True, "id": aid}

@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    AlertsService(_broker(), _features_db).delete_alert(alert_id)
    return {"ok": True}

@router.get("/alerts/check")
async def check_alerts():
    return AlertsService(_broker(), _features_db).check_alerts()


# ── 10. Paper Trading ──
@router.get("/paper/account")
async def paper_account():
    return PaperTradingService(_broker(), _features_db).get_account()

@router.post("/paper/buy")
async def paper_buy(req: PaperTradeRequest):
    return PaperTradingService(_broker(), _features_db).buy(req.symbol, req.qty)

@router.post("/paper/sell")
async def paper_sell(req: PaperTradeRequest):
    return PaperTradingService(_broker(), _features_db).sell(req.symbol, req.qty)

@router.get("/paper/trades")
async def paper_trades(limit: int = 50):
    return PaperTradingService(_broker(), _features_db).get_trades(limit)

@router.get("/paper/leaderboard")
async def paper_leaderboard():
    return PaperTradingService(_broker(), _features_db).get_leaderboard()


# ── 11. Options ──
@router.get("/options")
async def options_dashboard():
    return OptionsService(_broker()).get_dashboard()


# ── 12. AI Journal ──
@router.get("/journal")
async def get_journal(limit: int = 50):
    return JournalAIService(_features_db, _db).get_entries(limit)

@router.post("/journal")
async def add_journal_entry(req: JournalEntryRequest):
    return JournalAIService(_features_db, _db).add_entry(req.model_dump())

@router.get("/journal/ai-analysis")
async def journal_ai_analysis():
    return await JournalAIService(_features_db, _db).analyze_performance()


# ── 14. Screener ──
@router.get("/screener/presets")
async def screener_presets():
    return ScreenerService(_broker()).presets()

@router.post("/screener/run")
async def screener_run(req: ScreenerRequest):
    return ScreenerService(_broker()).screen(req.model_dump(exclude_none=True))

@router.get("/screener/preset/{name}")
async def screener_preset(name: str):
    presets = ScreenerService(_broker()).presets()
    if name not in presets:
        raise HTTPException(404, f"Unknown preset: {name}")
    f = presets[name]
    return ScreenerService(_broker()).screen({k: v for k, v in f.items() if k != "label"})
