"""Optional e-mail notifications (new enquiry -> business; confirmation -> customer).

Switched on by setting SMTP settings in the environment (see .env.example). If e-mail is
not configured, or sending fails, the enquiry is still saved and visible in the admin area -
a mail problem never loses an enquiry or shows the customer an error.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app, url_for

from .content import BUSINESS
from .pricing import FREQUENCY, SERVICE_LABELS

log = logging.getLogger(__name__)


def _send(msg: EmailMessage) -> bool:
    cfg = current_app.config
    if not cfg.get("SMTP_HOST"):
        return False
    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], int(cfg.get("SMTP_PORT", 587)), timeout=10) as s:
            if cfg.get("SMTP_STARTTLS", True):
                s.starttls(context=ssl.create_default_context())
            if cfg.get("SMTP_USER"):
                s.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            s.send_message(msg)
        return True
    except Exception:  # noqa: BLE001 - mail must never break a submission
        log.exception("Could not send e-mail '%s'", msg["Subject"])
        return False


def summary_lines(e: dict) -> list[str]:
    lines = [f"Reference: {e['ref']}"]
    if e.get("service"):
        lines.append(f"Service: {SERVICE_LABELS.get(e['service'], e['service'])}")
    if e.get("bedrooms") is not None:
        lines.append(f"Property: {e['bedrooms']} bedroom(s), {e['bathrooms']} bathroom(s)")
    if e.get("floor_area"):
        lines.append(f"Floor area: {e['floor_area']:,} sq ft")
    if e.get("frequency"):
        lines.append(f"How often: {FREQUENCY.get(e['frequency'], ('',))[0]}")
    if e.get("postcode"):
        lines.append(f"Postcode: {e['postcode']}")
    if e.get("estimate_low"):
        lines.append(f"Guide price: £{e['estimate_low']} to £{e['estimate_high']} per visit")
    return lines


def new_enquiry(e: dict):
    cfg = current_app.config
    to = cfg.get("NOTIFY_EMAIL")
    if to:
        m = EmailMessage()
        m["Subject"] = f"New {'quote request' if e['kind'] == 'quote' else 'message'} {e['ref']} from {e['name']}"
        m["From"] = cfg["MAIL_FROM"]; m["To"] = to; m["Reply-To"] = e["email"]
        body = summary_lines(e) + ["", f"Name: {e['name']}", f"Email: {e['email']}", f"Phone: {e.get('phone') or '-'}",
                                   "", e.get("message") or "", "", "Open in the admin area:",
                                   url_for("admin.detail", ref=e["ref"], _external=True)]
        m.set_content("\n".join(body))
        _send(m)
    if cfg.get("SEND_CUSTOMER_CONFIRMATION"):
        m = EmailMessage()
        m["Subject"] = f"We've received your {'quote request' if e['kind'] == 'quote' else 'message'} ({e['ref']})"
        m["From"] = cfg["MAIL_FROM"]; m["To"] = e["email"]
        m.set_content("\n".join([f"Hello {e['name'].split()[0]},", "",
                                 "Thank you for getting in touch. We'll reply within one working day.", ""] + summary_lines(e) +
                                ["", f"If anything is urgent, call us on {BUSINESS['phone']}.", "", BUSINESS["name"]]))
        _send(m)
