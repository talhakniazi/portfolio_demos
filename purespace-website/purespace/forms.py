"""Server-side validation for the quote and contact forms. Browser validation is a convenience only."""
from __future__ import annotations

import re
from datetime import date, timedelta

from . import pricing

EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
# Full UK postcode, e.g. M1 1AA, SW1A 2AA, GIR 0AA
POSTCODE_RE = re.compile(r"^(GIR ?0AA|[A-PR-UWYZ]([0-9]{1,2}|[A-HK-Y][0-9]{1,2}|[0-9][A-HJKPS-UW]|[A-HK-Y][0-9][ABEHMNPRV-Y]) ?[0-9][ABD-HJLNP-UW-Z]{2})$", re.I)
NAME_RE = re.compile(r"^[^\d<>{}\[\]\\/@#$%^*=+_|~`\"]{2,80}$")


def clean(s, maxlen):
    s = (s or "").replace("\x00", "").strip()
    s = re.sub(r"[\r\n\t]+", " ", s) if maxlen <= 200 else s
    return s[:maxlen]


def uk_phone(raw):
    digits = re.sub(r"[\s\-().]", "", raw or "")
    if digits.startswith("+44"):
        digits = "0" + digits[3:]
    elif digits.startswith("0044"):
        digits = "0" + digits[4:]
    if re.fullmatch(r"0\d{9,10}", digits):
        return digits
    return None


def format_phone(d):
    if d.startswith("07") or (d.startswith("01") and len(d) == 11 and d[2] != "1"):
        return f"{d[:5]} {d[5:]}"
    if d.startswith("02"):
        return f"{d[:3]} {d[3:7]} {d[7:]}"
    return f"{d[:4]} {d[4:7]} {d[7:]}"


def format_postcode(p):
    p = re.sub(r"\s+", "", p).upper()
    return p[:-3] + " " + p[-3:]


def _common(form, errors, data, need_phone):
    data["name"] = clean(form.get("name"), 80)
    if not data["name"]:
        errors["name"] = "Enter your name."
    elif not NAME_RE.match(data["name"]):
        errors["name"] = "Enter your name using letters only."
    data["email"] = clean(form.get("email"), 254).lower()
    if not data["email"]:
        errors["email"] = "Enter your email address so we can send your quote."
    elif not EMAIL_RE.match(data["email"]):
        errors["email"] = "Enter an email address in the format name@example.co.uk."
    raw_phone = clean(form.get("phone"), 30)
    if raw_phone:
        p = uk_phone(raw_phone)
        if not p:
            errors["phone"] = "Enter a UK phone number, like 07700 900123 or 0161 496 0000."
        else:
            data["phone"] = format_phone(p)
    elif need_phone:
        errors["phone"] = "Enter a phone number so we can call you back."
    data.setdefault("phone", None)


def validate_quote(form):
    """Return (data, errors). `errors` maps field name -> message written for the customer."""
    errors, data = {}, {}
    sector = form.get("sector")
    if sector not in ("residential", "commercial"):
        errors["sector"] = "Choose home or business."
    data["sector"] = sector
    service = form.get("service")
    allowed = pricing.RESIDENTIAL if sector == "residential" else pricing.COMMERCIAL if sector == "commercial" else {}
    if service not in allowed:
        errors["service"] = "Choose the type of clean you need."
    data["service"] = service
    data["bedrooms"] = data["bathrooms"] = data["floor_area"] = None
    if sector == "residential":
        for f, lo, hi, label in (("bedrooms", 0, 8, "bedrooms"), ("bathrooms", 1, 6, "bathrooms")):
            try:
                v = int(form.get(f, ""))
                if not lo <= v <= hi: raise ValueError
                data[f] = v
            except ValueError:
                errors[f] = f"Choose the number of {label}."
    elif sector == "commercial":
        try:
            v = int(re.sub(r"[,\s]", "", form.get("floor_area", "")))
            if not 100 <= v <= 200000: raise ValueError
            data["floor_area"] = v
        except ValueError:
            errors["floor_area"] = "Enter the floor area in square feet, between 100 and 200,000. A rough figure is fine."
    freq = form.get("frequency") or "one_off"
    if freq not in pricing.FREQUENCY:
        errors["frequency"] = "Choose how often you need cleaning."
    data["frequency"] = freq
    extras = [e for e in form.getlist("extras") if e in pricing.EXTRAS] if sector == "residential" else []
    data["extras"] = extras
    pc = clean(form.get("postcode"), 10)
    if not pc:
        errors["postcode"] = "Enter the postcode where the cleaning is needed."
    elif not POSTCODE_RE.match(re.sub(r"\s+", "", pc)):
        errors["postcode"] = "Enter a full UK postcode, like M1 1AA."
    else:
        data["postcode"] = format_postcode(pc)
    d = form.get("preferred_date", "").strip()
    data["preferred_date"] = None
    if d:
        try:
            pd = date.fromisoformat(d)
            if pd < date.today():
                errors["preferred_date"] = "Choose a date from today onwards."
            elif pd > date.today() + timedelta(days=365):
                errors["preferred_date"] = "Choose a date within the next 12 months."
            else:
                data["preferred_date"] = pd.isoformat()
        except ValueError:
            errors["preferred_date"] = "Enter a valid date."
    _common(form, errors, data, need_phone=False)
    data["contact_pref"] = form.get("contact_pref") if form.get("contact_pref") in ("email", "phone", "whatsapp") else "email"
    if data["contact_pref"] in ("phone", "whatsapp") and not data.get("phone") and "phone" not in errors:
        errors["phone"] = "Enter a phone number, or choose email as your contact preference."
    data["message"] = clean(form.get("message"), 2000) or None
    if form.get("consent") != "yes":
        errors["consent"] = "Tick the box to let us use your details to prepare your quote."
    if not errors:
        data["estimate_low"], data["estimate_high"] = pricing.estimate(sector, service, data["bedrooms"], data["bathrooms"],
                                                                       data["floor_area"], freq, extras)
    return data, errors


def validate_contact(form):
    errors, data = {}, {}
    _common(form, errors, data, need_phone=False)
    data["message"] = clean(form.get("message"), 2000)
    if len(data["message"]) < 10:
        errors["message"] = "Enter your message (at least 10 characters)."
    if form.get("consent") != "yes":
        errors["consent"] = "Tick the box to let us use your details to reply."
    return data, errors
