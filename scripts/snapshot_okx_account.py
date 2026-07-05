"""Fetch OKX demo/live account balances and persist account snapshots."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from okx_quant.brokers.okx.auth import OKXAuth
from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.config import load_env_file, load_okx_settings
from okx_quant.domain.account import parse_okx_account_balances
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--db", default="data/account_snapshot.sqlite3")
    parser.add_argument("--ccy", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_env_file(args.env_file)
    settings = load_okx_settings()
    settings.validate_for_private_api()
    client = OKXRestClient(
        auth=OKXAuth(
            api_key=settings.api_key,
            secret_key=settings.api_secret,
            passphrase=settings.passphrase,
            simulated_trading=settings.simulated_trading,
        )
    )
    payload = client.get_balance(args.ccy)
    balances = parse_okx_account_balances(payload)
    now = datetime.now(timezone.utc)

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        for balance in balances:
            store.insert_account_snapshot(
                snapshot_id=uuid4().hex,
                taken_at=now,
                ccy=balance.ccy,
                equity=balance.equity,
                available=balance.available,
                frozen=balance.frozen,
                source=f"okx_{settings.env}",
            )
        store.commit()
        selected = [
            {
                "ccy": balance.ccy,
                "equity": str(balance.equity),
                "available": str(balance.available),
                "frozen": str(balance.frozen),
            }
            for balance in balances
            if balance.ccy in {"USDT", "BTC", "ETH"}
        ]
        print(
            {
                "ok": payload.get("code") == "0",
                "env": settings.env,
                "simulated_trading": settings.simulated_trading,
                "balance_count": len(balances),
                "selected": selected,
                "account_snapshots": store.count("account_snapshots"),
                "db": str(Path(args.db).resolve()),
            }
        )


if __name__ == "__main__":
    main()

