import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from purespace import create_app  # noqa: E402
from purespace.db import get_db  # noqa: E402

ADMIN_USER, ADMIN_PASS = "owner", "Sparkle-Clean-2026"


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "test.sqlite3")})
    res = app.test_cli_runner().invoke(args=["create-admin", "--username", ADMIN_USER, "--password", ADMIN_PASS])
    assert res.exit_code == 0, res.output
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def csrf(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "page has no CSRF token"
    return m.group(1)


def token_for(client, url="/contact"):
    return csrf(client.get(url).get_data(as_text=True))


@pytest.fixture
def admin(client):
    t = token_for(client, "/admin/login")
    r = client.post("/admin/login", data={"csrf_token": t, "username": ADMIN_USER, "password": ADMIN_PASS})
    assert r.status_code == 303
    return client


@pytest.fixture
def rows(app):
    def _rows(sql="SELECT * FROM enquiries", *args):
        with app.app_context():
            return [dict(r) for r in get_db().execute(sql, args).fetchall()]
    return _rows


def good_quote(**over):
    d = {"sector": "residential", "service": "regular", "bedrooms": "3", "bathrooms": "2", "frequency": "fortnightly",
         "extras": ["oven"], "postcode": "sk4 1aa", "preferred_date": "", "name": "Priya Shah",
         "email": "Priya@Example.com", "phone": "07700 900123", "contact_pref": "email",
         "message": "Two cats, please bring your own vacuum.", "consent": "yes", "website": ""}
    d.update(over)
    return d


def good_contact(**over):
    d = {"name": "Tom Hughes", "email": "tom@example.com", "phone": "", "message": "Do you clean in Wilmslow?",
         "consent": "yes", "website": ""}
    d.update(over)
    return d
