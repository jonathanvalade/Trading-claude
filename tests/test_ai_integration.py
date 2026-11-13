import os
import tempfile
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from trading_claude.core import Bar
from trading_claude.runner import cycle
from trading_claude.storage import Store
from trading_claude.ai_advisor import Advice

class FakeData:
    def bars(self, symbol, now=None):
        start = datetime(2026, 11, 12, 9, 30, tzinfo=ZoneInfo("America/New_York"))
        bars = [Bar(symbol, start + timedelta(minutes=i), 10, 10.2, 9.8, 10, 100)
                for i in range(1, 16)]
        bars.append(Bar(symbol, start + timedelta(minutes=16), 10, 11, 10, 10.5, 100))
        return bars

class FakeAdvisor:
    def __init__(self, decision):
        self.decision = decision
    def evaluate(self, signal, bars):
        if self.decision == "ERROR":
            raise RuntimeError("offline")
        return Advice(self.decision, "test")

class IntegrationTests(unittest.TestCase):
    def test_gate(self):
        now = datetime(2026, 11, 12, 9, 46, 10, tzinfo=ZoneInfo("America/New_York"))
        for decision, expected in [("APPROVE", 1), ("REJECT", 0), ("ERROR", 0)]:
            with self.subTest(decision=decision), tempfile.TemporaryDirectory() as folder:
                store = Store(os.path.join(folder, "test.db"))
                cycle(FakeData(), store, ["ABC"], now, FakeAdvisor(decision))
                self.assertEqual(len(store.load().positions), expected)

if __name__ == "__main__":
    unittest.main()
