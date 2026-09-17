import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import api
import load_data
from integrations import fetch_vendor_data
from reporting import build_report


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.database = Path(self.folder.name) / "test.db"
        self.requirements = load_data.read_records("requirements.json")
        self.tests = load_data.read_records("tests.json")
        self.defects = load_data.read_records("defects.json")
        self.save()

    def save(self):
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            load_data.create_tables(connection)
            load_data.load_snapshot(connection, self.requirements, self.tests, self.defects)

    def test_sample_metrics_and_blockers(self):
        report = build_report(self.database)
        self.assertFalse(report["ready"])
        self.assertEqual(report["metrics"]["coverage"], 66.7)
        self.assertEqual(report["metrics"]["execution"], 66.7)
        self.assertEqual(report["metrics"]["pass_rate"], 50.0)
        self.assertEqual(report["uncovered"][0]["requirement_id"], "REQ-003")
        self.assertEqual(len(report["traceability"]), 4)

    def make_ready(self):
        self.tests.append({"test_id": "TEST-004", "requirement_id": "REQ-003",
                           "title": "Camera check", "status": "PASS"})
        for test in self.tests:
            test["status"] = "PASS"
        self.defects[0]["status"] = "CLOSED"
        self.save()

    def test_ready_requires_all_gates(self):
        self.make_ready()
        self.assertTrue(build_report(self.database)["ready"])
        for status in ("FAIL", "BLOCKED", "NOT_RUN"):
            self.tests[0]["status"] = status
            self.save()
            self.assertFalse(build_report(self.database)["ready"])

    def test_open_and_in_progress_high_defects_block(self):
        self.make_ready()
        for status in ("OPEN", "IN_PROGRESS"):
            self.defects[0]["status"] = status
            self.save()
            self.assertFalse(build_report(self.database)["ready"])

    def test_empty_and_unknown_scope_not_ready(self):
        self.assertFalse(build_report(self.database, "UNKNOWN")["ready"])
        self.requirements, self.tests, self.defects = [], [], []
        self.save()
        report = build_report(self.database)
        self.assertFalse(report["ready"])
        self.assertIsNone(report["metrics"]["coverage"])
        self.assertIsNone(report["metrics"]["pass_rate"])

    def test_filter_and_multiple_defects_do_not_inflate_metrics(self):
        self.requirements[2]["release"] = "DEMO-2"
        self.defects.append(dict(self.defects[0], defect_id="BUG-002"))
        self.save()
        report = build_report(self.database, "DEMO-1")
        self.assertEqual(report["metrics"]["requirements"], 2)
        self.assertEqual(report["metrics"]["tests"], 3)
        self.assertEqual(report["metrics"]["coverage"], 100)
        self.assertEqual(report["metrics"]["open_defects"], 2)
        self.assertEqual(build_report(self.database, "DEMO-2")["metrics"]["tests"], 0)

    def test_unknown_severity_blocks_but_load_age_is_informational(self):
        self.make_ready()
        self.defects[0]["severity"] = "UNCLASSIFIED"
        self.save()
        self.assertFalse(build_report(self.database)["ready"])
        self.defects[0]["severity"] = "HIGH"
        self.save()
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute("UPDATE sync_metadata SET loaded_at='2000-01-01T00:00:00Z'")
            connection.commit()
        report = build_report(self.database)
        self.assertTrue(report["ready"])
        self.assertEqual(report["loaded_at"], "2000-01-01T00:00:00Z")

    def test_http_vendor_pagination_and_dashboard(self):
        # Multiple defects force Jira pagination too.
        self.defects += [dict(self.defects[0], defect_id=f"BUG-{i:03d}") for i in (2, 3)]
        sources = dict(zip(("requirements.json", "tests.json", "defects.json"),
                           (self.requirements, self.tests, self.defects)))
        with patch.object(api, "read_records", side_effect=sources.__getitem__), \
                patch.object(api, "DATABASE_PATH", self.database), \
                api.ThreadingHTTPServer(("127.0.0.1", 0), api.SampleAPIHandler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            try:
                records = fetch_vendor_data(base_url, load_data.fetch_records)
                self.assertEqual(records, (self.requirements, self.tests, self.defects))
                with patch.object(load_data, "DATABASE_PATH", self.database):
                    self.assertEqual(load_data.main(base_url, vendor_mocks=True), 0)
                report = load_data.fetch_records(base_url, "/report?release=DEMO-1")
                self.assertEqual(report["metrics"]["open_defects"], 3)
                with load_data.urlopen(base_url + "/dashboard", timeout=2) as response:
                    self.assertIn(b"Release overview", response.read())
            finally:
                server.shutdown()
                thread.join()

    def test_unknown_vendor_status_rejected_before_database_open(self):
        self.tests[0]["status"] = "RETEST"
        # Model a TestRail response with an unsupported status ID.
        responses = [
            {"data": [], "meta": {"pageInfo": {"startIndex": 0, "resultCount": 0, "totalResults": 0}}},
            {"tests": [{"custom_source_id": "T1", "refs": "R1", "title": "Test", "status_id": 99}]},
        ]
        with patch.object(load_data, "fetch_records", side_effect=responses), \
                patch.object(load_data.sqlite3, "connect") as connect:
            self.assertEqual(load_data.main("http://localhost", vendor_mocks=True), 1)
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
