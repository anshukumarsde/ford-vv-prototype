"""Serve fictional V&V records over HTTP for local learning."""

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from src.reporting import build_report

# Resolve files from this script's location, so commands work consistently
# when they are launched from the project root.
SOURCE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SOURCE_DIR.parent
DATABASE_PATH = PROJECT_DIR / "vv.db"


def read_records(filename):
    """Read one fictional source-system JSON file into Python objects."""
    with (PROJECT_DIR / "data" / filename).open(encoding="utf-8") as source:
        return json.load(source)


ROUTES = {
    # Each route represents one external engineering tool in this demo.
    "/jama/requirements": "requirements.json",
    "/testrail/tests": "tests.json",
    "/jira/defects": "defects.json",
}


class SampleAPIHandler(BaseHTTPRequestHandler):
    """Route browser and loader GET requests to the correct response."""

    def send_body(self, body, content_type):
        """Send a successful HTTP response with its content type and size."""
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        """Handle dashboard, report, and fictional tool API requests."""
        parsed = urlsplit(self.path)

        # The root URL and /dashboard both return the same HTML page.
        if parsed.path in ("/", "/dashboard"):
            self.send_body((SOURCE_DIR / "dashboard.html").read_bytes(), "text/html; charset=utf-8")
            return
        # The dashboard calls this route to obtain calculated metrics as JSON.
        if parsed.path == "/report":
            try:
                release = parse_qs(parsed.query).get("release", [None])[0]
                report = build_report(DATABASE_PATH, release)
            except (sqlite3.Error, OSError):
                self.send_error(503, "Reporting database unavailable. Run load_data.py first.")
                return
            self.send_body(json.dumps(report).encode("utf-8"), "application/json")
            return
        # All remaining known routes return one of the sample JSON datasets.
        filename = ROUTES.get(parsed.path)
        if filename is None:
            self.send_error(404, "Unknown endpoint")
            return
        try:
            body = json.dumps(read_records(filename)).encode("utf-8")
        except (OSError, ValueError):
            self.send_error(500, "Could not read sample data")
            return
        self.send_body(body, "application/json; charset=utf-8")


if __name__ == "__main__":
    # A threaded server prevents one browser connection from blocking others.
    with ThreadingHTTPServer(("127.0.0.1", 8000), SampleAPIHandler) as server:
        print("Sample API running at http://127.0.0.1:8000. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
