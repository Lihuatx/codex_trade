"""Validate stored candles for a symbol/bar."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from okx_quant.data_quality import validate_candles
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/market.sqlite3")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--bar", default="1H")
    parser.add_argument("--include-unconfirmed", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles = store.list_candles(
            inst_id=args.inst,
            bar=args.bar,
            confirmed_only=not args.include_unconfirmed,
        )
    issues = validate_candles(candles, bar=args.bar)
    print(
        json.dumps(
            {
                "db": str(Path(args.db).resolve()),
                "inst": args.inst,
                "bar": args.bar,
                "candles": len(candles),
                "issue_count": len(issues),
                "issues": [issue.as_dict() for issue in issues[:20]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

