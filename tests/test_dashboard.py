from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from okx_quant.dashboard.data import DashboardConfig, load_dashboard_snapshot, read_jsonl_tail
from okx_quant.storage.sqlite_store import SQLiteEventStore


class DashboardDataTests(unittest.TestCase):
    def test_read_jsonl_tail(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "runner.jsonl"
            path.write_text('{"a":1}\n{"b":2}\n', encoding="utf-8")

            rows = read_jsonl_tail(path, 1)

            self.assertEqual(rows, [{"b": 2}])

    def test_load_snapshot_with_missing_files(self) -> None:
        with TemporaryDirectory() as tmp:
            snapshot = load_dashboard_snapshot(
                DashboardConfig(
                    db_path=Path(tmp) / "missing.sqlite3",
                    log_path=Path(tmp) / "missing.jsonl",
                    summary_path=Path(tmp) / "missing.json",
                    state_path=Path(tmp) / "missing_state.json",
                )
            )

            self.assertEqual(snapshot["runner"]["health"]["status"], "no_log")
            self.assertFalse(snapshot["db"]["exists"])

    def test_load_snapshot_reads_sqlite_counts_and_reconciliation(self) -> None:
        with TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite3"
            log = Path(tmp) / "runner.jsonl"
            log.write_text(
                '{"runner_event":"cycle","finished_at":"2026-01-01T00:00:00+00:00","result":{"ok":true}}\n',
                encoding="utf-8",
            )
            with SQLiteEventStore(db) as store:
                store.initialize()
                store.insert_reconciliation_run(
                    run_id="r1",
                    started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    finished_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    status="passed",
                    summary={"issue_count": 0},
                )
                store.commit()

            snapshot = load_dashboard_snapshot(DashboardConfig(db_path=db, log_path=log))

            self.assertTrue(snapshot["db"]["exists"])
            self.assertEqual(snapshot["db"]["counts"]["reconciliation_runs"], 1)
            self.assertEqual(snapshot["db"]["reconciliation_runs"][0]["summary"], {"issue_count": 0})


if __name__ == "__main__":
    unittest.main()
