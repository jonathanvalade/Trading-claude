import os
import tempfile
import unittest
from trading_claude.dashboard import snapshot, PAGE
from trading_claude.storage import Store

class DashboardTests(unittest.TestCase):
    def test_snapshot_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(os.path.join(folder, "paper.db"))
            p = store.load()
            p.enter("ABC", 10, 9, 12, "signal", {"ABC": 10})
            store.save(p)
            result = snapshot(store)
            self.assertEqual(result["mode"], "PAPER_ONLY")
            self.assertEqual(result["positions"][0]["symbol"], "ABC")
            self.assertEqual(result["equity"], 1000)
            self.assertEqual(len(store.load().events), 1)

    def test_no_remote_assets(self):
        self.assertNotIn("<script src=", PAGE)
        self.assertIn("textContent", PAGE)

if __name__ == "__main__":
    unittest.main()
