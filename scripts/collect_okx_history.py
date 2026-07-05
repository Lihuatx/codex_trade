"""Collect paginated OKX historical candles into SQLite."""

from __future__ import annotations

import argparse
from pathlib import Path
import time

from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.domain.market import parse_okx_candle_row
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/history.sqlite3")
    parser.add_argument("--inst", action="append", dest="inst_ids", default=None)
    parser.add_argument("--bar", default="1H")
    parser.add_argument("--pages", type=int, default=10)
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--sleep-seconds", type=float, default=0.12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inst_ids = args.inst_ids or ["BTC-USDT", "ETH-USDT"]
    if args.limit > 300:
        raise ValueError("OKX history-candles limit cannot exceed 300")

    client = OKXRestClient()
    total_rows = 0
    total_confirmed = 0

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        for inst_id in inst_ids:
            after: str | None = None
            seen_oldest: set[str] = set()
            for page in range(args.pages):
                payload = client.get_history_candles(inst_id, args.bar, args.limit, after=after)
                rows = payload.get("data", [])
                store.insert_market_raw(
                    source="okx_rest",
                    channel="market/history-candles",
                    inst_id=inst_id,
                    payload={"page": page, "after": after, "payload": payload},
                )
                if not rows:
                    break
                for row in rows:
                    candle = parse_okx_candle_row(inst_id, args.bar, row)
                    store.upsert_candle(candle, "okx_rest")
                    total_rows += 1
                    if candle.confirm:
                        total_confirmed += 1

                oldest_ts = str(rows[-1][0])
                if oldest_ts in seen_oldest:
                    break
                seen_oldest.add(oldest_ts)
                after = oldest_ts
                if args.sleep_seconds > 0:
                    time.sleep(args.sleep_seconds)

        store.commit()
        print(
            {
                "db": str(Path(args.db).resolve()),
                "instruments": inst_ids,
                "bar": args.bar,
                "pages_requested": args.pages,
                "rows_seen": total_rows,
                "confirmed_rows_seen": total_confirmed,
                "candles_in_db": store.count("candles"),
                "raw_rows": store.count("market_raw"),
            }
        )


if __name__ == "__main__":
    main()

