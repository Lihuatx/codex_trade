from decimal import Decimal
import unittest

from okx_quant.domain.enums import OrderSide
from okx_quant.portfolio.rebalance_signal import PortfolioAsset, cap_rebalance_intents, generate_rebalance_signal


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

    def test_caps_large_intent_by_order_notional(self) -> None:
        signal = generate_rebalance_signal(
            cash_usdt=Decimal("100"),
            assets=[PortfolioAsset("BTC", Decimal("1"), Decimal("900"))],
            target_weights={"USDT": Decimal("0.9"), "BTC": Decimal("0.1")},
            threshold=Decimal("0.05"),
            min_trade_notional=Decimal("10"),
        )

        capped = cap_rebalance_intents(
            signal,
            max_order_notional=Decimal("10"),
            max_total_crypto_exposure=Decimal("30"),
            min_trade_notional=Decimal("10"),
        )

        self.assertEqual(capped[0].capped_notional_usdt, Decimal("10"))
        self.assertTrue(capped[0].actionable)
        self.assertIn("max_order_notional_capped", capped[0].reasons)

    def test_caps_buy_by_remaining_crypto_exposure(self) -> None:
        signal = generate_rebalance_signal(
            cash_usdt=Decimal("300"),
            assets=[PortfolioAsset("BTC", Decimal("0"), Decimal("100"))],
            target_weights={"USDT": Decimal("0.8"), "BTC": Decimal("0.2")},
            threshold=Decimal("0.05"),
            min_trade_notional=Decimal("10"),
        )

        capped = cap_rebalance_intents(
            signal,
            max_order_notional=Decimal("20"),
            max_total_crypto_exposure=Decimal("15"),
            min_trade_notional=Decimal("10"),
        )

        self.assertEqual(capped[0].capped_notional_usdt, Decimal("15"))
        self.assertTrue(capped[0].actionable)
        self.assertIn("max_total_crypto_exposure_capped", capped[0].reasons)


if __name__ == "__main__":
    unittest.main()
