"""Serve the local monitoring dashboard."""

from __future__ import annotations

import argparse
from pathlib import Path

from okx_quant.dashboard.data import DashboardConfig
from okx_quant.dashboard.server import DashboardServerConfig, run_dashboard_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default="data/demo_rebalance_runner.sqlite3")
    parser.add_argument("--log-file", default="logs/demo_rebalance_runner_24h.jsonl")
    parser.add_argument("--summary-file", default="reports/demo_rebalance_runner_24h.json")
    parser.add_argument("--state-file", default="data/demo_rebalance_runner_state.json")
    parser.add_argument("--expected-interval-seconds", type=float, default=900.0)
    parser.add_argument("--max-events", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dashboard_server(
        DashboardServerConfig(
            host=args.host,
            port=args.port,
            dashboard=DashboardConfig(
                db_path=Path(args.db),
                log_path=Path(args.log_file),
                summary_path=Path(args.summary_file),
                state_path=Path(args.state_file),
                expected_interval_seconds=args.expected_interval_seconds,
                max_events=args.max_events,
            ),
        )
    )


if __name__ == "__main__":
    main()
