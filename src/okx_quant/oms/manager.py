"""OMS service that enforces local state transitions before persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from okx_quant.domain.enums import OrderStatus
from okx_quant.domain.models import Fill, Order
from okx_quant.oms.state_machine import transition_order_status
from okx_quant.storage.sqlite_store import SQLiteEventStore


class OrderManager:
    def __init__(self, store: SQLiteEventStore) -> None:
        self._store = store

    def create_order(self, order: Order) -> None:
        self._store.insert_order(order)

    def apply_status(
        self,
        *,
        client_order_id: str,
        next_status: OrderStatus,
        exchange_order_id: str | None = None,
    ) -> None:
        current = self._store.get_order_status(client_order_id)
        transition_order_status(current, next_status)
        self._store.update_order_status(
            client_order_id=client_order_id,
            status=next_status,
            updated_at=datetime.now(timezone.utc),
            exchange_order_id=exchange_order_id,
        )

    def record_fill(self, fill: Fill, final_status: OrderStatus = OrderStatus.PARTIALLY_FILLED) -> None:
        self._store.insert_fill(fill)
        self.apply_status(client_order_id=fill.client_order_id, next_status=final_status)

