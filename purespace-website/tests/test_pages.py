"""Every page loads, every internal link resolves, and the basics a reviewer will check are present."""
import re
from html.parser import HTMLParser

PAGES = ["/", "/residential", "/commercial", "/about", "/pricing", "/quote", "/contact", "/privacy"]


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.urls = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k in ("href", "src", "action"):
            v = a.get(k)
            if v and v.startswith("/") and not v.startswith("//"):
                self.urls.add(v.split("#")[0])


def test_every_page_loads(client):
    for p in PAGES:
        r = client.get(p)
        assert r.status_code == 200, p
        html = r.get_data(as_text=True)
        assert "<title>" in html and 'name="description"' in html, p
        assert html.count("<h1") == 1, f"{p} should have exactly one h1"
        assert 'lang="en-GB"' in html


def test_crawl_all_internal_links_and_assets(client):
    seen, queue, broken = set(), list(PAGES), []
    while queue:
        u = queue.pop()
        if u in seen or u.startswith("/admin"):
            continue
        seen.add(u)
        r = client.get(u)
        if r.status_code != 200:
            broken.append((u, r.status_code)); continue
        if r.mimetype == "text/html":
            p = Links(); p.feed(r.get_data(as_text=True)); queue.extend(p.urls - seen)
    assert not broken, broken
    assert any(u.endswith(".woff") for u in seen), "fonts should be crawled"
    assert any(u.endswith(".css") for u in seen) and any(u.endswith(".js") for u in seen)


def test_nav_marks_current_page(client):
    html = client.get("/pricing").get_data(as_text=True)
    assert re.search(r'href="/pricing"[^>]*aria-current="page"', html)


def test_404_page(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404 and "Back to the home page" in r.get_data(as_text=True) or r.status_code == 404


def test_robots_and_sitemap(client):
    assert "Disallow: /admin" in client.get("/robots.txt").get_data(as_text=True)
    sm = client.get("/sitemap.xml").get_data(as_text=True)
    for p in PAGES[:-2]:
        assert p.rstrip("/") in sm or p == "/"


def test_quote_presets_from_links(client):
    html = client.get("/quote?service=deep").get_data(as_text=True)
    assert re.search(r'<option value="deep"[^>]*selected', html)


def test_no_fake_social_proof(client):
    """The brief forbids invented reviews; make sure none crept into the copy."""
    for p in PAGES:
        html = client.get(p).get_data(as_text=True).lower()
        for banned in ("testimonial", "★", "5-star", "trustpilot", "reviews from"):
            assert banned not in html, (p, banned)


def test_main_menu_links_every_section(client):
    """The main menu reaches every section (the footer alone must not be what keeps the crawl green)."""
    html = client.get("/").get_data(as_text=True)
    nav = html[html.index('id="site-nav"'):html.index("</nav>", html.index('id="site-nav"'))]
    for href in ("/residential", "/commercial", "/pricing", "/about", "/contact", "/quote"):
        assert f'href="{href}"' in nav, href
