"""Quote and contact forms: validation, storage, confirmation, spam and abuse protection."""
from datetime import date, timedelta

from conftest import good_contact, good_quote, token_for
from purespace import pricing


def post_quote(client, **over):
    return client.post("/quote", data={"csrf_token": token_for(client, "/quote"), **good_quote(**over)})


def test_quote_success_is_stored_and_confirmed(client, rows):
    r = post_quote(client)
    assert r.status_code == 303 and r.headers["Location"].endswith("/quote/received")
    [e] = rows()
    assert e["kind"] == "quote" and e["status"] == "new"
    assert e["email"] == "priya@example.com" and e["postcode"] == "SK4 1AA" and e["phone"] == "07700 900123"
    assert e["extras"] == "oven" and e["bedrooms"] == 3 and e["bathrooms"] == 2
    low, high = pricing.estimate("residential", "regular", 3, 2, None, "fortnightly", ["oven"])
    assert (e["estimate_low"], e["estimate_high"]) == (low, high)
    assert e["source_ip_hash"] and "127.0.0.1" not in e["source_ip_hash"]
    page = client.get("/quote/received").get_data(as_text=True)
    assert e["ref"] in page and "Priya" in page


def test_estimate_is_computed_server_side(client, rows):
    post_quote(client, estimate_low="1", estimate_high="2")
    assert rows()[0]["estimate_low"] > 1


def test_commercial_quote(client, rows):
    r = post_quote(client, sector="commercial", service="office_regular", floor_area="3,500", frequency="weekly",
                   bedrooms="", bathrooms="", extras=["oven"])
    assert r.status_code == 303
    e = rows()[0]
    assert e["floor_area"] == 3500 and e["bedrooms"] is None and e["extras"] in (None, "")


def test_quote_validation_errors_are_shown_and_nothing_saved(client, rows):
    r = post_quote(client, name="", email="not-an-email", postcode="12345", consent="", service="office_regular")
    html = r.get_data(as_text=True)
    assert r.status_code == 422
    for msg in ("Enter your name.", "Enter an email address in the format", "Enter a full UK postcode",
                "Tick the box", "Choose the type of clean"):
        assert msg in html, msg
    assert 'id="error-summary"' in html and 'aria-invalid="true"' in html
    assert 'value="Two cats' in html or "Two cats" in html, "typed answers are kept"
    assert rows() == []


def test_date_rules(client, rows):
    past = (date.today() - timedelta(days=1)).isoformat()
    assert post_quote(client, preferred_date=past).status_code == 422
    far = (date.today() + timedelta(days=400)).isoformat()
    assert post_quote(client, preferred_date=far).status_code == 422
    assert post_quote(client, preferred_date=(date.today() + timedelta(days=7)).isoformat()).status_code == 303


def test_whatsapp_needs_phone(client):
    assert post_quote(client, contact_pref="whatsapp", phone="").status_code == 422


def test_out_of_range_numbers_rejected(client):
    assert post_quote(client, bedrooms="40").status_code == 422
    assert post_quote(client, sector="commercial", service="office_regular", floor_area="5").status_code == 422


def test_contact_success_and_errors(client, rows):
    t = token_for(client)
    assert client.post("/contact", data={"csrf_token": t, **good_contact(message="hi")}).status_code == 422
    r = client.post("/contact", data={"csrf_token": t, **good_contact()})
    assert r.status_code == 303
    [e] = rows()
    assert e["kind"] == "contact" and e["message"] == "Do you clean in Wilmslow?"
    assert e["ref"] in client.get("/contact/sent").get_data(as_text=True)


def test_csrf_required(client, rows):
    r = client.post("/contact", data=good_contact())
    assert r.status_code == 400
    r = client.post("/contact", data={"csrf_token": "forged", **good_contact()})
    assert r.status_code == 400 and rows() == []


def test_honeypot_pretends_success_but_stores_nothing(client, rows):
    r = client.post("/contact", data={"csrf_token": token_for(client), **good_contact(website="http://spam.example")})
    assert r.status_code == 303 and rows() == []


def test_rate_limit(client, rows):
    t = token_for(client)
    codes = [client.post("/contact", data={"csrf_token": t, **good_contact()}).status_code for _ in range(7)]
    assert codes[:5] == [303] * 5 and codes[5] == 429
    assert len(rows()) == 5


def test_html_is_escaped_everywhere(client, admin, rows):
    evil = '<script>alert(1)</script>'
    client.post("/contact", data={"csrf_token": token_for(client), **good_contact(message=evil + " please call")})
    ref = rows()[0]["ref"]
    for url in ("/contact/sent", f"/admin/enquiry/{ref}", "/admin/"):
        assert evil not in client.get(url).get_data(as_text=True)


def test_oversized_post_rejected(client):
    r = client.post("/contact", data={"csrf_token": token_for(client), **good_contact(message="x" * 100_000)})
    assert r.status_code == 413


def test_received_page_without_submission(client):
    r = client.get("/quote/received")
    assert r.status_code == 200
