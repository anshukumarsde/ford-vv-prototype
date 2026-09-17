"""Checks for the report and simple HTTP integration."""

import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from src import api, load_data
from src.reporting import build_report


class ReportingTests(unittest.TestCase):
    """Verify metrics, readiness rules, and the complete local HTTP flow."""

    def setUp(self):
        # Use a temporary database so tests never modify the user's vv.db file.
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.database = Path(self.folder.name) / "test.db"
        self.requirements = api.read_records("requirements.json")
        self.tests = api.read_records("tests.json")
        self.defects = api.read_records("defects.json")
        self.save()

    def save(self):
        """Write the current test records to the temporary database."""
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            load_data.create_tables(connection)
            load_data.load_snapshot(connection, self.requirements, self.tests, self.defects)

    def test_sample_metrics_and_blockers(self):
        # Confirm the fictional sample produces its documented dashboard values.
        report = build_report(self.database)
        self.assertFalse(report["ready"])
        self.assertEqual(report["metrics"]["coverage"], 66.7)
        self.assertEqual(report["metrics"]["execution"], 66.7)
        self.assertEqual(report["metrics"]["pass_rate"], 50.0)
        self.assertEqual(report["uncovered"][0]["requirement_id"], "REQ-003")

    def test_ready_state(self):
        # Cover REQ-003, pass every test, and close the defect to satisfy all gates.
        self.tests.append({"test_id": "TEST-004", "requirement_id": "REQ-003",
                           "title": "Verify rear camera", "status": "PASS"})
        for test in self.tests:
            test["status"] = "PASS"
        self.defects[0]["status"] = "CLOSED"
        self.save()
        self.assertTrue(build_report(self.database)["ready"])

    def test_http_load_report_and_dashboard(self):
        # Use an available temporary port and exercise the real HTTP handlers.
        with patch.object(api, "DATABASE_PATH", self.database), \
                api.ThreadingHTTPServer(("127.0.0.1", 0), api.SampleAPIHandler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            try:
                # Point both the loader and report endpoint at the temporary database.
                with patch.object(load_data, "DATABASE_PATH", self.database):
                    self.assertEqual(load_data.main(base_url), 0)
                report = load_data.fetch_records(base_url, "/report")
                self.assertEqual(report["metrics"]["requirements"], 3)
                with load_data.urlopen(base_url + "/dashboard", timeout=2) as response:
                    self.assertIn(b"Release overview", response.read())
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    unittest.main()
