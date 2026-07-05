from decimal import Decimal
import unittest

from okx_quant.brokers.okx.orders import (
    OKXCancelOrderRequest,
    OKXPlaceOrderRequest,
    decimal_to_okx_str,
    map_okx_order_state,
)
from okx_quant.domain.enums import OrderSide, OrderStatus, OrderType


class OKXOrderPayloadTests(unittest.TestCase):
    def test_limit_order_payload(self) -> None:
        order = OKXPlaceOrderRequest(
            inst_id="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            size=Decimal("0.00100000"),
            price=Decimal("60000.1000"),
            client_order_id="abc",
        )

        self.assertEqual(
            order.to_payload(),
            {
                "instId": "BTC-USDT",
                "tdMode": "cash",
                "side": "buy",
                "ordType": "limit",
                "sz": "0.001",
                "clOrdId": "abc",
                "px": "60000.1",
            },
        )

    def test_price_required_for_limit_order(self) -> None:
        order = OKXPlaceOrderRequest(
            inst_id="BTC-USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            size=Decimal("0.001"),
            client_order_id="abc",
        )

        with self.assertRaises(ValueError):
            order.to_payload()

    def test_cancel_payload_requires_one_id(self) -> None:
        with self.assertRaises(ValueError):
            OKXCancelOrderRequest(inst_id="BTC-USDT").to_payload()

    def test_order_state_mapping(self) -> None:
        self.assertEqual(map_okx_order_state("live"), OrderStatus.ACCEPTED)
        self.assertEqual(map_okx_order_state("partially_filled"), OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(map_okx_order_state("filled"), OrderStatus.FILLED)
        self.assertEqual(map_okx_order_state("canceled"), OrderStatus.CANCELLED)
        self.assertEqual(map_okx_order_state("something_new"), OrderStatus.UNKNOWN)

    def test_decimal_to_okx_str(self) -> None:
        self.assertEqual(decimal_to_okx_str(Decimal("1E-8")), "0.00000001")


if __name__ == "__main__":
    unittest.main()

