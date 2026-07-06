"""Read local runner JSONL logs and SQLite state for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any


@dataclass(frozen=True)
class DashboardConfig:
    db_path: Path
    log_path: Path
    summary_path: Path | None = None
    state_path: Path | None = None
    expected_interval_seconds: float = 900.0
    max_events: int = 100


def load_dashboard_snapshot(config: DashboardConfig) -> dict[str, object]:
    events = read_jsonl_tail(config.log_path, config.max_events)
    summary = read_json_file(config.summary_path) if config.summary_path else None
    state = read_json_file(config.state_path) if config.state_path else None
    db = read_sqlite_snapshot(config.db_path)
    latest_event = events[-1] if events else None
    return {
        "generated_at": utc_now_iso(),
        "paths": {
            "db": str(config.db_path),
            "log": str(config.log_path),
            "summary": str(config.summary_path) if config.summary_path else None,
            "state": str(config.state_path) if config.state_path else None,
        },
        "runner": {
            "health": runner_health(latest_event, config.expected_interval_seconds),
            "latest_event": latest_event,
            "summary": summary,
            "state": state,
        },
        "events": events,
        "db": db,
    }


def read_jsonl_tail(path: Path, limit: int) -> list[dict[str, object]]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    if not path.exists():
        return []
    rows = path.read_text(encoding="utf-8").splitlines()[-limit:]
    events: list[dict[str, object]] = []
    for line in rows:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            events.append({"parse_error": True, "raw": line[-500:]})
            continue
        events.append(payload if isinstance(payload, dict) else {"payload": payload})
    return events


def read_json_file(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"payload": payload}
    return payload


def runner_health(latest_event: dict[str, object] | None, expected_interval_seconds: float) -> dict[str, object]:
    if latest_event is None:
        return {"status": "no_log", "age_seconds": None}
    timestamp = str(latest_event.get("finished_at") or latest_event.get("started_at") or "")
    age_seconds = age_from_iso(timestamp)
    if age_seconds is None:
        return {"status": "unknown", "age_seconds": None}
    stale_after = max(expected_interval_seconds * 2, expected_interval_seconds + 60)
    status = "ok" if age_seconds <= stale_after else "stale"
    return {"status": status, "age_seconds": age_seconds, "stale_after_seconds": stale_after}


def read_sqlite_snapshot(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "exists": False,
            "counts": {},
            "orders": [],
            "risk_events": [],
            "reconciliation_runs": [],
        }
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        return {
            "exists": True,
            "counts": _counts(conn),
            "orders": _query_rows(
                conn,
                """
                SELECT client_order_id, exchange_order_id, inst_id, side, order_type, price, size, status, created_at, updated_at
                FROM orders
                ORDER BY updated_at DESC
                LIMIT 50
                """,
            ),
            "risk_events": _query_rows(
                conn,
                """
                SELECT event_id, created_at, inst_id, decision, reasons
                FROM risk_events
                ORDER BY created_at DESC
                LIMIT 50
                """,
            ),
            "reconciliation_runs": _query_rows(
                conn,
                """
                SELECT run_id, started_at, finished_at, status, summary
                FROM reconciliation_runs
                ORDER BY started_at DESC
                LIMIT 50
                """,
            ),
            "fills": _query_rows(
                conn,
                """
                SELECT fill_id, client_order_id, exchange_order_id, inst_id, side, price, size, fee, fee_ccy, filled_at
                FROM fills
                ORDER BY filled_at DESC
                LIMIT 50
                """,
            ),
        }
    finally:
        conn.close()


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    result: dict[str, int] = {}
    for table in ("orders", "fills", "risk_events", "reconciliation_runs", "account_snapshots"):
        try:
            row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
        except sqlite3.OperationalError:
            result[table] = 0
            continue
        result[table] = int(row["n"]) if row is not None else 0
    return result


def _query_rows(conn: sqlite3.Connection, sql: str) -> list[dict[str, object]]:
    try:
        rows = conn.execute(sql).fetchall()
    except sqlite3.OperationalError:
        return []
    return [decode_json_fields(dict(row)) for row in rows]


def decode_json_fields(row: dict[str, object]) -> dict[str, object]:
    for key in ("summary", "reasons"):
        value = row.get(key)
        if isinstance(value, str):
            try:
                row[key] = json.loads(value)
            except json.JSONDecodeError:
                pass
    return row


def age_from_iso(raw: str) -> float | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
