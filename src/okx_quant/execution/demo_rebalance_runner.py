"""Continuous runner helpers for OKX demo rebalance burn-in."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys


@dataclass(frozen=True)
class RunnerSettings:
    duration_seconds: float
    interval_seconds: float
    max_cycles: int | None
    execute: bool
    override_read_only: bool
    min_seconds_between_executions: float
    max_executions_per_day: int
    max_consecutive_errors: int


@dataclass
class RunnerState:
    started_at: str
    cycles: int = 0
    successful_cycles: int = 0
    failed_cycles: int = 0
    consecutive_errors: int = 0
    last_execution_at: str | None = None
    executions_by_day: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "started_at": self.started_at,
            "cycles": self.cycles,
            "successful_cycles": self.successful_cycles,
            "failed_cycles": self.failed_cycles,
            "consecutive_errors": self.consecutive_errors,
            "last_execution_at": self.last_execution_at,
            "executions_by_day": self.executions_by_day,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RunnerState":
        return cls(
            started_at=str(payload["started_at"]),
            cycles=int(payload.get("cycles", 0)),
            successful_cycles=int(payload.get("successful_cycles", 0)),
            failed_cycles=int(payload.get("failed_cycles", 0)),
            consecutive_errors=int(payload.get("consecutive_errors", 0)),
            last_execution_at=str(payload["last_execution_at"]) if payload.get("last_execution_at") else None,
            executions_by_day={str(key): int(value) for key, value in dict(payload.get("executions_by_day", {})).items()},
        )


def load_runner_state(path: Path, *, now: datetime | None = None) -> RunnerState:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("runner state must be a JSON object")
        return RunnerState.from_dict(payload)
    return RunnerState(started_at=(now or utc_now()).isoformat())


def save_runner_state(path: Path, state: RunnerState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def should_continue(
    *,
    started_monotonic: float,
    now_monotonic: float,
    state: RunnerState,
    settings: RunnerSettings,
) -> bool:
    if settings.max_cycles is not None and state.cycles >= settings.max_cycles:
        return False
    if now_monotonic - started_monotonic >= settings.duration_seconds:
        return False
    if state.consecutive_errors >= settings.max_consecutive_errors:
        return False
    return True


def should_execute_cycle(state: RunnerState, settings: RunnerSettings, now: datetime | None = None) -> bool:
    if not settings.execute:
        return False
    now = now or utc_now()
    today = utc_day(now)
    if state.executions_by_day.get(today, 0) >= settings.max_executions_per_day:
        return False
    if state.last_execution_at is None:
        return True
    last_execution_at = datetime.fromisoformat(state.last_execution_at)
    return (now - last_execution_at).total_seconds() >= settings.min_seconds_between_executions


def record_cycle_result(state: RunnerState, result: dict[str, object], *, executed_this_cycle: bool, now: datetime | None = None) -> None:
    now = now or utc_now()
    state.cycles += 1
    if bool(result.get("ok")):
        state.successful_cycles += 1
        state.consecutive_errors = 0
    else:
        state.failed_cycles += 1
        state.consecutive_errors += 1

    if executed_this_cycle and bool(result.get("ok")) and result.get("stage") == "executed":
        state.last_execution_at = now.isoformat()
        today = utc_day(now)
        state.executions_by_day[today] = state.executions_by_day.get(today, 0) + 1


def build_executor_command(
    *,
    repo_root: Path,
    python_exe: str,
    env_file: str,
    db: str,
    weights: str,
    threshold: str,
    min_trade_notional: str,
    max_order_notional: str,
    max_total_crypto_exposure: str,
    max_daily_loss: str,
    max_spread_bps: str,
    max_price_deviation_bps: str,
    stale_market_data_seconds: int,
    price_offset_bps: str,
    cancel_after_seconds: float,
    poll_timeout_seconds: float,
    execute: bool,
    override_read_only: bool,
) -> list[str]:
    command = [
        python_exe,
        str(repo_root / "scripts" / "run_demo_rebalance_executor.py"),
        "--env-file",
        env_file,
        "--db",
        db,
        "--weights",
        weights,
        "--threshold",
        threshold,
        "--min-trade-notional",
        min_trade_notional,
        "--max-order-notional",
        max_order_notional,
        "--max-total-crypto-exposure",
        max_total_crypto_exposure,
        "--max-daily-loss",
        max_daily_loss,
        "--max-spread-bps",
        max_spread_bps,
        "--max-price-deviation-bps",
        max_price_deviation_bps,
        "--stale-market-data-seconds",
        str(stale_market_data_seconds),
        "--price-offset-bps",
        price_offset_bps,
        "--cancel-after-seconds",
        str(cancel_after_seconds),
        "--poll-timeout-seconds",
        str(poll_timeout_seconds),
    ]
    if execute:
        command.append("--execute")
    if override_read_only:
        command.append("--override-read-only")
    return command


def run_executor_subprocess(command: list[str], *, repo_root: Path, timeout_seconds: float) -> dict[str, object]:
    env = dict(os.environ)
    src_path = str(repo_root / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_path
    completed = subprocess.run(
        command,
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "stage": "executor_output_parse_failed",
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-2000:],
        }
    if not isinstance(payload, dict):
        payload = {"ok": False, "stage": "executor_output_not_object", "payload": payload}
    payload["return_code"] = completed.returncode
    if completed.stderr:
        payload["stderr_tail"] = completed.stderr[-2000:]
    if completed.returncode != 0 and payload.get("ok") is True:
        payload["ok"] = False
    return payload


def append_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_summary(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def utc_day(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).date().isoformat()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_python_exe() -> str:
    return sys.executable
