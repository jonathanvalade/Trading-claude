import os
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from trading_claude.storage import Store
from trading_claude.runner import market_window

class StoreTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(os.path.join(folder, "paper.db"))
            p = store.load()
            p.enter("ABC", 10, 9, 12, "id1", {"ABC": 10})
            store.save(p)
            restored = store.load()
            self.assertEqual(restored.cash, 900)
            self.assertEqual(restored.positions["ABC"].quantity, 10)
            self.assertEqual(len(restored.events), 1)

    def test_window(self):
        ny = ZoneInfo("America/New_York")
        self.assertTrue(market_window(datetime(2026, 11, 12, 10, 0, tzinfo=ny)))
        self.assertFalse(market_window(datetime(2026, 11, 14, 10, 0, tzinfo=ny)))

if __name__ == "__main__":
    unittest.main()
