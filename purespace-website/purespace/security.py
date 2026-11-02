"""Security helpers: CSRF tokens, rate limiting, login protection, headers, references."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from functools import wraps

from flask import abort, current_app, g, redirect, request, session, url_for

from .db import get_db

# ---------------------------------------------------------------- CSRF
def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def check_csrf():
    """Reject any state-changing request without the session's token."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        sent = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
        if not sent or not hmac.compare_digest(sent, session.get("_csrf", "")):
            abort(400, description="Your session has expired or the form was submitted from another site. Please reload the page and try again.")


# ---------------------------------------------------------------- privacy-preserving client key
def client_key(extra: str = "") -> str:
    """Salted hash of the visitor's IP (+ extra). Raw IP addresses are never stored."""
    salt = current_app.config["SECRET_KEY"]
    ip = request.remote_addr or "unknown"
    return hashlib.sha256(f"{salt}|{ip}|{extra.lower()}".encode()).hexdigest()[:32]


# ---------------------------------------------------------------- rate limiting
def too_many(action: str, key: str, limit: int, window_s: int) -> bool:
    db = get_db()
    cutoff = time.time() - window_s
    db.execute("DELETE FROM events WHERE at < ?", (time.time() - 86400,))   # housekeeping
    n = db.execute("SELECT COUNT(*) FROM events WHERE action = ? AND key = ? AND at >= ?", (action, key, cutoff)).fetchone()[0]
    return n >= limit


def record(action: str, key: str):
    db = get_db()
    db.execute("INSERT INTO events (action, key, at) VALUES (?, ?, ?)", (action, key, time.time()))
    db.commit()


def clear(action: str, key: str):
    db = get_db()
    db.execute("DELETE FROM events WHERE action = ? AND key = ?", (action, key))
    db.commit()


# ---------------------------------------------------------------- admin auth
def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        admin_id = session.get("admin_id")
        last = session.get("last_seen", 0)
        if not admin_id or time.time() - last > current_app.config["ADMIN_IDLE_TIMEOUT"]:
            session.pop("admin_id", None)
            return redirect(url_for("admin.login", next=request.full_path if request.method == "GET" else None))
        row = get_db().execute("SELECT id, username FROM admins WHERE id = ?", (admin_id,)).fetchone()
        if not row:
            session.clear(); return redirect(url_for("admin.login"))
        g.admin = row
        session["last_seen"] = time.time()
        return view(*a, **kw)
    return wrapped


def password_problem(pw: str) -> str | None:
    if len(pw) < 12:
        return "Use at least 12 characters."
    if pw.lower() == pw or pw.upper() == pw or not any(c.isdigit() for c in pw):
        return "Use upper- and lower-case letters and at least one number."
    if pw.lower() in {"password1234", "purespace123", "cleaning1234", "letmein12345"}:
        return "That password is too easy to guess."
    return None


# ---------------------------------------------------------------- misc
def new_reference() -> str:
    from datetime import datetime
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O/1/I confusion when read out on the phone
    return "PS-" + datetime.now().strftime("%y%m%d") + "-" + "".join(secrets.choice(alphabet) for _ in range(4))


def safe_next(target: str | None) -> str | None:
    """Only allow redirects back into our own admin area (no open redirects)."""
    if target and target.startswith("/admin") and not target.startswith("//") and "\\" not in target:
        return target
    return None


def set_security_headers(resp):
    h = resp.headers
    h["Content-Security-Policy"] = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; font-src 'self'; "
                                    "form-action 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'")
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "strict-origin-when-cross-origin"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    if current_app.config.get("SESSION_COOKIE_SECURE"):
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.path.startswith("/admin"):
        h["Cache-Control"] = "no-store"
        h["X-Robots-Tag"] = "noindex, nofollow"
    return resp
