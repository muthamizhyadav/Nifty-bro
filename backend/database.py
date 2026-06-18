"""SQLite database for trades, signals, candles."""

import sqlite3
import json
import logging
from datetime import datetime
from contextlib import contextmanager

log = logging.getLogger("DB")


class Database:
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
                CREATE TABLE IF NOT EXISTS candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tf TEXT, time INTEGER,
                    open REAL, high REAL, low REAL, close REAL, volume INTEGER
                );
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time TEXT, signal TEXT, confidence INTEGER,
                    entry_zone TEXT, stop_loss TEXT,
                    target_1 TEXT, target_2 TEXT, target_3 TEXT,
                    reasoning TEXT
                );
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_time TEXT, exit_time TEXT,
                    direction TEXT, qty INTEGER,
                    entry_price REAL, exit_price REAL,
                    stop_loss REAL, target REAL,
                    pnl REAL, result TEXT, reason TEXT
                );
            """)

    def save_candle(self, tf, c):
        with self.conn() as conn:
            conn.execute("INSERT INTO candles (tf,time,open,high,low,close,volume) VALUES (?,?,?,?,?,?,?)",
                         (tf, int(c["time"]), c["open"], c["high"], c["low"], c["close"], c.get("volume", 0)))

    def get_candles(self, limit=100, tf="15m"):
        with self.conn() as c:
            rows = c.execute("SELECT * FROM candles WHERE tf=? ORDER BY id DESC LIMIT ?", (tf, limit)).fetchall()
            return [dict(r) for r in reversed(rows)]

    def save_signal(self, s):
        with self.conn() as c:
            c.execute("""INSERT INTO signals (time,signal,confidence,entry_zone,stop_loss,target_1,target_2,target_3,reasoning)
                         VALUES (?,?,?,?,?,?,?,?,?)""",
                      (datetime.now().isoformat(), s.get("signal"), s.get("confidence"),
                       str(s.get("entry_zone", "")), str(s.get("stop_loss", "")),
                       str(s.get("target_1", "")), str(s.get("target_2", "")),
                       str(s.get("target_3", "")), s.get("reasoning", "")))

    def get_signals(self, limit=50):
        with self.conn() as c:
            rows = c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def save_trade(self, t):
        with self.conn() as c:
            c.execute("""INSERT INTO trades (entry_time,exit_time,direction,qty,entry_price,exit_price,stop_loss,target,pnl,result,reason)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                      (t.get("entry_time"), t.get("exit_time"), t.get("direction"),
                       t.get("qty_initial"), t.get("entry_price"), t.get("exit_price"),
                       t.get("original_sl"), t.get("target_2"),
                       t.get("final_pnl"), t.get("result"), t.get("exit_reason")))

    def get_trades(self, limit=100):
        with self.conn() as c:
            rows = c.execute("SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self):
        with self.conn() as c:
            total = c.execute("SELECT COUNT(*) as n FROM trades").fetchone()["n"]
            wins = c.execute("SELECT COUNT(*) as n FROM trades WHERE pnl > 0").fetchone()["n"]
            total_pnl = c.execute("SELECT COALESCE(SUM(pnl),0) as p FROM trades").fetchone()["p"]
            today = datetime.now().strftime("%Y-%m-%d")
            today_pnl = c.execute("SELECT COALESCE(SUM(pnl),0) as p FROM trades WHERE entry_time LIKE ?",
                                  (today + "%",)).fetchone()["p"]
            return {
                "total_trades": total, "wins": wins, "losses": total - wins,
                "win_rate": round(wins/total*100, 1) if total > 0 else 0,
                "total_pnl": round(total_pnl, 2),
                "today_pnl": round(today_pnl, 2)
            }
