"""Collect OKX public REST metadata and historical candles into SQLite."""

from __future__ import annotations

import argparse
from pathlib import Path

from okx_quant.brokers.okx.client import OKXRestClient
from okx_quant.domain.market import parse_okx_candle_row
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/market.sqlite3")
    parser.add_argument("--inst", action="append", dest="inst_ids", default=None)
    parser.add_argument("--bar", default="1H")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inst_ids = args.inst_ids or ["BTC-USDT", "ETH-USDT"]
    client = OKXRestClient()

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()

        instruments = client.get_public_instruments("SPOT")
        store.insert_market_raw(
            source="okx_rest",
            channel="public/instruments",
            inst_id=None,
            payload=instruments,
        )

        total_candles = 0
        total_confirmed = 0
        for inst_id in inst_ids:
            payload = client.get_history_candles(inst_id, args.bar, args.limit)
            store.insert_market_raw(
                source="okx_rest",
                channel="market/history-candles",
                inst_id=inst_id,
                payload=payload,
            )
            for row in payload.get("data", []):
                candle = parse_okx_candle_row(inst_id, args.bar, row)
                store.upsert_candle(candle, "okx_rest")
                total_candles += 1
                if candle.confirm:
                    total_confirmed += 1

        store.commit()
        print(
            {
                "db": str(Path(args.db).resolve()),
                "raw_rows": store.count("market_raw"),
                "candles": store.count("candles"),
                "collected_candles": total_candles,
                "confirmed_candles": total_confirmed,
            }
        )


if __name__ == "__main__":
    main()

