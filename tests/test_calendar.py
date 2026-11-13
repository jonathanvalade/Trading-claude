import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from trading_claude.calendar import can_enter, session, should_flatten

NY = ZoneInfo("America/New_York")

class CalendarTests(unittest.TestCase):
    def test_regular(self):
        self.assertTrue(can_enter(datetime(2026, 11, 12, 10, tzinfo=NY)))
        self.assertFalse(can_enter(datetime(2026, 11, 12, 9, 35, tzinfo=NY)))
        self.assertTrue(should_flatten(datetime(2026, 11, 12, 15, 56, tzinfo=NY)))

    def test_holiday_and_weekend(self):
        self.assertIsNone(session(datetime(2026, 11, 26, 10, tzinfo=NY)))
        self.assertIsNone(session(datetime(2026, 11, 14, 10, tzinfo=NY)))

    def test_early_close(self):
        self.assertTrue(should_flatten(datetime(2026, 11, 27, 12, 56, tzinfo=NY)))
        self.assertFalse(can_enter(datetime(2026, 11, 27, 12, 45, tzinfo=NY)))

if __name__ == "__main__":
    unittest.main()
