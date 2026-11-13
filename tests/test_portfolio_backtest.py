import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from trading_claude.core import Bar, Config
from trading_claude.portfolio_backtest import replay, compare_portfolios

def history():
    start = datetime(2026, 11, 12, 9, 30, tzinfo=ZoneInfo("America/New_York"))
    bars = []
    for symbol in ("AAA", "BBB"):
        for minute in range(1, 391):
            close = 10.5 if minute >= 16 else 10
            high = 10.6 if minute >= 16 else 10.2
            low = 10 if minute >= 16 else 9.8
            bars.append(Bar(symbol, start + timedelta(minutes=minute),
                            close, high, low, close, 1000))
    return bars

class PortfolioReplayTests(unittest.TestCase):
    def test_shared_cash_and_ai_comparison(self):
        results = compare_portfolios(history(), approvals={})
        self.assertEqual(results["ai_gated"]["metrics"]["trade_count"], 0)
        self.assertEqual(results["rules_only"]["metrics"]["trade_count"], 2)
        self.assertGreaterEqual(results["rules_only"]["metrics"]["ending_equity"], 0)

    def test_max_positions(self):
        result = replay(history(), config=Config(max_open_positions=1))
        buys = [x for x in result["events"] if x["type"] == "BUY_SIMULATED"]
        self.assertEqual(len(buys), 1)

    def test_duplicate_bars_rejected(self):
        bars = history()
        with self.assertRaises(ValueError):
            replay(bars + [bars[0]])

if __name__ == "__main__":
    unittest.main()
