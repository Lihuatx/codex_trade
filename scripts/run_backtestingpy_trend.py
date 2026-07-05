"""Cross-check trend-filter results with backtesting.py."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from okx_quant.backtest.backtestingpy_adapter import run_backtestingpy_trend_filter
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/history_1d.sqlite3")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--bar", default="1D")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument("--ma-window", type=int, default=200)
    parser.add_argument("--taker-fee-bps", default="10")
    parser.add_argument("--slippage-bps", default="5")
    parser.add_argument("--fractional-unit", default="0.00000001")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles = store.list_candles(inst_id=args.inst, bar=args.bar, confirmed_only=True)

    result = run_backtestingpy_trend_filter(
        candles,
        initial_cash=Decimal(args.initial_cash),
        ma_window=args.ma_window,
        taker_fee_bps=Decimal(args.taker_fee_bps),
        slippage_bps=Decimal(args.slippage_bps),
        fractional_unit=Decimal(args.fractional_unit),
    )
    result.update({"inst": args.inst, "bar": args.bar, "candles": len(candles)})
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print({"output": str(Path(args.output).resolve())})
    else:
        print(text)


if __name__ == "__main__":
    main()
