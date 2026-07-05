"""Reconcile local SQLite orders against OKX pending/history orders."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.config import load_env_file, load_okx_settings
from okx_quant.reconciliation.orders import parse_okx_order_snapshots, reconcile_order_statuses
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--db", default="data/demo_order_ws.sqlite3")
    parser.add_argument("--inst-type", default="SPOT")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env_file(args.env_file)
    settings = load_okx_settings()
    settings.validate_for_private_api()
    client = OKXRestClient(
        auth=OKXAuth(settings.api_key, settings.api_secret, settings.passphrase, settings.simulated_trading)
    )
    pending = client.get_orders_pending(inst_type=args.inst_type, inst_id=args.inst, limit=args.limit)
    history = client.get_orders_history(inst_type=args.inst_type, inst_id=args.inst, limit=args.limit)
    exchange_orders = parse_okx_order_snapshots([pending, history])

    now = datetime.now(timezone.utc)
    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        local_statuses = store.list_order_statuses()
        issues = reconcile_order_statuses(local_statuses, exchange_orders, flag_extra_exchange_orders=False)
        store.insert_reconciliation_run(
            run_id=uuid4().hex,
            started_at=now,
            finished_at=datetime.now(timezone.utc),
            status="failed" if issues else "passed",
            summary={
                "local_orders": len(local_statuses),
                "exchange_orders": len(exchange_orders),
                "issue_count": len(issues),
                "issues": [issue.as_dict() for issue in issues],
            },
        )
        store.commit()
        print(
            {
                "ok": not issues,
                "local_orders": len(local_statuses),
                "exchange_orders": len(exchange_orders),
                "issue_count": len(issues),
                "issues": [issue.as_dict() for issue in issues],
                "reconciliation_runs": store.count("reconciliation_runs"),
                "db": str(Path(args.db).resolve()),
            }
        )


if __name__ == "__main__":
    main()
