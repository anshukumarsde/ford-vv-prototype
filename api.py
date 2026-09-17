"""Serve fictional V&V records over HTTP for local learning."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from load_data import read_records


ROUTES = {
    "/requirements": "requirements.json",
    "/tests": "tests.json",
    "/defects": "defects.json",
}


class SampleAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        filename = ROUTES.get(urlsplit(self.path).path)
        if filename is None:
            self.send_error(404, "Unknown endpoint")
            return
        try:
            body = json.dumps(read_records(filename)).encode("utf-8")
        except (OSError, ValueError):
            self.send_error(500, "Could not read sample data")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8000), SampleAPIHandler) as server:
        print("Sample API running at http://127.0.0.1:8000. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
