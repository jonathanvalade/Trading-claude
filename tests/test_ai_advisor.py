import unittest
from trading_claude.ai_advisor import parse_advice

class AdvisorTests(unittest.TestCase):
    def test_approve(self):
        self.assertEqual(parse_advice({"decision": "APPROVE", "reason": "test"}).decision, "APPROVE")
    def test_reject_bad_output(self):
        for bad in ({}, {"decision": "BUY", "reason": "test"}, {"decision": "APPROVE", "reason": ""}, []):
            with self.assertRaises(ValueError):
                parse_advice(bad)

if __name__ == "__main__":
    unittest.main()
