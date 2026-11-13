import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from trading_claude.core import Bar, Portfolio, orb_signal

class CoreTests(unittest.TestCase):
    def test_risk_duplicate_and_stop(self):
        p = Portfolio()
        self.assertEqual(p.enter("ABC", 10, 9, 12, "one", {"ABC": 10}), "FILLED_PAPER")
        self.assertEqual(p.positions["ABC"].quantity, 10)
        self.assertEqual(p.enter("ABC", 10, 9, 12, "one", {"ABC": 10}), "BLOCK_DUPLICATE")
        p.process_bar(Bar("ABC", datetime.now(ZoneInfo("UTC")), 10, 13, 8, 11, 100))
        self.assertEqual(p.events[-1]["reason"], "STOP")

    def test_orb(self):
        start = datetime(2026, 11, 12, 9, 30, tzinfo=ZoneInfo("America/New_York"))
        bars = [Bar("ABC", start + timedelta(minutes=i), 10, 10.2, 9.8, 10, 100) for i in range(1, 16)]
        bars.append(Bar("ABC", start + timedelta(minutes=16), 10, 11, 10, 10.5, 100))
        self.assertIsNotNone(orb_signal(bars))

if __name__ == "__main__":
    unittest.main()
