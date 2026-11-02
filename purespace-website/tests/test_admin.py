"""Admin area: access control, login protection, and managing enquiries."""
import csv
import io

from conftest import ADMIN_PASS, ADMIN_USER, good_contact, good_quote, token_for

PROTECTED = ["/admin/", "/admin/account", "/admin/export.csv"]


def submit(client, n=1, **over):
    for _ in range(n):
        client.post("/quote", data={"csrf_token": token_for(client, "/quote"), **good_quote(**over)})


def test_admin_pages_need_login(client):
    for u in PROTECTED:
        r = client.get(u)
        assert r.status_code == 302 and "/admin/login" in r.headers["Location"], u
    assert client.post("/admin/enquiry/PS-X/status", data={"csrf_token": token_for(client)}).status_code == 302


def test_wrong_password(client):
    t = token_for(client, "/admin/login")
    r = client.post("/admin/login", data={"csrf_token": t, "username": ADMIN_USER, "password": "wrong"})
    assert r.status_code == 401 and "not right" in r.get_data(as_text=True)
    r = client.post("/admin/login", data={"csrf_token": t, "username": "nobody", "password": "wrong"})
    assert r.status_code == 401, "unknown users get the same response"


def test_login_lockout(client):
    t = token_for(client, "/admin/login")
    codes = [client.post("/admin/login", data={"csrf_token": t, "username": ADMIN_USER, "password": "x"}).status_code
             for _ in range(6)]
    assert codes[-1] == 429
    r = client.post("/admin/login", data={"csrf_token": t, "username": ADMIN_USER, "password": ADMIN_PASS})
    assert r.status_code == 429, "even the right password waits during lockout"


def test_open_redirect_blocked(client):
    t = token_for(client, "/admin/login")
    r = client.post("/admin/login?next=https://evil.example/", data={"csrf_token": t, "username": ADMIN_USER, "password": ADMIN_PASS})
    assert r.headers["Location"].endswith("/admin/")


def test_login_changes_session(client):
    client.get("/contact")
    before = client.get_cookie("ps_session").value
    t = token_for(client, "/admin/login")
    client.post("/admin/login", data={"csrf_token": t, "username": ADMIN_USER, "password": ADMIN_PASS})
    assert client.get_cookie("ps_session").value != before


def test_dashboard_lists_and_filters(admin, rows):
    submit(admin, 2)
    admin.post("/contact", data={"csrf_token": token_for(admin), **good_contact(name="Zara Ahmed")})
    html = admin.get("/admin/").get_data(as_text=True)
    assert html.count('badge--new') >= 3 and "Zara Ahmed" in html and "Priya Shah" in html
    assert "Zara Ahmed" not in admin.get("/admin/?kind=quote").get_data(as_text=True)
    assert "Priya" not in admin.get("/admin/?q=zara").get_data(as_text=True)
    ref = rows()[0]["ref"]
    assert ref in admin.get(f"/admin/?q={ref}").get_data(as_text=True)


def test_status_notes_delete(admin, rows):
    submit(admin)
    ref = rows()[0]["ref"]
    t = token_for(admin, f"/admin/enquiry/{ref}")
    assert admin.post(f"/admin/enquiry/{ref}/status", data={"csrf_token": t, "status": "booked"}).status_code == 303
    assert admin.post(f"/admin/enquiry/{ref}/status", data={"csrf_token": t, "status": "hacked"}).status_code in (303, 400)
    assert rows()[0]["status"] == "booked"
    admin.post(f"/admin/enquiry/{ref}/note", data={"csrf_token": t, "body": "Booked for Tuesday 9am"})
    notes = rows("SELECT body FROM notes")
    assert any("Tuesday" in n["body"] for n in notes) and any("status" in n["body"].lower() for n in notes)
    admin.post(f"/admin/enquiry/{ref}/delete", data={"csrf_token": t, "confirm": "wrong"})
    assert len(rows()) == 1
    admin.post(f"/admin/enquiry/{ref}/delete", data={"csrf_token": t, "confirm": ref})
    assert rows() == [] and rows("SELECT * FROM notes") == []


def test_admin_actions_need_csrf(admin, rows):
    submit(admin)
    ref = rows()[0]["ref"]
    assert admin.post(f"/admin/enquiry/{ref}/status", data={"status": "lost"}).status_code == 400
    assert admin.post(f"/admin/enquiry/{ref}/delete", data={"confirm": ref}).status_code == 400
    assert len(rows()) == 1 and rows()[0]["status"] == "new"


def test_csv_export_escapes_formulas(admin):
    admin.post("/contact", data={"csrf_token": token_for(admin), **good_contact(message="=HYPERLINK(\"http://x\") call me")})
    r = admin.get("/admin/export.csv?status=all")
    assert r.mimetype == "text/csv"
    data = list(csv.DictReader(io.StringIO(r.get_data(as_text=True).lstrip("﻿"))))
    assert data[0]["message"].startswith("'=")


def test_change_password(admin):
    t = token_for(admin, "/admin/account")
    r = admin.post("/admin/account", data={"csrf_token": t, "current": ADMIN_PASS, "new": "short", "again": "short"})
    assert r.status_code in (200, 422)
    new = "Another-Good-Pass-9"
    admin.post("/admin/account", data={"csrf_token": t, "current": ADMIN_PASS, "new": new, "again": new})
    admin.post("/admin/logout", data={"csrf_token": token_for(admin, "/admin/")})
    t = token_for(admin, "/admin/login")
    assert admin.post("/admin/login", data={"csrf_token": t, "username": ADMIN_USER, "password": new}).status_code == 303


def test_logout_requires_post_and_ends_session(admin):
    assert admin.get("/admin/logout").status_code == 405
    admin.post("/admin/logout", data={"csrf_token": token_for(admin, "/admin/")})
    assert admin.get("/admin/").status_code == 302


def test_weak_admin_password_refused(app):
    res = app.test_cli_runner().invoke(args=["create-admin", "--username", "x", "--password", "password"])
    assert res.exit_code != 0


def test_purge_old_keeps_bookings_and_recent(app, client, rows):
    from purespace.db import get_db
    submit(client, 3)
    with app.app_context():
        db = get_db()
        ids = [r["id"] for r in db.execute("SELECT id FROM enquiries ORDER BY id")]
        db.execute("UPDATE enquiries SET created_at = '2020-01-01T09:00:00+00:00' WHERE id IN (?, ?)", ids[:2])
        db.execute("UPDATE enquiries SET status = 'booked' WHERE id = ?", (ids[0],))
        db.commit()
    res = app.test_cli_runner().invoke(args=["purge-old", "--yes"])
    assert "Deleted 1" in res.output
    left = {r["id"] for r in rows()}
    assert left == {ids[0], ids[2]}, "old booking and recent enquiry are kept"
