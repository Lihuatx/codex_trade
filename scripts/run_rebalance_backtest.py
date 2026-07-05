"""Run a BTC/ETH/USDT threshold rebalancing backtest."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.backtest.rebalance import ThresholdRebalanceBacktest
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/history_1d.sqlite3")
    parser.add_argument("--bar", default="1D")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument("--taker-fee-bps", default="10")
    parser.add_argument("--spread-bps", default="0")
    parser.add_argument("--slippage-bps", default="5")
    parser.add_argument("--threshold", default="0.05")
    parser.add_argument("--min-trade-notional", default="10")
    parser.add_argument("--weights", default="USDT=0.5,BTC=0.25,ETH=0.25")
    parser.add_argument("--asset", action="append", dest="assets", default=None)
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_weights = _parse_weights(args.weights)
    asset_map = _parse_assets(args.assets or ["BTC=BTC-USDT", "ETH=ETH-USDT"])
    engine = ThresholdRebalanceBacktest(
        ExecutionCostModel(
            taker_fee_bps=Decimal(args.taker_fee_bps),
            spread_bps=Decimal(args.spread_bps),
            slippage_bps=Decimal(args.slippage_bps),
        )
    )

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles_by_asset = {
            asset: store.list_candles(inst_id=inst_id, bar=args.bar, confirmed_only=True)
            for asset, inst_id in asset_map.items()
        }

    report = engine.run(
        candles_by_asset,
        target_weights=target_weights,
        threshold=Decimal(args.threshold),
        initial_cash=Decimal(args.initial_cash),
        min_trade_notional=Decimal(args.min_trade_notional),
    )
    output = report.as_dict()
    output["trades"] = output["trades"][:50]
    text = json.dumps(output, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print({"output": str(Path(args.output).resolve())})
    else:
        print(text)


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
