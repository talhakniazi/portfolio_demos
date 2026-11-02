"""A small stand-in for the marketplace's orders API, so the demo runs without real credentials.

Serves data/raw/marketplace_orders.json as paginated JSON at /api/orders?page=N&per_page=M.
The first request for page 2 deliberately fails with HTTP 503, to show the pipeline's retry logic working.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA = json.loads((Path(__file__).resolve().parents[1] / "data/raw/marketplace_orders.json").read_text())
_failed = set()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if u.path != "/api/orders":
            self.send_error(404); return
        qs = parse_qs(u.query)
        page, per = int(qs.get("page", ["1"])[0]), min(100, int(qs.get("per_page", ["25"])[0]))
        if page == 2 and 2 not in _failed:
            _failed.add(2)
            self.send_error(503, "temporarily unavailable"); return
        chunk = DATA[(page - 1) * per: page * per]
        body = json.dumps({"data": chunk, "page": page, "next_page": page + 1 if page * per < len(DATA) else None}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def start(port=8765):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    print("Mock API on http://127.0.0.1:8765/api/orders (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
