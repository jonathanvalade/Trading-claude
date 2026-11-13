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
                   "halted": portfolio.halted}
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
            p.events = [json.loads(x[0]) for x in db.execute("SELECT payload FROM events ORDER BY id")]
        return p
