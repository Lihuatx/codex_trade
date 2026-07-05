"""Run a minimal backtest from SQLite candles."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.backtest.engine import BacktestEngine
from okx_quant.backtest.report import render_markdown_report
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/market.sqlite3")
    parser.add_argument("--strategy", choices=["buy-and-hold", "trend-filter"], default="buy-and-hold")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--bar", default="1H")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument("--taker-fee-bps", default="10")
    parser.add_argument("--slippage-bps", default="5")
    parser.add_argument("--ma-window", type=int, default=20)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cost_model = ExecutionCostModel(
        taker_fee_bps=Decimal(args.taker_fee_bps),
        slippage_bps=Decimal(args.slippage_bps),
    )
    engine = BacktestEngine(cost_model)

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles = store.list_candles(inst_id=args.inst, bar=args.bar, confirmed_only=True)

    if args.strategy == "buy-and-hold":
        report = engine.run_buy_and_hold(candles, Decimal(args.initial_cash))
    else:
        report = engine.run_trend_filter(candles, Decimal(args.initial_cash), args.ma_window)

    if args.format == "markdown":
        text = render_markdown_report(report)
    else:
        output = report.as_dict()
        output["trades"] = output["trades"][:20]
        text = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print({"output": str(Path(args.output).resolve())})
    else:
        print(text)


if __name__ == "__main__":
    main()
