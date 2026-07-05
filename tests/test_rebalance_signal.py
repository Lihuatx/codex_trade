from decimal import Decimal
import unittest

from okx_quant.domain.enums import OrderSide
from okx_quant.portfolio.rebalance_signal import PortfolioAsset, generate_rebalance_signal


class RebalanceSignalTests(unittest.TestCase):
    def test_generates_sell_for_overweight_asset(self) -> None:
        signal = generate_rebalance_signal(
            cash_usdt=Decimal("500"),
            assets=[PortfolioAsset("BTC", Decimal("1"), Decimal("1000"))],
            target_weights={"USDT": Decimal("0.5"), "BTC": Decimal("0.5")},
            threshold=Decimal("0.05"),
            min_trade_notional=Decimal("10"),
        )

        self.assertEqual(len(signal.intents), 1)
        self.assertEqual(signal.intents[0].side, OrderSide.SELL)

    def test_generates_no_intent_inside_threshold(self) -> None:
        signal = generate_rebalance_signal(
            cash_usdt=Decimal("500"),
            assets=[PortfolioAsset("BTC", Decimal("0.5"), Decimal("1000"))],
            target_weights={"USDT": Decimal("0.5"), "BTC": Decimal("0.5")},
            threshold=Decimal("0.05"),
            min_trade_notional=Decimal("10"),
        )

        self.assertEqual(signal.intents, [])


if __name__ == "__main__":
    unittest.main()

