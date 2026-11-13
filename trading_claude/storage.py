"""Atomic SQLite persistence for paper portfolio state and events."""
import json
import sqlite3
from .core import Portfolio, Position, Config

class Store:
    def __init__(self, path="paper.db"):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)")

    def save(self, portfolio):
        payload = {"cash": portfolio.cash, "positions": {k: vars(v) for k, v in portfolio.positions.items()},
                   "realized_pnl_today": portfolio.realized_pnl_today, "seen_signals": list(portfolio.seen_signals),
                   "halted": portfolio.halted, "session_date": portfolio.session_date,\n                   "session_start_equity": portfolio.session_start_equity, "last_prices": portfolio.last_prices,\n                   "processed_bars": portfolio.processed_bars}
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO state(id,payload) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                       (json.dumps(payload),))
            db.execute("DELETE FROM events")
            db.executemany("INSERT INTO events(payload) VALUES(?)",
                           [(json.dumps(event),) for event in portfolio.events])

    def load(self, config=None):
        p = Portfolio(config=config or Config())
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT payload FROM state WHERE id=1").fetchone()
            if not row:
                return p
            raw = json.loads(row[0])
            p.cash = raw["cash"]
            p.positions = {k: Position(**v) for k, v in raw["positions"].items()}
            p.realized_pnl_today = raw["realized_pnl_today"]
            p.seen_signals = set(raw["seen_signals"])
            p.halted = raw["halted"]
            p.session_date = raw.get("session_date", "")
            p.session_start_equity = raw.get("session_start_equity", p.config.initial_capital_usd)
            p.last_prices = raw.get("last_prices", {})
            p.processed_bars = raw.get("processed_bars", {})
            p.events = [json.loads(x[0]) for x in db.execute("SELECT payload FROM events ORDER BY id")]
        return p
