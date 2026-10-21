import unittest

from pearl_dashboard.calc import evaluate


class CalcTest(unittest.TestCase):
    def test_vast_cheapest_example(self):
        # 340 TH/s, 5.75 PRL/day per 370 TH/s, $2, $0.40/h, no fees
        e = evaluate(0.40, 340, 5.75 / 370, 2.0, 0)
        self.assertAlmostEqual(e["prl_day"], 5.284, places=2)
        self.assertAlmostEqual(e["cost_day"], 9.60)
        self.assertAlmostEqual(e["profit_day"], 0.968, places=2)
        self.assertAlmostEqual(e["breakeven_price"], 1.817, places=2)

    def test_fee_reduces_output(self):
        e = evaluate(0.40, 340, 5.75 / 370, 2.0, 0.05)
        self.assertAlmostEqual(e["prl_day"], 5.284 * 0.95, places=2)

    def test_no_price(self):
        e = evaluate(0.40, 340, 0.0155, None, 0)
        self.assertIsNone(e["profit_day"])
        self.assertIsNone(e["margin"])
        self.assertIsNotNone(e["breakeven_price"])


if __name__ == "__main__":
    unittest.main()
