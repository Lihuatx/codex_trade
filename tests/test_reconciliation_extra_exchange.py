import unittest

from okx_quant.domain.enums import OrderStatus
from okx_quant.reconciliation.orders import ExchangeOrderSnapshot, reconcile_order_statuses


class ExtraExchangeOrderReconciliationTests(unittest.TestCase):
    def test_can_ignore_exchange_orders_not_in_local_scope(self) -> None:
        issues = reconcile_order_statuses(
            {"local": OrderStatus.CANCELLED},
            [
                ExchangeOrderSnapshot("local", OrderStatus.CANCELLED),
                ExchangeOrderSnapshot("other", OrderStatus.CANCELLED),
            ],
            flag_extra_exchange_orders=False,
        )

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()

