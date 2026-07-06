from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from okx_quant.execution.demo_rebalance_runner import (
    RunnerSettings,
    RunnerState,
    build_executor_command,
    record_cycle_result,
    should_continue,
    should_execute_cycle,
)


class DemoRebalanceRunnerTests(unittest.TestCase):
    def test_should_continue_respects_max_cycles(self) -> None:
        settings = _settings(max_cycles=1)
        state = RunnerState(started_at="2026-01-01T00:00:00+00:00", cycles=1)

        self.assertFalse(
            should_continue(started_monotonic=0, now_monotonic=1, state=state, settings=settings)
        )

    def test_should_continue_stops_on_consecutive_errors(self) -> None:
        settings = _settings(max_consecutive_errors=3)
        state = RunnerState(started_at="2026-01-01T00:00:00+00:00", consecutive_errors=3)

        self.assertFalse(
            should_continue(started_monotonic=0, now_monotonic=1, state=state, settings=settings)
        )

    def test_should_execute_cycle_respects_cooldown(self) -> None:
        now = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
        settings = _settings(execute=True, min_seconds_between_executions=3600)
        state = RunnerState(
            started_at="2026-01-01T00:00:00+00:00",
            last_execution_at=(now - timedelta(seconds=1800)).isoformat(),
        )

        self.assertFalse(should_execute_cycle(state, settings, now))

        state.last_execution_at = (now - timedelta(seconds=3601)).isoformat()
        self.assertTrue(should_execute_cycle(state, settings, now))

    def test_should_execute_cycle_respects_daily_limit(self) -> None:
        now = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
        settings = _settings(execute=True, max_executions_per_day=2)
        state = RunnerState(
            started_at="2026-01-01T00:00:00+00:00",
            executions_by_day={"2026-01-01": 2},
        )

        self.assertFalse(should_execute_cycle(state, settings, now))

    def test_record_cycle_result_tracks_execution(self) -> None:
        now = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
        state = RunnerState(started_at="2026-01-01T00:00:00+00:00")

        record_cycle_result(state, {"ok": True, "stage": "executed"}, executed_this_cycle=True, now=now)

        self.assertEqual(state.cycles, 1)
        self.assertEqual(state.successful_cycles, 1)
        self.assertEqual(state.executions_by_day, {"2026-01-01": 1})
        self.assertEqual(state.last_execution_at, now.isoformat())

    def test_build_executor_command_includes_execute_flags(self) -> None:
        command = build_executor_command(
            repo_root=Path("D:/repo"),
            python_exe="python",
            env_file=".env.demo",
            db="data/db.sqlite3",
            weights="USDT=0.9,BTC=0.05,ETH=0.05",
            threshold="0.08",
            min_trade_notional="10",
            max_order_notional="10",
            max_total_crypto_exposure="30",
            max_daily_loss="5",
            max_spread_bps="20",
            max_price_deviation_bps="30",
            stale_market_data_seconds=10,
            price_offset_bps="2",
            cancel_after_seconds=3.0,
            poll_timeout_seconds=20.0,
            execute=True,
            override_read_only=True,
        )

        self.assertIn("--execute", command)
        self.assertIn("--override-read-only", command)
        self.assertIn("data/db.sqlite3", command)


def _settings(
    *,
    execute: bool = False,
    max_cycles: int | None = None,
    min_seconds_between_executions: float = 0,
    max_executions_per_day: int = 8,
    max_consecutive_errors: int = 3,
) -> RunnerSettings:
    return RunnerSettings(
        duration_seconds=3600,
        interval_seconds=1,
        max_cycles=max_cycles,
        execute=execute,
        override_read_only=True,
        min_seconds_between_executions=min_seconds_between_executions,
        max_executions_per_day=max_executions_per_day,
        max_consecutive_errors=max_consecutive_errors,
    )


if __name__ == "__main__":
    unittest.main()
