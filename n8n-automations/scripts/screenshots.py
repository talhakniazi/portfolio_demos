"""Screenshot each workflow in the n8n editor and its latest successful execution. Run after run_demo.py while n8n is up."""
from pathlib import Path

from playwright.sync_api import sync_playwright

N8N = "http://127.0.0.1:5678"
OUT = Path(__file__).resolve().parents[1] / "evidence" / "screenshots"
OWNER = {"email": "demo@northwind-studio.example", "firstName": "Demo", "lastName": "Owner", "password": "Demo-Owner-Passw0rd!"}
WORKFLOWS = {"leadCaptureDemo01": "01-lead-capture", "weeklyReportDemo02": "02-weekly-report", "aiTriageDemo03": "03-ai-triage"}

OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=2)
    r = ctx.request.post(N8N + "/rest/owner/setup", data=OWNER)
    print("owner setup:", r.status)
    if not r.ok:
        r = ctx.request.post(N8N + "/rest/login", data={"emailOrLdapLoginId": OWNER["email"], "password": OWNER["password"]})
        print("login:", r.status)
    page = ctx.new_page()
    for wid, name in WORKFLOWS.items():
        page.goto(f"{N8N}/workflow/{wid}", wait_until="networkidle")
        page.wait_for_timeout(3000)
        for label in ("Skip", "Got it", "Close", "Dismiss"):          # first-run tips and survey pop-ups
            btn = page.get_by_role("button", name=label)
            if btn.count():
                try:
                    btn.first.click(timeout=1000)
                except Exception:
                    pass
        page.keyboard.press("Escape")
        for sel in ('[data-test-id*="checklist"] button[aria-label*="lose"]', 'button[aria-label="Close"]', '.el-popover button:has(svg)'):
            try:
                loc = page.locator(sel)
                if loc.count():
                    loc.first.click(timeout=800)
            except Exception:
                pass
        page.mouse.click(800, 650)                                     # click empty canvas to dismiss pop-overs
        page.keyboard.press("Shift+1")                                 # zoom to fit
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / f"{name}-canvas.png"))
        ex = ctx.request.get(f"{N8N}/rest/executions?filter=" + '{"workflowId":"%s","status":["success"]}' % wid)
        try:
            items = ex.json()["data"]["results"]
        except Exception:
            items = []
        if items:
            first = min(items, key=lambda e: int(e["id"]))              # the first test case: hot lead / urgent ticket
            page.goto(f"{N8N}/workflow/{wid}/executions/{first['id']}", wait_until="networkidle")
            page.wait_for_timeout(4000)
            page.screenshot(path=str(OUT / f"{name}-execution.png"))
        print(name, "canvas ok,", len(items), "successful executions")
    b.close()
