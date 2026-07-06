"""Run the OKX demo rebalance executor continuously for burn-in."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

from okx_quant.execution.demo_rebalance_runner import (
    RunnerSettings,
    append_jsonl,
    build_executor_command,
    default_python_exe,
    load_runner_state,
    record_cycle_result,
    run_executor_subprocess,
    save_runner_state,
    should_continue,
    should_execute_cycle,
    utc_now,
    write_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.demo")
    parser.add_argument("--db", default="data/demo_rebalance_runner.sqlite3")
    parser.add_argument("--state-file", default="data/demo_rebalance_runner_state.json")
    parser.add_argument("--log-file", default=None)
    parser.add_argument("--summary-file", default=None)
    parser.add_argument("--duration-hours", type=float, default=24.0)
    parser.add_argument("--duration-seconds", type=float, default=None)
    parser.add_argument("--interval-seconds", type=float, default=900.0)
    parser.add_argument("--max-cycles", type=int, default=None)
    parser.add_argument("--max-consecutive-errors", type=int, default=3)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--override-read-only", action="store_true")
    parser.add_argument("--min-seconds-between-executions", type=float, default=10800.0)
    parser.add_argument("--max-executions-per-day", type=int, default=8)
    parser.add_argument("--executor-timeout-seconds", type=float, default=90.0)
    parser.add_argument("--weights", default="USDT=0.9,BTC=0.05,ETH=0.05")
    parser.add_argument("--threshold", default="0.08")
    parser.add_argument("--min-trade-notional", default="10")
    parser.add_argument("--max-order-notional", default="10")
    parser.add_argument("--max-total-crypto-exposure", default="30")
    parser.add_argument("--max-daily-loss", default="5")
    parser.add_argument("--max-spread-bps", default="20")
    parser.add_argument("--max-price-deviation-bps", default="30")
    parser.add_argument("--stale-market-data-seconds", type=int, default=10)
    parser.add_argument("--price-offset-bps", default="2")
    parser.add_argument("--cancel-after-seconds", type=float, default=3.0)
    parser.add_argument("--poll-timeout-seconds", type=float, default=20.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    duration_seconds = args.duration_seconds if args.duration_seconds is not None else args.duration_hours * 3600
    settings = RunnerSettings(
        duration_seconds=duration_seconds,
        interval_seconds=args.interval_seconds,
        max_cycles=args.max_cycles,
        execute=args.execute,
        override_read_only=args.override_read_only,
        min_seconds_between_executions=args.min_seconds_between_executions,
        max_executions_per_day=args.max_executions_per_day,
        max_consecutive_errors=args.max_consecutive_errors,
    )
    started_wall = utc_now()
    started_monotonic = time.monotonic()
    state_path = Path(args.state_file)
    log_path = Path(args.log_file) if args.log_file else Path("logs") / f"demo_rebalance_runner_{started_wall.strftime('%Y%m%d_%H%M%S')}.jsonl"
    summary_path = Path(args.summary_file) if args.summary_file else Path("reports") / f"demo_rebalance_runner_{started_wall.strftime('%Y%m%d_%H%M%S')}.json"
    state = load_runner_state(state_path, now=started_wall)

    stop_reason = "duration_or_cycle_limit"
    while should_continue(
        started_monotonic=started_monotonic,
        now_monotonic=time.monotonic(),
        state=state,
        settings=settings,
    ):
        cycle_started = utc_now()
        execute_this_cycle = should_execute_cycle(state, settings, cycle_started)
        command = build_executor_command(
            repo_root=repo_root,
            python_exe=default_python_exe(),
            env_file=args.env_file,
            db=args.db,
            weights=args.weights,
            threshold=args.threshold,
            min_trade_notional=args.min_trade_notional,
            max_order_notional=args.max_order_notional,
            max_total_crypto_exposure=args.max_total_crypto_exposure,
            max_daily_loss=args.max_daily_loss,
            max_spread_bps=args.max_spread_bps,
            max_price_deviation_bps=args.max_price_deviation_bps,
            stale_market_data_seconds=args.stale_market_data_seconds,
            price_offset_bps=args.price_offset_bps,
            cancel_after_seconds=args.cancel_after_seconds,
            poll_timeout_seconds=args.poll_timeout_seconds,
            execute=execute_this_cycle,
            override_read_only=args.override_read_only,
        )
        result = run_executor_subprocess(command, repo_root=repo_root, timeout_seconds=args.executor_timeout_seconds)
        cycle_finished = utc_now()
        record_cycle_result(state, result, executed_this_cycle=execute_this_cycle, now=cycle_finished)
        save_runner_state(state_path, state)

        log_event = {
            "runner_event": "cycle",
            "cycle": state.cycles,
            "started_at": cycle_started.isoformat(),
            "finished_at": cycle_finished.isoformat(),
            "execute_requested": args.execute,
            "executed_this_cycle": execute_this_cycle,
            "result": _compact_result(result),
            "state": state.as_dict(),
        }
        append_jsonl(log_path, log_event)
        print(json.dumps(log_event, ensure_ascii=False, separators=(",", ":")), flush=True)

        if state.consecutive_errors >= settings.max_consecutive_errors:
            stop_reason = "max_consecutive_errors"
            break

        elapsed = time.monotonic() - started_monotonic
        if elapsed >= settings.duration_seconds:
            break
        if settings.max_cycles is not None and state.cycles >= settings.max_cycles:
            break
        time.sleep(min(settings.interval_seconds, max(0.0, settings.duration_seconds - elapsed)))

    summary = {
        "ok": state.consecutive_errors < settings.max_consecutive_errors,
        "runner": "demo_rebalance_runner",
        "started_at": started_wall.isoformat(),
        "finished_at": utc_now().isoformat(),
        "stop_reason": stop_reason,
        "execute_requested": args.execute,
        "settings": {
            "duration_seconds": settings.duration_seconds,
            "interval_seconds": settings.interval_seconds,
            "max_cycles": settings.max_cycles,
            "max_consecutive_errors": settings.max_consecutive_errors,
            "min_seconds_between_executions": settings.min_seconds_between_executions,
            "max_executions_per_day": settings.max_executions_per_day,
        },
        "state": state.as_dict(),
        "log_file": str(log_path.resolve()),
        "summary_file": str(summary_path.resolve()),
        "db": str(Path(args.db).resolve()),
    }
    write_summary(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


def _compact_result(result: dict[str, object]) -> dict[str, object]:
    keep = {
        "ok",
        "stage",
        "reason",
        "client_order_id",
        "exchange_order_id",
        "side",
        "ord_type",
        "rounded_notional",
        "final_exchange_state",
        "local_status",
        "reconciliation_issues",
        "return_code",
        "stderr",
        "stderr_tail",
        "stdout",
    }
    compact = {key: value for key, value in result.items() if key in keep}
    if "risk" in result:
        compact["risk"] = result["risk"]
    return compact


if __name__ == "__main__":
    sys.exit(main())
