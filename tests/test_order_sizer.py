from decimal import Decimal
import unittest

from okx_quant.domain.instruments import InstrumentRules
from okx_quant.execution.order_sizer import size_spot_limit_order_by_quote_notional


class OrderSizerTests(unittest.TestCase):
    def test_size_by_quote_notional_rounds_down_to_lot_size(self) -> None:
        rules = InstrumentRules(
            inst_id="BTC-USDT",
            base_ccy="BTC",
            quote_ccy="USDT",
            tick_size=Decimal("0.1"),
            lot_size=Decimal("0.00001"),
            min_size=Decimal("0.00001"),
        )

        sized = size_spot_limit_order_by_quote_notional(
            rules=rules,
            quote_notional=Decimal("20"),
            reference_price=Decimal("63000"),
        )

        self.assertEqual(sized.size, Decimal("0.00031"))
        self.assertEqual(sized.rounded_notional, Decimal("19.53000"))

    def test_rejects_size_below_minimum(self) -> None:
        rules = InstrumentRules(
            inst_id="BTC-USDT",
            base_ccy="BTC",
            quote_ccy="USDT",
            tick_size=Decimal("0.1"),
            lot_size=Decimal("0.00001"),
            min_size=Decimal("0.0001"),
        )

        with self.assertRaises(ValueError):
            size_spot_limit_order_by_quote_notional(
                rules=rules,
                quote_notional=Decimal("1"),
                reference_price=Decimal("63000"),
            )


if __name__ == "__main__":
    unittest.main()

