"""Serve fictional V&V records over HTTP for local learning."""

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from load_data import DATABASE_PATH, PROJECT_DIR, read_records
from reporting import build_report
from vendor_mocks import mock_response


ROUTES = {
    "/requirements": "requirements.json",
    "/tests": "tests.json",
    "/defects": "defects.json",
}


class SampleAPIHandler(BaseHTTPRequestHandler):
    def send_body(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path in ("/", "/dashboard"):
            self.send_body((PROJECT_DIR / "dashboard.html").read_bytes(), "text/html; charset=utf-8")
            return
        if parsed.path == "/report":
            try:
                release = parse_qs(parsed.query).get("release", [None])[0]
                report = build_report(DATABASE_PATH, release)
            except (sqlite3.Error, OSError):
                self.send_error(503, "Reporting database unavailable. Run load_data.py first.")
                return
            self.send_body(json.dumps(report).encode("utf-8"), "application/json")
            return
        if parsed.path.startswith("/mock/"):
            try:
                result = mock_response(self.path, read_records)
            except (ValueError, KeyError, TypeError):
                self.send_error(400, "Invalid page parameters or unsupported mock data")
                return
            except OSError:
                self.send_error(500, "Could not read mock data")
                return
            if result is None:
                self.send_error(404, "Unknown mock endpoint")
            else:
                self.send_body(json.dumps(result).encode("utf-8"), "application/json")
            return
        filename = ROUTES.get(urlsplit(self.path).path)
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
    with ThreadingHTTPServer(("127.0.0.1", 8000), SampleAPIHandler) as server:
        print("Sample API running at http://127.0.0.1:8000. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
