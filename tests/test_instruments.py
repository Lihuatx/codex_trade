from decimal import Decimal
import unittest

from okx_quant.domain.instruments import InstrumentRules


class InstrumentRulesTests(unittest.TestCase):
    def test_round_price_and_size(self) -> None:
        rules = InstrumentRules(
            inst_id="BTC-USDT",
            base_ccy="BTC",
            quote_ccy="USDT",
            tick_size=Decimal("0.1"),
            lot_size=Decimal("0.00001"),
            min_size=Decimal("0.0001"),
        )

        self.assertEqual(rules.round_price(Decimal("123.456")), Decimal("123.4"))
        self.assertEqual(rules.round_size(Decimal("0.123456")), Decimal("0.12345"))

    def test_validate_size_rejects_below_minimum(self) -> None:
        rules = InstrumentRules(
            inst_id="BTC-USDT",
            base_ccy="BTC",
            quote_ccy="USDT",
            tick_size=Decimal("0.1"),
            lot_size=Decimal("0.00001"),
            min_size=Decimal("0.0001"),
        )

        with self.assertRaises(ValueError):
            rules.validate_size(Decimal("0.00009"))


if __name__ == "__main__":
    unittest.main()

