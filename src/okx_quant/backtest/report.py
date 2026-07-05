"""Backtest report renderers."""

from __future__ import annotations

from okx_quant.backtest.engine import BacktestReport


def render_markdown_report(report: BacktestReport, *, max_trades: int = 20) -> str:
    data = report.as_dict()
    lines = [
        f"# Backtest Report: {data['strategy']} {data['inst_id']} {data['bar']}",
        "",
        "## Summary",
        "",
        f"- Period: `{data['first_ts']}` to `{data['last_ts']}`",
        f"- Initial cash: `{data['initial_cash']}`",
        f"- Final equity: `{data['final_equity']}`",
        f"- Net PnL: `{data['net_pnl']}`",
        f"- Gross PnL: `{data['gross_pnl']}`",
        f"- Total return: `{data['total_return']}`",
        f"- Max drawdown: `{data['max_drawdown']}`",
        f"- Total fee: `{data['total_fee']}`",
        f"- Fee / gross PnL: `{data['fee_to_gross_pnl']}`",
        f"- Turnover: `{data['turnover']}`",
        f"- Average trade edge: `{data['average_trade_edge']}`",
        f"- Number of trades: `{data['number_of_trades']}`",
        f"- Exposure time: `{data['exposure_time']}`",
        f"- Win rate: `{data['win_rate']}`",
        f"- Profit factor: `{data['profit_factor']}`",
        f"- Average win: `{data['average_win']}`",
        f"- Average loss: `{data['average_loss']}`",
        f"- Max consecutive losses: `{data['max_consecutive_losses']}`",
        "",
        "## Trades",
        "",
        "| ts | side | price | size | notional | fee | reason |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for trade in data["trades"][:max_trades]:
        lines.append(
            "| {ts} | {side} | {price} | {size} | {notional} | {fee} | {reason} |".format(**trade)
        )
    if len(data["trades"]) > max_trades:
        lines.append(f"| ... | ... | ... | ... | ... | ... | {len(data['trades']) - max_trades} more |")
    lines.append("")
    return "\n".join(lines)

