from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from okx_quant.domain.market import Candle
from okx_quant.storage.sqlite_store import SQLiteEventStore


class SQLiteEventStoreTests(unittest.TestCase):
    def test_initialize_insert_raw_and_candle(self) -> None:
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "market.sqlite3"
            with SQLiteEventStore(db) as store:
                store.initialize()
                store.insert_market_raw(
                    source="unit",
                    channel="tickers",
                    inst_id="BTC-USDT",
                    payload={"arg": {"channel": "tickers", "instId": "BTC-USDT"}},
                )
                store.upsert_candle(
                    Candle(
                        inst_id="BTC-USDT",
                        bar="1H",
                        ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
                        open=Decimal("1"),
                        high=Decimal("2"),
                        low=Decimal("0.5"),
                        close=Decimal("1.5"),
                        volume=Decimal("10"),
                        volume_ccy=Decimal("15"),
                        volume_ccy_quote=Decimal("15"),
                        confirm=True,
                    ),
                    "unit",
                )
                store.commit()

                self.assertEqual(store.count("market_raw"), 1)
                self.assertEqual(store.count("candles"), 1)
                candles = store.list_candles(inst_id="BTC-USDT", bar="1H", confirmed_only=True)
                self.assertEqual(len(candles), 1)
                self.assertEqual(candles[0].close, Decimal("1.5"))
                store.insert_risk_event(
                    event_id="risk-1",
                    created_at=datetime.now(timezone.utc),
                    inst_id="BTC-USDT",
                    approved=False,
                    reasons=("read_only_mode",),
                )
                self.assertEqual(store.count("risk_events"), 1)
                store.insert_account_snapshot(
                    snapshot_id="snapshot-1",
                    taken_at=datetime.now(timezone.utc),
                    ccy="USDT",
                    equity=Decimal("100"),
                    available=Decimal("90"),
                    frozen=Decimal("10"),
                    source="unit",
                )
                store.insert_reconciliation_run(
                    run_id="reconcile-1",
                    started_at=datetime.now(timezone.utc),
                    finished_at=datetime.now(timezone.utc),
                    status="passed",
                    summary={"issue_count": 0},
                )
                self.assertEqual(store.count("account_snapshots"), 1)
                self.assertEqual(store.count("reconciliation_runs"), 1)
                self.assertEqual(store.latest_reconciliation_status(), "passed")


if __name__ == "__main__":
    unittest.main()
