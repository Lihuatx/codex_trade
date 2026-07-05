"""Run a parameter sweep for the trend-filter strategy."""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import json
from pathlib import Path

from okx_quant.backtest.cost_model import ExecutionCostModel
from okx_quant.backtest.engine import BacktestEngine
from okx_quant.storage.sqlite_store import SQLiteEventStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/history.sqlite3")
    parser.add_argument("--inst", default="BTC-USDT")
    parser.add_argument("--bar", default="1H")
    parser.add_argument("--initial-cash", default="1000")
    parser.add_argument("--taker-fee-bps", default="10")
    parser.add_argument("--slippage-bps", default="5")
    parser.add_argument("--ma-windows", default="10,20,50,100,200")
    parser.add_argument("--output", default=None)
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    windows = [int(item.strip()) for item in args.ma_windows.split(",") if item.strip()]
    engine = BacktestEngine(
        ExecutionCostModel(
            taker_fee_bps=Decimal(args.taker_fee_bps),
            slippage_bps=Decimal(args.slippage_bps),
        )
    )
    with SQLiteEventStore(Path(args.db)) as store:
        store.initialize()
        candles = store.list_candles(inst_id=args.inst, bar=args.bar, confirmed_only=True)

    rows = []
    for window in windows:
        if len(candles) < window:
            rows.append({"ma_window": window, "error": "not_enough_candles"})
            continue
        report = engine.run_trend_filter(candles, Decimal(args.initial_cash), ma_window=window)
        data = report.as_dict()
        rows.append(
            {
                "ma_window": window,
                "final_equity": data["final_equity"],
                "net_pnl": data["net_pnl"],
                "total_return": data["total_return"],
                "max_drawdown": data["max_drawdown"],
                "total_fee": data["total_fee"],
                "turnover": data["turnover"],
                "fee_to_gross_pnl": data["fee_to_gross_pnl"],
                "average_trade_edge": data["average_trade_edge"],
                "number_of_trades": data["number_of_trades"],
                "win_rate": data["win_rate"],
                "profit_factor": data["profit_factor"],
                "max_consecutive_losses": data["max_consecutive_losses"],
            }
        )

    text = _render(rows, args.format)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8", newline="")
        print({"output": str(Path(args.output).resolve()), "rows": len(rows)})
    else:
        print(text)


def _render(rows: list[dict[str, object]], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2)

    if not rows:
        return ""
    headers = list(rows[0].keys())
    output = []
    writer = csv.DictWriter(_ListWriter(output), fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return "".join(output)


class _ListWriter:
    def __init__(self, output: list[str]) -> None:
        self._output = output

    def write(self, value: str) -> int:
        self._output.append(value)
        return len(value)


if __name__ == "__main__":
    main()

