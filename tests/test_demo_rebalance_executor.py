from datetime import datetime, timezone
from decimal import Decimal
import unittest

from okx_quant.domain.enums import OrderSide, OrderStatus
from okx_quant.domain.instruments import InstrumentRules
from okx_quant.domain.models import TradeIntent
from okx_quant.execution.demo_rebalance_executor import (
    active_local_orders,
    build_passive_post_only_order,
    passive_limit_price,
    select_first_actionable_intent,
)
from okx_quant.portfolio.rebalance_signal import RebalanceIntent, RiskCappedIntent


class DemoRebalanceExecutorTests(unittest.TestCase):
    def test_select_first_actionable_intent(self) -> None:
        blocked = _capped(actionable=False)
        actionable = _capped(actionable=True)

        self.assertIs(select_first_actionable_intent([blocked, actionable]), actionable)
        self.assertIsNone(select_first_actionable_intent([blocked]))

    def test_active_local_orders(self) -> None:
        active = active_local_orders(
            {
                "a": OrderStatus.ACCEPTED,
                "b": OrderStatus.CANCELLED,
                "c": OrderStatus.UNKNOWN,
            }
        )

        self.assertEqual(active, {"a": OrderStatus.ACCEPTED, "c": OrderStatus.UNKNOWN})

    def test_passive_limit_price_uses_safe_side_of_book(self) -> None:
        rules = _rules()

        buy_price = passive_limit_price(
            side=OrderSide.BUY,
            rules=rules,
            bid=Decimal("100.00"),
            ask=Decimal("100.10"),
            price_offset_bps=Decimal("10"),
        )
        sell_price = passive_limit_price(
            side=OrderSide.SELL,
            rules=rules,
            bid=Decimal("100.00"),
            ask=Decimal("100.10"),
            price_offset_bps=Decimal("10"),
        )

        self.assertEqual(buy_price, Decimal("99.9"))
        self.assertEqual(sell_price, Decimal("100.2"))

    def test_build_passive_post_only_order(self) -> None:
        now = datetime.now(timezone.utc)
        prepared = build_passive_post_only_order(
            capped_intent=_capped(actionable=True),
            trade_intent=TradeIntent(
                strategy_id="test",
                inst_id="BTC-USDT",
                side=OrderSide.SELL,
                notional=Decimal("10"),
                reference_price=Decimal("100"),
                reason="test",
                created_at=now,
            ),
            rules=_rules(),
            bid=Decimal("99.9"),
            ask=Decimal("100"),
            price_offset_bps=Decimal("10"),
            client_order_id="demo123",
        )

        self.assertEqual(prepared.request.client_order_id, "demo123")
        self.assertEqual(prepared.request.side, OrderSide.SELL)
        self.assertEqual(prepared.request.price, Decimal("100.1"))
        self.assertEqual(prepared.sized_order.rounded_notional, Decimal("9.9099"))


def _capped(*, actionable: bool) -> RiskCappedIntent:
    return RiskCappedIntent(
        intent=RebalanceIntent(
            asset="BTC",
            side=OrderSide.SELL,
            notional_usdt=Decimal("100"),
            current_weight=Decimal("0.8"),
            target_weight=Decimal("0.05"),
            reason="threshold_deviation",
        ),
        capped_notional_usdt=Decimal("10"),
        actionable=actionable,
        reasons=(),
    )


def _rules() -> InstrumentRules:
    return InstrumentRules(
        inst_id="BTC-USDT",
        base_ccy="BTC",
        quote_ccy="USDT",
        tick_size=Decimal("0.1"),
        lot_size=Decimal("0.001"),
        min_size=Decimal("0.001"),
    )


if __name__ == "__main__":
    unittest.main()
