"""News fetch + AI sentiment analysis."""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Optional
from urllib.request import urlopen, Request

from features.db_store import FeaturesDB

log = logging.getLogger("News")


class NewsService:
    RSS_URLS = [
        ("Google News", "https://news.google.com/rss/search?q=NSE+stock+market+India&hl=en-IN&gl=IN&ceid=IN:en"),
        ("Google Nifty", "https://news.google.com/rss/search?q=Nifty+50&hl=en-IN&gl=IN&ceid=IN:en"),
    ]

    def __init__(self, db: FeaturesDB):
        self.db = db

    def fetch_live_news(self, limit: int = 20) -> list[dict]:
        items = []
        for source, url in self.RSS_URLS:
            try:
                req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(req, timeout=10) as resp:
                    root = ET.fromstring(resp.read())
                for item in root.findall(".//item")[:limit // 2]:
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    pub = item.findtext("pubDate", "")
                    sentiment = self._quick_sentiment(title)
                    items.append({
                        "title": title,
                        "source": source,
                        "url": link,
                        "published_at": pub,
                        "sentiment": sentiment,
                        "sentiment_label": "Positive" if sentiment > 0.2 else "Negative" if sentiment < -0.2 else "Neutral",
                        "summary": title[:200],
                    })
            except Exception as e:
                log.error(f"RSS fetch error ({source}): {e}")
        if items:
            self.db.save_news(items[:limit])
        return items[:limit] if items else self.db.get_news(limit)

    def _quick_sentiment(self, text: str) -> float:
        text = text.lower()
        pos = sum(1 for w in ["surge", "rally", "gain", "rise", "bull", "up", "high", "record", "profit"] if w in text)
        neg = sum(1 for w in ["fall", "drop", "crash", "bear", "down", "low", "loss", "decline", "weak"] if w in text)
        if pos + neg == 0:
            return 0
        return round((pos - neg) / (pos + neg), 2)

    async def analyze_with_claude(self, headline: str) -> Optional[str]:
        try:
            from trading_mcp.claude_agent import chat
            result = await chat(
                f"Analyze this market news headline for Indian stock market impact. "
                f"Give sentiment (Positive/Negative/Neutral), sector impact, and 2-sentence summary:\n\n{headline}",
                history=[],
                max_turns=1,
            )
            return result.get("reply")
        except Exception as e:
            log.error(f"Claude news analysis: {e}")
            return None

    def get_news_with_analysis(self, limit: int = 15) -> list[dict]:
        return self.fetch_live_news(limit)
