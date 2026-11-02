"""Start the chatbot server, ask real questions through the widget, and screenshot desktop and mobile."""
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
srv = subprocess.Popen([sys.executable, "-m", "chatbot.web"], cwd=ROOT, env={**os.environ, "PORT": "5050"})
try:
    for _ in range(60):
        try:
            if requests.get("http://127.0.0.1:5050/healthz", timeout=2).ok:
                break
        except requests.RequestException:
            time.sleep(1)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, vp, qs in [("desktop", {"width": 1366, "height": 860}, ["Can I return a helmet I've worn?", "How much is a full service?", "Do you sell skateboards?"]),
                             ("mobile", {"width": 390, "height": 844}, ["How long is the warranty on a carbon frame?", "and aluminium?"])]:
            page = b.new_page(viewport=vp, device_scale_factor=2)
            page.goto("http://127.0.0.1:5050/")
            page.get_by_role("button", name="Ask a question").click()
            for q in qs:
                page.get_by_label("Your question").fill(q)
                page.get_by_role("button", name="Send").click()
                page.locator(".kc-typing").wait_for(state="detached", timeout=180000)
                page.wait_for_timeout(500)
            page.screenshot(path=str(OUT / f"chat-{name}.png"))
            print("saved", name)
        b.close()
finally:
    srv.terminate()
