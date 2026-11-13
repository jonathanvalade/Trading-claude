import os
import tempfile
import unittest
from trading_claude.core import Portfolio
from trading_claude.storage import Store

class SessionRiskTests(unittest.TestCase):
    def test_unrealized_drawdown_blocks_entries(self):
        p = Portfolio()
        p.begin_session("2026-11-12")
        self.assertEqual(p.enter("ABC", 10, 9, 12, "a", {"ABC": 10}), "FILLED_PAPER")
        p.last_prices["ABC"] = 4
        self.assertTrue(p.check_drawdown())
        self.assertEqual(p.enter("XYZ", 10, 9, 12, "b", {"ABC": 4, "XYZ": 10}), "BLOCK_DAILY_LOSS")

    def test_new_session_resets_halt(self):
        p = Portfolio()
        p.begin_session("2026-11-12")
        p.halted = True
        p.begin_session("2026-11-13")
        self.assertFalse(p.halted)

    def test_risk_state_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(os.path.join(folder, "state.db"))
            p = store.load()
            p.begin_session("2026-11-12")
            p.halted = True
            p.last_prices["ABC"] = 42
            store.save(p)
            restored = store.load()
            self.assertTrue(restored.halted)
            self.assertEqual(restored.session_date, "2026-11-12")
            self.assertEqual(restored.last_prices["ABC"], 42)

if __name__ == "__main__":
    unittest.main()
