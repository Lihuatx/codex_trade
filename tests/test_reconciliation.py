import unittest

from okx_quant.domain.enums import OrderStatus
from okx_quant.reconciliation.orders import ExchangeOrderSnapshot, parse_okx_order_snapshots, reconcile_order_statuses


class OrderReconciliationTests(unittest.TestCase):
    def test_matching_statuses_have_no_issues(self) -> None:
        issues = reconcile_order_statuses(
            {"abc": OrderStatus.FILLED},
            [ExchangeOrderSnapshot(client_order_id="abc", status=OrderStatus.FILLED)],
        )

        self.assertEqual(issues, [])

    def test_detects_status_mismatch(self) -> None:
        issues = reconcile_order_statuses(
            {"abc": OrderStatus.FILLED},
            [ExchangeOrderSnapshot(client_order_id="abc", status=OrderStatus.CANCELLED)],
        )

        self.assertEqual(issues[0].code, "order_status_mismatch")

    def test_detects_missing_orders_on_both_sides(self) -> None:
        issues = reconcile_order_statuses(
            {"local-only": OrderStatus.FILLED},
            [ExchangeOrderSnapshot(client_order_id="exchange-only", status=OrderStatus.FILLED)],
        )

        self.assertEqual({issue.code for issue in issues}, {"missing_exchange_order", "missing_local_order"})

    def test_parse_okx_order_snapshots(self) -> None:
        snapshots = parse_okx_order_snapshots(
            [
                {
                    "data": [
                        {
                            "clOrdId": "abc",
                            "ordId": "123",
                            "state": "canceled",
                        }
                    ]
                }
            ]
        )

        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].client_order_id, "abc")
        self.assertEqual(snapshots[0].status, OrderStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
