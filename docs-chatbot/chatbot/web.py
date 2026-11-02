"""Web server: a demo shop page with the chat widget, and the JSON chat API the widget calls.

    python -m chatbot.web            then open http://127.0.0.1:5050
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

from .assistant import Assistant
from .ingest import ingest, load, save

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def create_app(kb_dir: Path = ROOT / "kb_source", data_dir: Path = ROOT / "data") -> Flask:
    app = Flask(__name__, static_folder=None)
    index_file = data_dir / "chunks.json"
    if not index_file.exists():
        save(ingest(kb_dir), index_file)
    bot = Assistant(load(index_file), log_dir=data_dir / "logs")
    hits: dict[str, deque] = defaultdict(deque)
    LIMIT, WINDOW = int(os.environ.get("CHATBOT_RATE_LIMIT", "20")), 60

    @app.after_request
    def headers(r):
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if r.mimetype == "text/html":
            r.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        return r

    @app.get("/")
    def home():
        return send_from_directory(WEB, "index.html")

    @app.get("/static/<path:name>")
    def static(name):
        return send_from_directory(WEB / "static", name)

    @app.post("/api/chat")
    def chat():
        ip = request.remote_addr or "?"
        q = hits[ip]
        now = time.time()
        while q and q[0] < now - WINDOW:
            q.popleft()
        if len(q) >= LIMIT:
            return jsonify(error="You're sending messages very quickly. Please wait a minute."), 429
        q.append(now)
        body = request.get_json(silent=True) or {}
        msg = body.get("message")
        if not isinstance(msg, str) or not msg.strip():
            abort(400)
        if len(msg) > 500:
            return jsonify(error="Please keep questions under 500 characters."), 400
        history = [m for m in body.get("history", []) if isinstance(m, dict) and isinstance(m.get("content"), str)][-6:]
        history = [{"role": m.get("role"), "content": m["content"][:1000]} for m in history]
        return jsonify(bot.answer(msg, history))

    @app.get("/healthz")
    def health():
        return {"ok": True, "chunks": len(bot.index.chunks)}

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5050")))
