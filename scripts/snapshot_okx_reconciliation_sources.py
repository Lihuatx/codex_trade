"""Fetch read-only OKX sources needed for reconciliation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.config import load_env_file, load_okx_settings
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--db", default="data/reconciliation_sources.sqlite3")
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

    snapshots = {
        "trade/orders-pending": client.get_orders_pending(inst_type=args.inst_type, inst_id=args.inst, limit=args.limit),
        "trade/orders-history": client.get_orders_history(inst_type=args.inst_type, inst_id=args.inst, limit=args.limit),
        "trade/fills": client.get_fills(inst_type=args.inst_type, inst_id=args.inst, limit=args.limit),
        "account/bills": client.get_bills(inst_type=args.inst_type, limit=args.limit),
    }

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        for channel, payload in snapshots.items():
            store.insert_market_raw(
                source=f"okx_rest_private_{settings.env}",
                channel=channel,
                inst_id=args.inst if channel.startswith("trade/") else None,
                payload=payload,
                received_at=datetime.now(timezone.utc),
            )
        store.commit()
        print(
            {
                "ok": all(payload.get("code") == "0" for payload in snapshots.values()),
                "env": settings.env,
                "simulated_trading": settings.simulated_trading,
                "counts": {channel: len(payload.get("data", [])) for channel, payload in snapshots.items()},
                "raw_rows": store.count("market_raw"),
                "db": str(Path(args.db).resolve()),
            }
        )


if __name__ == "__main__":
    main()

