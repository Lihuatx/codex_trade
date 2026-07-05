"""Run rolling walk-forward checks for threshold rebalancing."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from okx_quant.backtest.cost_scenarios import CostScenario, parse_cost_scenarios
from okx_quant.backtest.rebalance import RebalanceReport, ThresholdRebalanceBacktest, align_candles
from okx_quant.backtest.walk_forward import compact_report, rolling_windows, slice_window
from okx_quant.domain.market import Candle
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/history_1d.sqlite3")
    parser.add_argument("--bar", default="1D")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument("--thresholds", default="0.03,0.05,0.08,0.10")
    parser.add_argument("--min-trade-notional", default="10")
    parser.add_argument("--weights", default="USDT=0.5,BTC=0.25,ETH=0.25")
    parser.add_argument("--asset", action="append", dest="assets", default=None)
    parser.add_argument("--train-size", type=int, default=1095)
    parser.add_argument("--test-size", type=int, default=365)
    parser.add_argument("--step-size", type=int, default=365)
    parser.add_argument(
        "--cost-scenario",
        action="append",
        dest="cost_scenarios",
        default=None,
        help="Format: name:taker_fee_bps:spread_bps:slippage_bps",
    )
    parser.add_argument("--output", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thresholds = _parse_decimals(args.thresholds)
    target_weights = _parse_weights(args.weights)
    asset_map = _parse_assets(args.assets or ["BTC=BTC-USDT", "ETH=ETH-USDT"])
    initial_cash = Decimal(args.initial_cash)
    cost_scenarios = parse_cost_scenarios(args.cost_scenarios)

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles_by_asset = {
            asset: store.list_candles(inst_id=inst_id, bar=args.bar, confirmed_only=True)
            for asset, inst_id in asset_map.items()
        }

    aligned = align_candles(candles_by_asset)
    windows = rolling_windows(
        len(aligned),
        train_size=args.train_size,
        test_size=args.test_size,
        step_size=args.step_size,
    )
    result = {
        "strategy": "threshold_rebalance_walk_forward",
        "bar": args.bar,
        "initial_cash": str(initial_cash),
        "weights": {asset: str(weight) for asset, weight in target_weights.items()},
        "thresholds": [str(threshold) for threshold in thresholds],
        "min_trade_notional": args.min_trade_notional,
        "train_size": args.train_size,
        "test_size": args.test_size,
        "step_size": args.step_size,
        "cost_scenarios": [scenario.as_dict() for scenario in cost_scenarios],
        "windows": [
            _run_window(aligned, window, thresholds, initial_cash, args, target_weights, scenario)
            for scenario in cost_scenarios
            for window in windows
        ],
    }

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print({"output": str(Path(args.output).resolve())})
    else:
        print(text)


def _run_window(
    aligned: list[dict[str, Candle]],
    window,
    thresholds: list[Decimal],
    initial_cash: Decimal,
    args: argparse.Namespace,
    target_weights: dict[str, Decimal],
    scenario: CostScenario,
) -> dict[str, object]:
    train_rows, test_rows = slice_window(aligned, window)
    train = _unalign(train_rows)
    test = _unalign(test_rows)
    engine = ThresholdRebalanceBacktest(scenario.cost_model())
    train_reports = [
        (
            threshold,
            engine.run(
                train,
                target_weights=target_weights,
                threshold=threshold,
                initial_cash=initial_cash,
                min_trade_notional=Decimal(args.min_trade_notional),
            ),
        )
        for threshold in thresholds
    ]
    best_threshold, best_train = max(train_reports, key=lambda item: item[1].total_return)
    test_report = engine.run(
        test,
        target_weights=target_weights,
        threshold=best_threshold,
        initial_cash=initial_cash,
        min_trade_notional=Decimal(args.min_trade_notional),
    )
    return {
        "cost_scenario": scenario.name,
        "window_index": window.index,
        "train_start": next(iter(train_rows[0].values())).ts.isoformat(),
        "train_end": next(iter(train_rows[-1].values())).ts.isoformat(),
        "test_start": next(iter(test_rows[0].values())).ts.isoformat(),
        "test_end": next(iter(test_rows[-1].values())).ts.isoformat(),
        "selected_threshold": str(best_threshold),
        "train_selected": compact_report(best_train),
        "test": compact_report(test_report),
        "train_candidates": [
            {"threshold": str(threshold), **_candidate_summary(report)}
            for threshold, report in train_reports
        ],
    }


def _candidate_summary(report: RebalanceReport) -> dict[str, str | int | None]:
    return {
        "total_return": str(report.total_return),
        "max_drawdown": str(report.max_drawdown),
        "number_of_trades": report.number_of_trades,
        "fee_to_gross_pnl": str(report.fee_to_gross_pnl) if report.fee_to_gross_pnl is not None else None,
    }


def _unalign(aligned: list[dict[str, Candle]]) -> dict[str, list[Candle]]:
    result: dict[str, list[Candle]] = {}
    for row in aligned:
        for asset, candle in row.items():
            result.setdefault(asset, []).append(candle)
    return result


def _parse_decimals(raw: str) -> list[Decimal]:
    values = [Decimal(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("at least one decimal value is required")
    return values


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
