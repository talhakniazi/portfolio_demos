"""Real-browser checks with Playwright + Chromium against a live server.

Skipped automatically if Playwright or its browser is not installed.
Set SCREENSHOTS=1 to save full-page screenshots to test-results/screenshots/.
"""
import os
import re
import threading
from datetime import date, timedelta
from pathlib import Path

import pytest
from werkzeug.serving import make_server

pw = pytest.importorskip("playwright.sync_api")
from conftest import ADMIN_PASS, ADMIN_USER  # noqa: E402

PAGES = ["/", "/residential", "/commercial", "/about", "/pricing", "/quote", "/contact", "/privacy"]
SIZES = {"desktop": (1440, 900), "tablet": (820, 1180), "mobile": (390, 844)}
SHOTS = Path(__file__).resolve().parents[1] / "test-results" / "screenshots"


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    from purespace import create_app
    d = tmp_path_factory.mktemp("browser")
    app = create_app({"TESTING": False, "SECRET_KEY": "browser-test", "DATABASE": str(d / "b.sqlite3"),
                      "FORM_LIMIT": (100, 900)})
    app.test_cli_runner().invoke(args=["create-admin", "--username", ADMIN_USER, "--password", ADMIN_PASS])
    srv = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception as e:  # browser binary missing
            pytest.skip(f"Chromium not available: {e}")
        yield b
        b.close()


def watch(page):
    """Collect console errors, CSP violations, failed requests and HTTP errors."""
    problems = []
    page.on("console", lambda m: m.type == "error" and problems.append(f"console: {m.text}"))
    page.on("pageerror", lambda e: problems.append(f"js: {e}"))
    page.on("requestfailed", lambda r: problems.append(f"failed: {r.url}"))
    page.on("response", lambda r: r.status >= 400 and problems.append(f"{r.status}: {r.url}"))
    return problems


def shot(page, name):
    if os.environ.get("SCREENSHOTS"):
        SHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)


@pytest.mark.parametrize("size", SIZES)
def test_pages_render_cleanly(server, browser, size):
    w, h = SIZES[size]
    page = browser.new_page(viewport={"width": w, "height": h})
    problems = watch(page)
    for path in PAGES:
        page.goto(server + path, wait_until="networkidle")
        page.wait_for_timeout(1200)   # let the hero animation finish
        broken = page.evaluate("[...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.src)")
        assert broken == [], (path, broken)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert overflow <= 1, f"{path} scrolls sideways by {overflow}px at {size}"
        fonts = page.evaluate("[...document.fonts].filter(f => f.status === 'loaded').map(f => f.family)")
        assert any("Bricolage" in f for f in fonts) and any("Atkinson" in f for f in fonts), (path, fonts)
        shot(page, f"{size}{path.replace('/', '-') or '-home'}".replace("--", "-").rstrip("-") or size)
    assert problems == [], problems
    page.close()


def test_mobile_menu(server, browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.goto(server + "/")
    toggle = page.get_by_role("button", name=re.compile("menu", re.I))
    assert toggle.is_visible()
    assert not page.locator("#site-nav").is_visible()
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true"
    shot(page, "mobile-menu-open")
    page.keyboard.press("Escape")
    assert toggle.get_attribute("aria-expanded") == "false"
    toggle.click()
    page.locator("#site-nav").get_by_role("link", name="Office cleaning").click()
    page.wait_for_url("**/commercial")
    assert page.locator("h1").is_visible()
    page.close()


def test_nav_links_work_on_desktop(server, browser):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(server + "/")
    hrefs = page.eval_on_selector_all("#site-nav a", "els => els.map(e => e.getAttribute('href'))")
    assert len(hrefs) >= 6
    for href in hrefs:
        page.goto(server + "/")
        page.locator(f'#site-nav a[href="{href}"]').first.click()
        page.wait_for_load_state()
        assert page.url.endswith(href) and page.locator("h1").count() == 1
    page.close()


def test_quote_journey_in_browser(server, browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    problems = watch(page)
    page.goto(server + "/quote")
    # Submitting empty shows the error summary, focused, and keeps the visitor on the page
    page.get_by_role("button", name=re.compile("quote", re.I)).last.click()
    page.wait_for_load_state()
    if page.locator("#error-summary").count():  # server-side validation (browser validation may stop it first)
        assert page.locator("#error-summary").is_visible()
        assert page.evaluate("document.activeElement.id") == "error-summary", "error summary takes focus"
        shot(page, "mobile-quote-errors")
    problems.clear()   # the 422 above was expected
    page.goto(server + "/quote")
    page.locator("#sector-res").check()
    page.select_option("select[name=service]", "deep")
    page.select_option("select[name=bedrooms]", "2")
    page.select_option("select[name=bathrooms]", "1")
    est = page.locator("#est-value").inner_text()
    assert "£" in est, est
    page.locator("input[name=extras][value=oven]").check()
    assert page.locator("#est-value").inner_text() != est, "estimate updates live"
    live = page.locator("#est-value").inner_text()
    page.fill("input[name=postcode]", "m20 2ab")
    page.fill("input[name=preferred_date]", (date.today() + timedelta(days=10)).isoformat())
    page.fill("input[name=name]", "Browser Test")
    page.fill("input[name=email]", "browser@example.com")
    page.fill("input[name=phone]", "07700 900555")
    page.locator("input[name=consent]").check()
    shot(page, "mobile-quote-filled")
    page.get_by_role("button", name=re.compile("quote", re.I)).last.click()
    page.wait_for_url("**/quote/received")
    body = page.locator("main").inner_text()
    ref = re.search(r"PS-\d{6}-[A-Z2-9]{4}", body).group(0)
    assert "Browser" in body
    assert re.sub(r"\D", " ", live).split()[0] in body.replace(",", ""), "server estimate matches the live one"
    shot(page, "mobile-quote-received")
    # Business commercial: residential-only fields hide
    page.goto(server + "/quote")
    page.locator("#sector-com").check()
    assert not page.locator("select[name=bedrooms]").is_visible()
    assert page.locator("input[name=floor_area]").is_visible()
    assert problems == [], problems
    page.close()
    pytest.ref = ref


def test_admin_in_browser(server, browser):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    problems = watch(page)
    page.goto(server + "/admin/")
    assert "/admin/login" in page.url
    page.fill("#f-username", ADMIN_USER)
    page.fill("#f-password", ADMIN_PASS)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url("**/admin/")
    ref = getattr(pytest, "ref", None)
    if ref:
        assert ref in page.content()
        page.get_by_role("link", name=ref).click()
        page.select_option("#f-status", "contacted")
        page.get_by_role("button", name="Update status").click()
        assert page.get_by_text("Status changed to").is_visible()
        page.fill("#f-body", "Called, booking Thursday.")
        page.get_by_role("button", name="Save note").click()
        assert page.get_by_text("Called, booking Thursday.").is_visible()
        shot(page, "desktop-admin-detail")
    page.goto(server + "/admin/?status=all")
    shot(page, "desktop-admin-list")
    page.set_viewport_size({"width": 390, "height": 844})
    page.reload()
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1
    shot(page, "mobile-admin-list")
    page.get_by_role("button", name=re.compile("Sign out")).click()
    page.wait_for_url("**/admin/login")
    assert problems == [], problems
    page.close()
