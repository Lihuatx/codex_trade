"""SQLite event store for local development and smoke tests."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from typing import Any

from okx_quant.domain.enums import OrderStatus
from okx_quant.domain.market import Candle
from okx_quant.domain.models import Fill, Order


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def utc_iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()


@dataclass
class SQLiteEventStore(AbstractContextManager["SQLiteEventStore"]):
    db_path: Path

    def __post_init__(self) -> None:
        self.db_path = Path(self.db_path)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if self._conn is not None:
            if exc_type is None:
                self._conn.commit()
            self._conn.close()
            self._conn = None

    def initialize(self) -> None:
        self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.conn.commit()

    def insert_market_raw(
        self,
        *,
        source: str,
        channel: str,
        inst_id: str | None,
        payload: dict[str, Any],
        received_at: datetime | None = None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO market_raw (source, channel, inst_id, received_at, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source,
                channel,
                inst_id,
                utc_iso(received_at),
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        return int(cur.lastrowid)

    def upsert_candle(self, candle: Candle, source: str) -> None:
        self.conn.execute(
            """
            INSERT INTO candles (
                inst_id, bar, ts, open, high, low, close, volume, confirm, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(inst_id, bar, ts) DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume,
                confirm = excluded.confirm,
                source = excluded.source
            """,
            (
                candle.inst_id,
                candle.bar,
                candle.ts.isoformat(),
                str(candle.open),
                str(candle.high),
                str(candle.low),
                str(candle.close),
                str(candle.volume),
                int(candle.confirm),
                source,
            ),
        )

    def insert_order(self, order: Order) -> None:
        self.conn.execute(
            """
            INSERT INTO orders (
                client_order_id, exchange_order_id, inst_id, side, order_type,
                price, size, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.client_order_id,
                order.exchange_order_id,
                order.inst_id,
                order.side.value,
                order.order_type.value,
                str(order.price) if order.price is not None else None,
                str(order.size),
                order.status.value,
                order.created_at.isoformat(),
                order.updated_at.isoformat(),
            ),
        )

    def update_order_status(
        self,
        *,
        client_order_id: str,
        status: OrderStatus,
        updated_at: datetime,
        exchange_order_id: str | None = None,
    ) -> None:
        self.conn.execute(
            """
            UPDATE orders
            SET status = ?,
                updated_at = ?,
                exchange_order_id = COALESCE(?, exchange_order_id)
            WHERE client_order_id = ?
            """,
            (status.value, updated_at.isoformat(), exchange_order_id, client_order_id),
        )

    def get_order_status(self, client_order_id: str) -> OrderStatus:
        row = self.conn.execute(
            """
            SELECT status
            FROM orders
            WHERE client_order_id = ?
            """,
            (client_order_id,),
        ).fetchone()
        if row is None:
            raise KeyError(client_order_id)
        return OrderStatus(row["status"])

    def insert_fill(self, fill: Fill) -> None:
        self.conn.execute(
            """
            INSERT INTO fills (
                fill_id, client_order_id, exchange_order_id, inst_id, side,
                price, size, fee, fee_ccy, filled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fill.fill_id,
                fill.client_order_id,
                fill.exchange_order_id,
                fill.inst_id,
                fill.side.value,
                str(fill.price),
                str(fill.size),
                str(fill.fee),
                fill.fee_ccy,
                fill.filled_at.isoformat(),
            ),
        )

    def insert_risk_event(
        self,
        *,
        event_id: str,
        created_at: datetime,
        inst_id: str,
        approved: bool,
        reasons: tuple[str, ...],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO risk_events (event_id, created_at, inst_id, decision, reasons)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_id,
                created_at.isoformat(),
                inst_id,
                "approved" if approved else "rejected",
                json.dumps(list(reasons), ensure_ascii=False, separators=(",", ":")),
            ),
        )

    def insert_account_snapshot(
        self,
        *,
        snapshot_id: str,
        taken_at: datetime,
        ccy: str,
        equity: Decimal,
        available: Decimal,
        frozen: Decimal,
        source: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO account_snapshots (
                snapshot_id, taken_at, ccy, equity, available, frozen, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                taken_at.isoformat(),
                ccy,
                str(equity),
                str(available),
                str(frozen),
                source,
            ),
        )

    def list_order_statuses(self) -> dict[str, OrderStatus]:
        rows = self.conn.execute(
            """
            SELECT client_order_id, status
            FROM orders
            """
        ).fetchall()
        return {row["client_order_id"]: OrderStatus(row["status"]) for row in rows}

    def insert_reconciliation_run(
        self,
        *,
        run_id: str,
        started_at: datetime,
        finished_at: datetime | None,
        status: str,
        summary: dict[str, Any],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO reconciliation_runs (run_id, started_at, finished_at, status, summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                started_at.isoformat(),
                finished_at.isoformat() if finished_at else None,
                status,
                json.dumps(summary, ensure_ascii=False, separators=(",", ":")),
            ),
        )

    def latest_reconciliation_status(self) -> str | None:
        row = self.conn.execute(
            """
            SELECT status
            FROM reconciliation_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()
        return str(row["status"]) if row is not None else None

    def commit(self) -> None:
        self.conn.commit()

    def count(self, table: str) -> int:
        if table not in {
            "market_raw",
            "candles",
            "trade_intents",
            "orders",
            "fills",
            "account_snapshots",
            "risk_events",
            "reconciliation_runs",
        }:
            raise ValueError(f"Unsupported table: {table}")
        row = self.conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
        return int(row["n"])

    def recent_market_raw(self, limit: int = 5) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT id, source, channel, inst_id, received_at, payload_json
                FROM market_raw
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        )

    def list_candles(self, *, inst_id: str, bar: str, confirmed_only: bool = True) -> list[Candle]:
        rows = self.conn.execute(
            """
            SELECT inst_id, bar, ts, open, high, low, close, volume, confirm
            FROM candles
            WHERE inst_id = ? AND bar = ? AND (? = 0 OR confirm = 1)
            ORDER BY ts ASC
            """,
            (inst_id, bar, int(confirmed_only)),
        ).fetchall()
        return [
            Candle(
                inst_id=row["inst_id"],
                bar=row["bar"],
                ts=datetime.fromisoformat(row["ts"]),
                open=Decimal(row["open"]),
                high=Decimal(row["high"]),
                low=Decimal(row["low"]),
                close=Decimal(row["close"]),
                volume=Decimal(row["volume"]),
                volume_ccy=Decimal(row["volume"]),
                volume_ccy_quote=None,
                confirm=bool(row["confirm"]),
            )
            for row in rows
        ]
