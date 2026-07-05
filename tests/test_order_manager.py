from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from okx_quant.domain.enums import OrderSide, OrderStatus, OrderType
from okx_quant.domain.models import Fill, Order
from okx_quant.oms.manager import OrderManager
from okx_quant.oms.state_machine import InvalidOrderTransition
from okx_quant.storage.sqlite_store import SQLiteEventStore


class OrderManagerTests(unittest.TestCase):
    def test_persists_order_status_and_fill(self) -> None:
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "oms.sqlite3"
            with SQLiteEventStore(db) as store:
                store.initialize()
                manager = OrderManager(store)
                order = _order()
                manager.create_order(order)
                manager.apply_status(client_order_id=order.client_order_id, next_status=OrderStatus.SUBMITTED)
                manager.apply_status(client_order_id=order.client_order_id, next_status=OrderStatus.ACCEPTED)
                manager.record_fill(_fill(order.client_order_id), final_status=OrderStatus.FILLED)
                store.commit()

                self.assertEqual(store.get_order_status(order.client_order_id), OrderStatus.FILLED)
                self.assertEqual(store.count("orders"), 1)
                self.assertEqual(store.count("fills"), 1)

    def test_rejects_invalid_transition(self) -> None:
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "oms.sqlite3"
            with SQLiteEventStore(db) as store:
                store.initialize()
                manager = OrderManager(store)
                order = _order()
                manager.create_order(order)

                with self.assertRaises(InvalidOrderTransition):
                    manager.apply_status(client_order_id=order.client_order_id, next_status=OrderStatus.FILLED)


def _order() -> Order:
    return Order(
        client_order_id="test-order",
        inst_id="BTC-USDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        size=Decimal("0.0003"),
        price=Decimal("60000.1"),
    )


def _fill(client_order_id: str) -> Fill:
    return Fill(
        fill_id="fill-1",
        client_order_id=client_order_id,
        exchange_order_id="okx-order",
        inst_id="BTC-USDT",
        side=OrderSide.BUY,
        price=Decimal("60000.1"),
        size=Decimal("0.0003"),
        fee=Decimal("0.018"),
        fee_ccy="USDT",
        filled_at=datetime.now(timezone.utc),
    )


if __name__ == "__main__":
    unittest.main()

