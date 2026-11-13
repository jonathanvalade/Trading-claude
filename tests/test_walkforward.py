import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from trading_claude.core import Bar
from trading_claude.walkforward import split_sessions

class WalkForwardTests(unittest.TestCase):
    def test_disjoint_chronological_windows(self):
        start = datetime(2026, 11, 9, 10, tzinfo=ZoneInfo("America/New_York"))
        bars = [Bar("ABC", start + timedelta(days=i), 10, 11, 9, 10, 10) for i in range(6)]
        folds = list(split_sessions(bars, train_sessions=2, test_sessions=2, step_sessions=1))
        self.assertEqual(len(folds), 3)
        for fold in folds:
            self.assertLess(max(fold["train_dates"]), min(fold["test_dates"]))
            self.assertFalse(set(fold["train_dates"]) & set(fold["test_dates"]))

    def test_bad_window(self):
        with self.assertRaises(ValueError):
            list(split_sessions([], 0, 2))

if __name__ == "__main__":
    unittest.main()
