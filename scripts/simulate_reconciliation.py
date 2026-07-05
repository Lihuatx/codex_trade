"""Simulate an order-status reconciliation run."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from okx_quant.domain.enums import OrderSide, OrderStatus, OrderType
from okx_quant.domain.models import Order
from okx_quant.oms.manager import OrderManager
from okx_quant.reconciliation.orders import ExchangeOrderSnapshot, reconcile_order_statuses
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/reconcile_sim.sqlite3")
    parser.add_argument("--mismatch", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client_order_id = f"reconcile-{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        manager = OrderManager(store)
        manager.create_order(
            Order(
                client_order_id=client_order_id,
                inst_id="BTC-USDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=Decimal("60000.1"),
                size=Decimal("0.0003"),
                status=OrderStatus.CREATED,
            )
        )
        manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.SUBMITTED)
        manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.ACCEPTED)
        manager.apply_status(client_order_id=client_order_id, next_status=OrderStatus.FILLED)

        exchange_status = OrderStatus.CANCELLED if args.mismatch else OrderStatus.FILLED
        issues = reconcile_order_statuses(
            store.list_order_statuses(),
            [ExchangeOrderSnapshot(client_order_id=client_order_id, status=exchange_status)],
        )
        store.insert_reconciliation_run(
            run_id=uuid4().hex,
            started_at=now,
            finished_at=datetime.now(timezone.utc),
            status="failed" if issues else "passed",
            summary={"issue_count": len(issues), "issues": [issue.as_dict() for issue in issues]},
        )
        store.commit()
        print(
            {
                "db": str(Path(args.db).resolve()),
                "issue_count": len(issues),
                "issues": [issue.as_dict() for issue in issues],
                "reconciliation_runs": store.count("reconciliation_runs"),
            }
        )


if __name__ == "__main__":
    main()
