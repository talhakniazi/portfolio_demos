"""Public website: pages, quote request and contact forms."""
from __future__ import annotations

import json

from flask import Blueprint, Response, abort, current_app, redirect, render_template, request, session, url_for

from . import content, notify, pricing
from .db import get_db, now
from .forms import validate_contact, validate_quote
from .security import client_key, new_reference, record, too_many

bp = Blueprint("public", __name__)

PAGES = {  # endpoint -> (template, title, description)
    "home": ("home.html", None, "Home and office cleaning across Greater Manchester. Vetted, insured cleaners. Get a guide price online in a minute."),
    "residential": ("residential.html", "Home cleaning", "Regular, deep, end-of-tenancy and after-builders cleaning for homes in Greater Manchester."),
    "commercial": ("commercial.html", "Office and commercial cleaning", "Daily and weekly cleaning for offices, studios and communal areas, out of hours if you need it."),
    "about": ("about.html", "About us", "Who we are and how we work."),
    "pricing": ("pricing.html", "Prices", "Guide prices for home and office cleaning, and how we work out your quote."),
    "privacy": ("privacy.html", "Privacy notice", "How we use the details you send us."),
}


def _page(endpoint):
    tpl, title, desc = PAGES[endpoint]
    return render_template(tpl, title=title, description=desc, pricing=pricing, content=content)


@bp.get("/")
def home(): return _page("home")


@bp.get("/residential")
def residential(): return _page("residential")


@bp.get("/commercial")
def commercial(): return _page("commercial")


@bp.get("/about")
def about(): return _page("about")


@bp.get("/pricing")
def prices(): return render_template("pricing.html", title="Prices", description=PAGES["pricing"][2], pricing=pricing, content=content)


@bp.get("/privacy")
def privacy(): return _page("privacy")


def _insert(kind, d, ref):
    db = get_db()
    t = now()
    db.execute("""INSERT INTO enquiries (ref, kind, status, created_at, updated_at, name, email, phone, postcode, sector, service,
                  bedrooms, bathrooms, floor_area, frequency, extras, preferred_date, message, estimate_low, estimate_high,
                  contact_pref, source_ip_hash) VALUES (?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
               (ref, kind, t, t, d["name"], d["email"], d.get("phone"), d.get("postcode"), d.get("sector"), d.get("service"),
                d.get("bedrooms"), d.get("bathrooms"), d.get("floor_area"), d.get("frequency"), ",".join(d.get("extras") or []),
                d.get("preferred_date"), d.get("message"), d.get("estimate_low"), d.get("estimate_high"), d.get("contact_pref"),
                client_key()))
    db.commit()


def _guarded_submit(kind, validate, template, done_endpoint, **ctx):
    """Shared POST handling: spam trap, rate limit, validation, save, notify, redirect."""
    form = request.form
    if form.get("website"):                # honeypot: humans never see this field; bots fill it in
        session["last_enquiry"] = {"ref": None, "kind": kind}
        return redirect(url_for(done_endpoint), 303)
    limit, window = current_app.config["FORM_LIMIT"]
    key = client_key()
    if too_many("form", key, limit, window):
        abort(429, description=f"You've sent several requests in a short time. Please wait a few minutes, or call us on {content.BUSINESS['phone']}.")
    data, errors = validate(form)
    if errors:
        return render_template(template, errors=errors, form=form, **ctx), 422
    record("form", key)
    ref = new_reference()
    _insert(kind, data, ref)
    notify.new_enquiry({**data, "ref": ref, "kind": kind})
    session["last_enquiry"] = {"ref": ref, "kind": kind, "name": data["name"].split()[0], "email": data["email"],
                               "contact_pref": data.get("contact_pref", "email"),
                               "summary": notify.summary_lines({**data, "ref": ref})[1:]}
    return redirect(url_for(done_endpoint), 303)


def _quote_ctx():
    return dict(title="Get a quote", description="Tell us about the clean you need and see a guide price straight away.",
                pricing=pricing, pricing_json=json.dumps(pricing.as_json()), content=content)


@bp.route("/quote", methods=["GET", "POST"])
def quote():
    ctx = _quote_ctx()
    if request.method == "POST":
        return _guarded_submit("quote", validate_quote, "quote.html", "public.quote_received", **ctx)
    preset = {k: request.args.get(k) for k in ("sector", "service") if request.args.get(k)}
    return render_template("quote.html", errors={}, form=preset, **ctx)


@bp.get("/quote/received")
def quote_received():
    return render_template("received.html", title="Quote request received", description="", e=session.get("last_enquiry"))


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    ctx = dict(title="Contact us", description="Call, WhatsApp or send us a message.", content=content)
    if request.method == "POST":
        return _guarded_submit("contact", validate_contact, "contact.html", "public.contact_sent", **ctx)
    return render_template("contact.html", errors={}, form={}, **ctx)


@bp.get("/contact/sent")
def contact_sent():
    return render_template("received.html", title="Message sent", description="", e=session.get("last_enquiry"))


@bp.get("/robots.txt")
def robots():
    return Response(f"User-agent: *\nDisallow: /admin\nSitemap: {url_for('public.sitemap', _external=True)}\n", mimetype="text/plain")


@bp.get("/sitemap.xml")
def sitemap():
    urls = [url_for(f"public.{e}", _external=True) for e in ("home", "residential", "commercial", "prices", "about", "quote", "contact", "privacy")]
    body = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + \
           "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>"
    return Response(body, mimetype="application/xml")
