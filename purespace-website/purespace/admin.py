"""Administrator area: sign in, view and manage enquiries."""
from __future__ import annotations

import csv
import io
import math
import time

from flask import Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from . import content, pricing
from .db import get_db, now
from .security import clear, client_key, login_required, password_problem, record, safe_next, too_many

bp = Blueprint("admin", __name__, url_prefix="/admin")

STATUSES = [("new", "New"), ("contacted", "Contacted"), ("quoted", "Quoted"), ("booked", "Booked"), ("lost", "Not going ahead"), ("archived", "Archived")]
STATUS_LABEL = dict(STATUSES)
PER_PAGE = 25
# A real hash of a random password: used when the username doesn't exist, so a failed login
# takes the same time whether or not the username is real (no username discovery).
_DUMMY_HASH = generate_password_hash("not-a-real-password-8f3k", method="scrypt")


@bp.app_template_filter("status_label")
def status_label(s): return STATUS_LABEL.get(s, s)


@bp.app_template_filter("service_label")
def service_label(s): return pricing.SERVICE_LABELS.get(s, s or "-")


@bp.app_template_filter("freq_label")
def freq_label(s): return pricing.FREQUENCY.get(s, (s or "-",))[0]


@bp.app_template_filter("when")
def when(iso):
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    try:
        dt = datetime.fromisoformat(iso).astimezone(ZoneInfo("Europe/London"))
    except Exception:  # noqa: BLE001
        return iso
    return f"{dt.day} {dt:%b %Y, %H:%M}"      # no %-d: it does not work on Windows


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()[:80]
        password = request.form.get("password", "")[:200]
        limit, window = current_app.config["LOGIN_LIMIT"]
        key = client_key(username)
        if too_many("login_fail", key, limit, window):
            error = "Too many failed attempts. Wait 15 minutes and try again."
            return render_template("admin/login.html", error=error, username=username), 429
        else:
            row = get_db().execute("SELECT id, password_hash FROM admins WHERE username = ?", (username,)).fetchone()
            ok = check_password_hash(row["password_hash"] if row else _DUMMY_HASH, password) and row is not None
            if ok:
                clear("login_fail", key)
                session.clear()                      # new session on sign-in (prevents session fixation)
                session.permanent = True
                session["admin_id"] = row["id"]
                session["last_seen"] = time.time()
                db = get_db(); db.execute("UPDATE admins SET last_login_at = ? WHERE id = ?", (now(), row["id"])); db.commit()
                return redirect(safe_next(request.args.get("next")) or url_for("admin.index"), 303)
            record("login_fail", key)
            error = "The username or password is not right."
        return render_template("admin/login.html", error=error, username=username), 401
    return render_template("admin/login.html", error=None, username="")


@bp.post("/logout")
def logout():
    session.clear()
    flash("You have signed out.")
    return redirect(url_for("admin.login"), 303)


def _filters():
    q = request.args.get("q", "").strip()[:80]
    status = request.args.get("status", "open")
    kind = request.args.get("kind", "")
    where, args = [], []
    if status == "open":
        where.append("status NOT IN ('lost', 'archived')")
    elif status in STATUS_LABEL:
        where.append("status = ?"); args.append(status)
    if kind in ("quote", "contact"):
        where.append("kind = ?"); args.append(kind)
    if q:
        like = f"%{q.replace('%', '').replace('_', '')}%"
        where.append("(name LIKE ? OR email LIKE ? OR postcode LIKE ? OR ref LIKE ? OR phone LIKE ?)"); args += [like] * 5
    return (" WHERE " + " AND ".join(where)) if where else "", args, dict(q=q, status=status, kind=kind)


@bp.get("/")
@login_required
def index():
    db = get_db()
    where, args, f = _filters()
    total = db.execute(f"SELECT COUNT(*) FROM enquiries{where}", args).fetchone()[0]
    pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(1, request.args.get("page", 1, type=int)), pages)
    rows = db.execute(f"SELECT * FROM enquiries{where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
                      args + [PER_PAGE, (page - 1) * PER_PAGE]).fetchall()
    counts = {r["status"]: r["n"] for r in db.execute("SELECT status, COUNT(*) n FROM enquiries GROUP BY status")}
    week = db.execute("SELECT COUNT(*) FROM enquiries WHERE created_at >= datetime('now', '-7 days')").fetchone()[0]
    return render_template("admin/index.html", rows=rows, total=total, page=page, pages=pages, f=f, counts=counts, week=week,
                           statuses=STATUSES, sample=content.SAMPLE_CONTENT)


def _get(ref):
    row = get_db().execute("SELECT * FROM enquiries WHERE ref = ?", (ref,)).fetchone()
    if not row:
        abort(404)
    return row


@bp.get("/enquiry/<ref>")
@login_required
def detail(ref):
    e = _get(ref)
    notes = get_db().execute("SELECT * FROM notes WHERE enquiry_id = ? ORDER BY created_at DESC, id DESC", (e["id"],)).fetchall()
    extras = [pricing.EXTRAS[x][0] for x in (e["extras"] or "").split(",") if x in pricing.EXTRAS]
    return render_template("admin/detail.html", e=e, notes=notes, statuses=STATUSES, extras=extras)


@bp.post("/enquiry/<ref>/status")
@login_required
def set_status(ref):
    e = _get(ref)
    new = request.form.get("status")
    if new not in STATUS_LABEL:
        abort(400, description="Unknown status.")
    if new != e["status"]:
        db = get_db()
        db.execute("UPDATE enquiries SET status = ?, updated_at = ? WHERE id = ?", (new, now(), e["id"]))
        db.execute("INSERT INTO notes (enquiry_id, created_at, author, body) VALUES (?, ?, ?, ?)",
                   (e["id"], now(), g.admin["username"], f"Status changed from {STATUS_LABEL[e['status']]} to {STATUS_LABEL[new]}."))
        db.commit()
        flash(f"Status changed to {STATUS_LABEL[new]}.")
    return redirect(url_for("admin.detail", ref=ref), 303)


@bp.post("/enquiry/<ref>/note")
@login_required
def add_note(ref):
    e = _get(ref)
    body = request.form.get("body", "").strip()[:2000]
    if not body:
        flash("Write a note before saving.", "error")
    else:
        db = get_db()
        db.execute("INSERT INTO notes (enquiry_id, created_at, author, body) VALUES (?, ?, ?, ?)", (e["id"], now(), g.admin["username"], body))
        db.execute("UPDATE enquiries SET updated_at = ? WHERE id = ?", (now(), e["id"]))
        db.commit()
        flash("Note saved.")
    return redirect(url_for("admin.detail", ref=ref) + "#notes", 303)


@bp.post("/enquiry/<ref>/delete")
@login_required
def delete(ref):
    e = _get(ref)
    if request.form.get("confirm") != ref:
        flash(f"To delete, type the reference {ref} exactly.", "error")
        return redirect(url_for("admin.detail", ref=ref) + "#delete", 303)
    db = get_db()
    db.execute("DELETE FROM enquiries WHERE id = ?", (e["id"],))   # notes go too (ON DELETE CASCADE)
    db.commit()
    flash(f"Enquiry {ref} and its notes were permanently deleted.")
    return redirect(url_for("admin.index"), 303)


def _csv_safe(v):
    """Stop spreadsheet formula injection: a value starting with = + - @ is shown as text in Excel."""
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


@bp.get("/export.csv")
@login_required
def export():
    where, args, _ = _filters()
    rows = get_db().execute(f"SELECT * FROM enquiries{where} ORDER BY created_at DESC", args).fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["ref", "kind", "status", "created_at", "name", "email", "phone", "postcode", "sector", "service", "bedrooms", "bathrooms",
            "floor_area", "frequency", "extras", "preferred_date", "estimate_low", "estimate_high", "contact_pref", "message"]
    w.writerow(cols)
    for r in rows:
        w.writerow([_csv_safe(r[c]) for c in cols])
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=purespace-enquiries.csv"})


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    error = None
    if request.method == "POST":
        row = get_db().execute("SELECT password_hash FROM admins WHERE id = ?", (g.admin["id"],)).fetchone()
        current, new, again = (request.form.get(k, "") for k in ("current", "new", "again"))
        if not check_password_hash(row["password_hash"], current):
            error = "Your current password is not right."
        elif new != again:
            error = "The two new passwords are different."
        elif password_problem(new):
            error = password_problem(new)
        else:
            db = get_db()
            db.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (generate_password_hash(new, method="scrypt"), g.admin["id"]))
            db.commit()
            flash("Password changed.")
            return redirect(url_for("admin.index"), 303)
    return render_template("admin/account.html", error=error), (422 if error else 200)
