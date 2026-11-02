"""PureSpace Cleaning Services - website application."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, render_template, request


def _env_bool(name, default=False):
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


def _secret_key(instance: Path) -> str:
    """SECRET_KEY from the environment, else a random key stored in instance/ (created once, never committed)."""
    if os.environ.get("PURESPACE_SECRET_KEY"):
        return os.environ["PURESPACE_SECRET_KEY"]
    f = instance / "secret_key"
    if not f.exists():
        instance.mkdir(parents=True, exist_ok=True)
        f.write_text(secrets.token_hex(32))
        try:
            os.chmod(f, 0o600)
        except OSError:
            pass
    return f.read_text().strip()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    instance = Path(app.instance_path)
    app.config.update(
        SECRET_KEY=_secret_key(instance) if not (test_config or {}).get("SECRET_KEY") else test_config["SECRET_KEY"],
        DATABASE=os.environ.get("PURESPACE_DATABASE", str(instance / "purespace.sqlite3")),
        MAX_CONTENT_LENGTH=64 * 1024,                     # forms only; nothing large is ever uploaded
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_env_bool("PURESPACE_SECURE_COOKIES", False),   # set true when served over HTTPS
        SESSION_COOKIE_NAME="ps_session",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        ADMIN_IDLE_TIMEOUT=int(os.environ.get("PURESPACE_ADMIN_IDLE_MINUTES", "60")) * 60,
        FORM_LIMIT=(5, 15 * 60),                          # max 5 form submissions per visitor per 15 minutes
        LOGIN_LIMIT=(5, 15 * 60),                         # max 5 failed logins per IP+username per 15 minutes
        SMTP_HOST=os.environ.get("PURESPACE_SMTP_HOST") or None,
        SMTP_PORT=os.environ.get("PURESPACE_SMTP_PORT", "587"),
        SMTP_USER=os.environ.get("PURESPACE_SMTP_USER") or None,
        SMTP_PASSWORD=os.environ.get("PURESPACE_SMTP_PASSWORD") or None,
        SMTP_STARTTLS=_env_bool("PURESPACE_SMTP_TLS", True),
        MAIL_FROM=os.environ.get("PURESPACE_MAIL_FROM") or "website@purespace-cleaning.example",
        NOTIFY_EMAIL=os.environ.get("PURESPACE_NOTIFY_EMAIL") or None,
        SEND_CUSTOMER_CONFIRMATION=_env_bool("PURESPACE_SEND_CUSTOMER_CONFIRMATION", False),
        TRUST_PROXY=_env_bool("PURESPACE_TRUST_PROXY", False),
    )
    if test_config:
        app.config.update(test_config)

    if app.config["TRUST_PROXY"]:   # behind nginx / a hosting proxy: use the real client IP for rate limiting
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    from . import db, security
    db.init_app(app)
    with app.app_context():
        db.init_db()               # creates tables if missing; never deletes data

    from .public import bp as public_bp
    from .admin import bp as admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    app.before_request(security.check_csrf)
    app.after_request(security.set_security_headers)

    @app.context_processor
    def inject():
        from .content import BUSINESS, CLOTHS
        return {"csrf_token": security.csrf_token, "business": BUSINESS, "cloths": CLOTHS}

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", code=400, title="Please try again", message=e.description), 400

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, title="We can't find that page",
                               message="The page may have moved. Use the menu, or go to the home page."), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("error.html", code=413, title="That was too much text",
                               message="Please shorten your message and try again."), 413

    @app.errorhandler(429)
    def too_many(e):
        return render_template("error.html", code=429, title="Too many attempts",
                               message=e.description), 429

    @app.errorhandler(500)
    def server_error(e):
        logging.getLogger(__name__).exception("Server error on %s", request.path)
        return render_template("error.html", code=500, title="Something went wrong on our side",
                               message="Your details have not been lost if you saw a confirmation. Otherwise please try again, "
                                       "or call us."), 500

    return app
