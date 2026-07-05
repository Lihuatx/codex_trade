"""Run in-sample / out-of-sample checks for threshold rebalancing."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.backtest.rebalance import ThresholdRebalanceBacktest, align_candles
from okx_quant.domain.market import Candle
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/history_1d.sqlite3")
    parser.add_argument("--bar", default="1D")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument("--taker-fee-bps", default="10")
    parser.add_argument("--slippage-bps", default="5")
    parser.add_argument("--threshold", default="0.05")
    parser.add_argument("--min-trade-notional", default="10")
    parser.add_argument("--weights", default="USDT=0.5,BTC=0.25,ETH=0.25")
    parser.add_argument("--asset", action="append", dest="assets", default=None)
    parser.add_argument("--train-ratio", default="0.70")
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_ratio = Decimal(args.train_ratio)
    if train_ratio <= 0 or train_ratio >= 1:
        raise ValueError("train-ratio must be between 0 and 1")

    target_weights = _parse_weights(args.weights)
    asset_map = _parse_assets(args.assets or ["BTC=BTC-USDT", "ETH=ETH-USDT"])
    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles_by_asset = {
            asset: store.list_candles(inst_id=inst_id, bar=args.bar, confirmed_only=True)
            for asset, inst_id in asset_map.items()
        }

    aligned = align_candles(candles_by_asset)
    split_index = int(len(aligned) * float(train_ratio))
    train = _unalign(aligned[:split_index])
    test = _unalign(aligned[split_index:])
    engine = ThresholdRebalanceBacktest(
        ExecutionCostModel(
            taker_fee_bps=Decimal(args.taker_fee_bps),
            slippage_bps=Decimal(args.slippage_bps),
        )
    )

    result = {
        "strategy": "threshold_rebalance",
        "bar": args.bar,
        "weights": {asset: str(weight) for asset, weight in target_weights.items()},
        "threshold": args.threshold,
        "train_ratio": str(train_ratio),
        "train_candles": len(aligned[:split_index]),
        "test_candles": len(aligned[split_index:]),
        "in_sample": _run(engine, train, args, target_weights).as_dict(),
        "out_of_sample": _run(engine, test, args, target_weights).as_dict(),
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
    engine: ThresholdRebalanceBacktest,
    candles_by_asset: dict[str, list[Candle]],
    args: argparse.Namespace,
    target_weights: dict[str, Decimal],
):
    return engine.run(
        candles_by_asset,
        target_weights=target_weights,
        threshold=Decimal(args.threshold),
        initial_cash=Decimal(args.initial_cash),
        min_trade_notional=Decimal(args.min_trade_notional),
    )


def _unalign(aligned: list[dict[str, Candle]]) -> dict[str, list[Candle]]:
    result: dict[str, list[Candle]] = {}
    for row in aligned:
        for asset, candle in row.items():
            result.setdefault(asset, []).append(candle)
    return result


def _parse_weights(raw: str) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for item in raw.split(","):
        key, value = item.split("=", 1)
        result[key.strip()] = Decimal(value.strip())
    return result


def _parse_assets(raw_items: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in raw_items:
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


if __name__ == "__main__":
    main()
