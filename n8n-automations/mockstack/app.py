"""Mock business stack for the n8n demos: CRM, shop orders API, helpdesk, team chat webhook and email API.

Stands in for HubSpot/Pipedrive, Shopify, Zendesk, Slack and Postmark so the workflows run end to end without
anyone's real accounts. Everything received is kept in memory and visible at GET /_inspect.
    python mockstack/app.py    (listens on 127.0.0.1:4000)
"""
from __future__ import annotations

import itertools
import os
import random
from datetime import date, datetime, timedelta, timezone

from flask import Flask, abort, jsonify, request

app = Flask(__name__)
API_KEY = os.environ.get("MOCK_API_KEY", "demo-key")
ids = itertools.count(101)
STATE = {"contacts": [], "tickets": [], "chat": [], "emails": []}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.before_request
def auth():
    if request.path.startswith("/_"):
        return
    if request.headers.get("Authorization") != f"Bearer {API_KEY}":
        return jsonify(error="unauthorised"), 401


# ---------------------------------------------------------------- CRM
@app.get("/crm/contacts")
def find_contact():
    email = (request.args.get("email") or "").lower()
    return jsonify(results=[c for c in STATE["contacts"] if c["email"] == email])


@app.post("/crm/contacts")
def create_contact():
    b = request.get_json(force=True)
    if not b.get("email"):
        return jsonify(error="email required"), 422
    c = {"id": next(ids), "created_at": now(), "notes": [], **b}
    STATE["contacts"].append(c)
    return jsonify(c), 201


@app.patch("/crm/contacts/<int:cid>")
def update_contact(cid):
    c = next((c for c in STATE["contacts"] if c["id"] == cid), None) or abort(404)
    b = request.get_json(force=True)
    note = b.pop("note", None)
    c.update(b)
    if note:
        c["notes"].append({"at": now(), "text": note})
    return jsonify(c)


# ---------------------------------------------------------------- shop orders (deterministic sample data)
@app.get("/shop/orders")
def orders():
    since = date.fromisoformat(request.args.get("since", (date.today() - timedelta(days=14)).isoformat()))
    rng = random.Random(7)
    products = [("Starter plan", 29), ("Team plan", 79), ("Onboarding session", 150), ("Extra seat", 9)]
    out = []
    for d in range(28):
        day = date.today() - timedelta(days=d)
        for n in range(rng.randint(2, 7)):
            name, price = rng.choice(products)
            qty = rng.choice([1, 1, 1, 2, 3])
            if day >= since:
                out.append({"id": f"ORD-{day:%m%d}-{n}", "date": day.isoformat(), "product": name, "qty": qty,
                            "total": price * qty, "status": "refunded" if rng.random() < 0.05 else "paid"})
    return jsonify(orders=out, count=len(out))


# ---------------------------------------------------------------- helpdesk
@app.post("/helpdesk/tickets")
def ticket():
    b = request.get_json(force=True)
    t = {"id": next(ids), "created_at": now(), "status": "open", **b}
    STATE["tickets"].append(t)
    return jsonify(t), 201


# ---------------------------------------------------------------- team chat (Slack-style incoming webhook)
@app.post("/chat/webhook")
def chat():
    b = request.get_json(force=True)
    STATE["chat"].append({"at": now(), **b})
    return "ok"


# ---------------------------------------------------------------- transactional email (Postmark-style)
@app.post("/email/send")
def email():
    b = request.get_json(force=True)
    missing = [k for k in ("From", "To", "Subject") if not b.get(k)]
    if missing:
        return jsonify(ErrorCode=300, Message=f"missing {missing}"), 422
    m = {"MessageID": f"msg-{next(ids)}", "SubmittedAt": now(), **b}
    STATE["emails"].append(m)
    return jsonify(m)


@app.get("/_inspect")
def inspect():
    return jsonify(STATE)


@app.post("/_reset")
def reset():
    for v in STATE.values():
        v.clear()
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "4000")))
