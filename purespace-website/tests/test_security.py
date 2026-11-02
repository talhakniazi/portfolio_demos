"""Headers, cookies and information exposure."""
from conftest import token_for


def test_security_headers(client):
    h = client.get("/").headers
    csp = h["Content-Security-Policy"]
    assert "script-src 'self'" in csp and "unsafe-inline" not in csp and "frame-ancestors 'none'" in csp
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in h


def test_session_cookie_flags(client):
    client.get("/contact")
    c = client.get_cookie("ps_session")
    assert c.http_only and c.same_site.lower() == "lax"


def test_admin_not_cached_or_indexed(admin):
    h = admin.get("/admin/").headers
    assert "no-store" in h["Cache-Control"] and "noindex" in h.get("X-Robots-Tag", "")


def test_no_inline_scripts_or_styles(client):
    """CSP forbids them, so any that slip in would silently break in browsers."""
    import re
    for p in ["/", "/quote", "/contact", "/admin/login"]:
        html = client.get(p).get_data(as_text=True)
        assert not re.search(r"<script(?![^>]*\bsrc=)(?![^>]*application/json)", html), p
        assert " style=" not in html and "<style" not in html, p
        assert " onclick=" not in html and " onload=" not in html, p


def test_errors_do_not_leak_details(client):
    r = client.post("/contact", data={"csrf_token": "x"})
    body = r.get_data(as_text=True)
    assert "Traceback" not in body and "werkzeug" not in body.lower()


def test_passwords_are_hashed(app):
    from purespace.db import get_db
    with app.app_context():
        h = get_db().execute("SELECT password_hash FROM admins").fetchone()[0]
    assert h.startswith("scrypt:") and "Sparkle" not in h
