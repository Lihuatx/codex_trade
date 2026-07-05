"""Run rolling walk-forward checks for the trend-filter strategy."""

from __future__ import annotations

import argparse
from decimal import Decimal
import json
from pathlib import Path

from okx_quant.backtest.cost_scenarios import CostScenario, parse_cost_scenarios
from okx_quant.backtest.engine import BacktestEngine, BacktestReport
from okx_quant.backtest.walk_forward import compact_report, rolling_windows, slice_window
from okx_quant.domain.market import Candle
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/history_1d.sqlite3")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--bar", default="1D")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument("--ma-windows", default="100,150,200,250")
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
    ma_windows = _parse_ints(args.ma_windows)
    initial_cash = Decimal(args.initial_cash)
    cost_scenarios = parse_cost_scenarios(args.cost_scenarios)

    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles = store.list_candles(inst_id=args.inst, bar=args.bar, confirmed_only=True)

    windows = rolling_windows(
        len(candles),
        train_size=args.train_size,
        test_size=args.test_size,
        step_size=args.step_size,
    )
    result = {
        "strategy": "trend_filter_walk_forward",
        "inst": args.inst,
        "bar": args.bar,
        "initial_cash": str(initial_cash),
        "ma_windows": ma_windows,
        "train_size": args.train_size,
        "test_size": args.test_size,
        "step_size": args.step_size,
        "cost_scenarios": [scenario.as_dict() for scenario in cost_scenarios],
        "windows": [
            _run_window(candles, window, ma_windows, initial_cash, scenario)
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
    candles: list[Candle],
    window,
    ma_windows: list[int],
    initial_cash: Decimal,
    scenario: CostScenario,
) -> dict[str, object]:
    train, test = slice_window(candles, window)
    engine = BacktestEngine(scenario.cost_model())
    train_reports = [
        (ma_window, engine.run_trend_filter(train, initial_cash, ma_window))
        for ma_window in ma_windows
        if len(train) >= ma_window and len(test) >= ma_window
    ]
    if not train_reports:
        raise ValueError("no ma_window can be evaluated with the selected train/test sizes")

    best_ma, best_train = max(train_reports, key=lambda item: item[1].total_return)
    test_report = engine.run_trend_filter(test, initial_cash, best_ma)
    return {
        "cost_scenario": scenario.name,
        "window_index": window.index,
        "train_start": train[0].ts.isoformat(),
        "train_end": train[-1].ts.isoformat(),
        "test_start": test[0].ts.isoformat(),
        "test_end": test[-1].ts.isoformat(),
        "selected_ma_window": best_ma,
        "train_selected": compact_report(best_train),
        "test": compact_report(test_report),
        "train_candidates": [
            {"ma_window": ma_window, **_candidate_summary(report)}
            for ma_window, report in train_reports
        ],
    }


def _candidate_summary(report: BacktestReport) -> dict[str, str | int | None]:
    return {
        "total_return": str(report.total_return),
        "max_drawdown": str(report.max_drawdown),
        "number_of_trades": report.number_of_trades,
        "profit_factor": str(report.profit_factor) if report.profit_factor is not None else None,
    }


def _parse_ints(raw: str) -> list[int]:
    values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("at least one integer value is required")
    return values


if __name__ == "__main__":
    main()
