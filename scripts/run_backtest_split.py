"""Run in-sample / out-of-sample checks for a strategy."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.backtest.engine import BacktestEngine, BacktestReport
from okx_quant.domain.market import Candle
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/history.sqlite3")
    parser.add_argument("--strategy", choices=["buy-and-hold", "trend-filter"], default="trend-filter")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--bar", default="1D")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument("--taker-fee-bps", default="10")
    parser.add_argument("--spread-bps", default="0")
    parser.add_argument("--slippage-bps", default="5")
    parser.add_argument("--ma-window", type=int, default=200)
    parser.add_argument("--train-ratio", default="0.70")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_ratio = Decimal(args.train_ratio)
    if train_ratio <= 0 or train_ratio >= 1:
        raise ValueError("train-ratio must be between 0 and 1")

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles = store.list_candles(inst_id=args.inst, bar=args.bar, confirmed_only=True)

    split_index = int(len(candles) * float(train_ratio))
    train = candles[:split_index]
    test = candles[split_index:]
    engine = BacktestEngine(
        ExecutionCostModel(
            taker_fee_bps=Decimal(args.taker_fee_bps),
            spread_bps=Decimal(args.spread_bps),
            slippage_bps=Decimal(args.slippage_bps),
        )
    )

    result = {
        "inst": args.inst,
        "bar": args.bar,
        "strategy": args.strategy,
        "train_ratio": str(train_ratio),
        "train_candles": len(train),
        "test_candles": len(test),
        "in_sample": _run(engine, args.strategy, train, Decimal(args.initial_cash), args.ma_window).as_dict(),
        "out_of_sample": _run(engine, args.strategy, test, Decimal(args.initial_cash), args.ma_window).as_dict(),
    }
    result["in_sample"].pop("trades", None)
    result["out_of_sample"].pop("trades", None)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print({"output": str(Path(args.output).resolve())})
    else:
        print(text)


def _run(
    engine: BacktestEngine,
    strategy: str,
    candles: list[Candle],
    initial_cash: Decimal,
    ma_window: int,
) -> BacktestReport:
    if strategy == "buy-and-hold":
        return engine.run_buy_and_hold(candles, initial_cash)
    return engine.run_trend_filter(candles, initial_cash, ma_window=ma_window)


if __name__ == "__main__":
    main()
