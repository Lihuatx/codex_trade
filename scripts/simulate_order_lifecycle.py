"""Simulate a local order lifecycle and persist it to SQLite."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from okx_quant.domain.enums import OrderSide, OrderStatus, OrderType
from okx_quant.domain.models import Fill, Order, new_client_order_id
from okx_quant.oms.manager import OrderManager
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/oms_sim.sqlite3")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client_order_id = new_client_order_id("sim")
    exchange_order_id = "okx-simulated-local"

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        manager = OrderManager(store)
        manager.create_order(
            Order(
                client_order_id=client_order_id,
                exchange_order_id=None,
                inst_id="BTC-USDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=Decimal("60000.1"),
                size=Decimal("0.0003"),
            )
        )
        manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.SUBMITTED)
        manager.apply_status(
            client_order_id=client_order_id,
            next_status=OrderStatus.ACCEPTED,
            exchange_order_id=exchange_order_id,
        )
        manager.record_fill(
            Fill(
                fill_id="local-fill-1",
                client_order_id=client_order_id,
                exchange_order_id=exchange_order_id,
                inst_id="BTC-USDT",
                side=OrderSide.BUY,
                price=Decimal("60000.1"),
                size=Decimal("0.0003"),
                fee=Decimal("0.018"),
                fee_ccy="USDT",
                filled_at=datetime.now(timezone.utc),
            ),
            final_status=OrderStatus.FILLED,
        )
        store.commit()
        print(
            {
                "db": str(Path(args.db).resolve()),
                "client_order_id": client_order_id,
                "orders": store.count("orders"),
                "fills": store.count("fills"),
                "final_status": store.get_order_status(client_order_id).value,
            }
        )


if __name__ == "__main__":
    main()

