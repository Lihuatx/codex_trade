"""Collect a short OKX public WebSocket sample into SQLite."""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from pathlib import Path

from okx_quant.brokers.okx.ws_public import PublicWSSubscription, collect_public_messages
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/market.sqlite3")
    parser.add_argument("--inst", action="append", dest="inst_ids", default=None)
    parser.add_argument("--channel", action="append", dest="channels", default=None)
    parser.add_argument("--max-messages", type=int, default=12)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    inst_ids = args.inst_ids or ["BTC-USDT"]
    channels = args.channels or ["tickers", "books5", "trades"]
    subscriptions = [
        PublicWSSubscription(channel=channel, inst_id=inst_id)
        for inst_id in inst_ids
        for channel in channels
    ]
    messages = await collect_public_messages(
        subscriptions,
        max_messages=args.max_messages,
        timeout_seconds=args.timeout_seconds,
    )

    counts: Counter[str] = Counter()
    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        for message in messages:
            channel = message.channel or "unknown"
            counts[channel] += 1
            store.insert_market_raw(
                source="okx_ws_public",
                channel=channel,
                inst_id=message.inst_id,
                payload=message.payload,
                received_at=message.received_at,
            )
        store.commit()
        print(
            {
                "db": str(Path(args.db).resolve()),
                "messages": len(messages),
                "by_channel": dict(counts),
                "raw_rows": store.count("market_raw"),
            }
        )


if __name__ == "__main__":
    asyncio.run(run())

