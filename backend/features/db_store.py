"""Extended SQLite tables for portfolio, watchlist, alerts, paper trading, journal."""

import json
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

log = logging.getLogger("FeaturesDB")


class FeaturesDB:
    def __init__(self, path="bot.db"):
        self.path = path

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def init(self):
        with self.conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS portfolio_holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    qty REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    added_at TEXT
                );
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    added_at TEXT
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    alert_type TEXT,
                    condition_json TEXT,
                    message TEXT,
                    triggered INTEGER DEFAULT 0,
                    active INTEGER DEFAULT 1,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS paper_portfolio (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cash REAL DEFAULT 1000000,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS paper_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT, direction TEXT, qty INTEGER,
                    entry_price REAL, exit_price REAL,
                    entry_time TEXT, exit_time TEXT,
                    pnl REAL, status TEXT, reason TEXT
                );
                CREATE TABLE IF NOT EXISTS ai_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT, direction TEXT,
                    entry_price REAL, exit_price REAL,
                    entry_reason TEXT, exit_reason TEXT,
                    pnl REAL, ai_analysis TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS news_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT, source TEXT, url TEXT,
                    sentiment REAL, summary TEXT,
                    published_at TEXT, fetched_at TEXT
                );
            """)
            row = c.execute("SELECT id FROM paper_portfolio LIMIT 1").fetchone()
            if not row:
                c.execute("INSERT INTO paper_portfolio (cash, updated_at) VALUES (?,?)",
                          (1000000, datetime.now().isoformat()))

    # ── Portfolio ──
    def get_holdings(self):
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM portfolio_holdings").fetchall()]

    def add_holding(self, symbol, qty, avg_price):
        with self.conn() as c:
            c.execute("""INSERT INTO portfolio_holdings (symbol,qty,avg_price,added_at)
                           VALUES (?,?,?,?)""",
                      (symbol.upper(), qty, avg_price, datetime.now().isoformat()))

    def remove_holding(self, holding_id):
        with self.conn() as c:
            c.execute("DELETE FROM portfolio_holdings WHERE id=?", (holding_id,))

    # ── Watchlist ──
    def get_watchlist(self):
        with self.conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM watchlist ORDER BY id").fetchall()]

    def add_watchlist(self, symbol):
        with self.conn() as c:
            try:
                c.execute("INSERT INTO watchlist (symbol,added_at) VALUES (?,?)",
                          (symbol.upper(), datetime.now().isoformat()))
            except sqlite3.IntegrityError:
                pass

    def remove_watchlist(self, symbol):
        with self.conn() as c:
            c.execute("DELETE FROM watchlist WHERE symbol=?", (symbol.upper(),))

    # ── Alerts ──
    def get_alerts(self, active_only=True):
        with self.conn() as c:
            q = "SELECT * FROM alerts"
            if active_only:
                q += " WHERE active=1"
            return [dict(r) for r in c.execute(q + " ORDER BY id DESC").fetchall()]

    def add_alert(self, symbol, alert_type, condition, message=""):
        with self.conn() as c:
            c.execute("""INSERT INTO alerts (symbol,alert_type,condition_json,message,created_at)
                         VALUES (?,?,?,?,?)""",
                      (symbol, alert_type, json.dumps(condition), message, datetime.now().isoformat()))
            return c.execute("SELECT last_insert_rowid()").fetchone()[0]

    def delete_alert(self, alert_id):
        with self.conn() as c:
            c.execute("UPDATE alerts SET active=0 WHERE id=?", (alert_id,))

    # ── Paper trading ──
    def get_paper_cash(self):
        with self.conn() as c:
            row = c.execute("SELECT cash FROM paper_portfolio ORDER BY id LIMIT 1").fetchone()
            return row["cash"] if row else 1000000

    def update_paper_cash(self, cash):
        with self.conn() as c:
            c.execute("UPDATE paper_portfolio SET cash=?, updated_at=? WHERE id=1",
                      (cash, datetime.now().isoformat()))

    def get_paper_trades(self, limit=100):
        with self.conn() as c:
            rows = c.execute("SELECT * FROM paper_trades ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def save_paper_trade(self, t):
        with self.conn() as c:
            c.execute("""INSERT INTO paper_trades
                (symbol,direction,qty,entry_price,exit_price,entry_time,exit_time,pnl,status,reason)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (t["symbol"], t["direction"], t["qty"], t["entry_price"],
                       t.get("exit_price"), t["entry_time"], t.get("exit_time"),
                       t.get("pnl", 0), t["status"], t.get("reason", "")))

    # ── AI Journal ──
    def save_journal_entry(self, entry):
        with self.conn() as c:
            c.execute("""INSERT INTO ai_journal
                (symbol,direction,entry_price,exit_price,entry_reason,exit_reason,pnl,ai_analysis,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                      (entry.get("symbol"), entry.get("direction"), entry.get("entry_price"),
                       entry.get("exit_price"), entry.get("entry_reason"), entry.get("exit_reason"),
                       entry.get("pnl"), entry.get("ai_analysis"), datetime.now().isoformat()))

    def get_journal_entries(self, limit=50):
        with self.conn() as c:
            rows = c.execute("SELECT * FROM ai_journal ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ── News cache ──
    def save_news(self, items):
        with self.conn() as c:
            for item in items:
                c.execute("""INSERT INTO news_cache (title,source,url,sentiment,summary,published_at,fetched_at)
                             VALUES (?,?,?,?,?,?,?)""",
                          (item["title"], item.get("source", ""), item.get("url", ""),
                           item.get("sentiment", 0), item.get("summary", ""),
                           item.get("published_at", ""), datetime.now().isoformat()))

    def get_news(self, limit=30):
        with self.conn() as c:
            rows = c.execute("SELECT * FROM news_cache ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
