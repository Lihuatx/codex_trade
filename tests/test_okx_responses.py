import unittest

from okx_quant.brokers.okx.responses import parse_order_ack, parse_order_snapshot
from okx_quant.domain.enums import OrderStatus


class OKXResponseParsingTests(unittest.TestCase):
    def test_parse_order_ack(self) -> None:
        ack = parse_order_ack({"data": [{"clOrdId": "abc", "ordId": "123", "sCode": "0", "sMsg": ""}]})

        self.assertTrue(ack.ok)
        self.assertEqual(ack.client_order_id, "abc")
        self.assertEqual(ack.exchange_order_id, "123")

    def test_parse_order_snapshot(self) -> None:
        snapshot = parse_order_snapshot({"data": [{"clOrdId": "abc", "ordId": "123", "state": "canceled"}]})

        self.assertEqual(snapshot.status, OrderStatus.CANCELLED)
        self.assertEqual(snapshot.raw_state, "canceled")


if __name__ == "__main__":
    unittest.main()

