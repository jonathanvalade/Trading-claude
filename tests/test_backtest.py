import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from trading_claude.core import Bar
from trading_claude.backtest import Costs, run_backtest, compare, validate_history

def sample():
    ny = ZoneInfo("America/New_York")
    start = datetime(2026, 11, 12, 9, 30, tzinfo=ny)
    bars = []
    for minute in range(1, 391):
        price = 10.0
        high = 10.2
        low = 9.8
        if minute == 16:
            price, high, low = 10.5, 10.6, 10.0
        if minute == 17:
            price, high, low = 10.8, 11.2, 10.4
        if minute > 17:
            price, high, low = 10.8, 11.0, 10.5
        bars.append(Bar("ABC", start + timedelta(minutes=minute), price, high, low, price, 1000))
    return bars

class BacktestTests(unittest.TestCase):
    def test_next_bar_fill_and_costs(self):
        result = run_backtest(sample(), costs=Costs(slippage_bps=10, commission_per_share=0.01))
        buys = [e for e in result["events"] if e["type"] == "BUY_SIMULATED"]
        self.assertEqual(len(buys), 1)
        self.assertGreater(buys[0]["price"], 10.8)
        self.assertEqual(result["metrics"]["trade_count"], 1)

    def test_ai_rejection(self):
        result = compare(sample(), approvals={})
        self.assertEqual(result["ai_gated"]["metrics"]["trade_count"], 0)
        self.assertEqual(result["rules_only"]["metrics"]["trade_count"], 1)

    def test_bad_history(self):
        with self.assertRaises(ValueError):
            validate_history(sample()[:1] * 2)
        with self.assertRaises(ValueError):
            Costs(slippage_bps=-1)

if __name__ == "__main__":
    unittest.main()
