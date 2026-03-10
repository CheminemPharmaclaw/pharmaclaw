#!/usr/bin/env python3
"""Quick POC - just grab 5 key screenshots to prove it works."""
import os, time, threading, http.server, functools
from playwright.sync_api import sync_playwright

SITE_DIR = "/home/democritus/.openclaw/workspace/pharmaclaw"
OUTDIR = "/home/democritus/.openclaw/workspace/pharmaclaw/poc_frames"
PORT = 8765
URL = f"http://localhost:{PORT}"

os.makedirs(OUTDIR, exist_ok=True)

# In-process HTTP server
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE_DIR)
httpd = http.server.HTTPServer(("", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print(f"Server on :{PORT}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    
    print("Loading...")
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(3)  # Let Tailwind render
    
    # 1. Hero
    page.screenshot(path=f"{OUTDIR}/01_hero.png")
    print("✅ 01_hero")
    
    # 2. Pipeline
    page.evaluate("document.querySelector('#pipeline').scrollIntoView({behavior:'instant'})")
    time.sleep(1)
    page.screenshot(path=f"{OUTDIR}/02_pipeline.png")
    print("✅ 02_pipeline")
    
    # 3. Demo - click sotorasib
    page.evaluate("document.querySelector('#demo').scrollIntoView({behavior:'instant'})")
    time.sleep(1)
    page.click("text=Sotorasib")
    time.sleep(0.5)
    page.click("#runBtn")
    time.sleep(4)
    page.screenshot(path=f"{OUTDIR}/03_demo_report.png")
    print("✅ 03_demo_report")
    
    # 4. CLI
    page.evaluate("document.querySelector('#cli').scrollIntoView({behavior:'instant'})")
    time.sleep(1)
    page.screenshot(path=f"{OUTDIR}/04_cli.png")
    print("✅ 04_cli")
    
    # 5. Case Study
    page.evaluate("document.querySelector('#case-study').scrollIntoView({behavior:'instant'})")
    time.sleep(1)
    page.screenshot(path=f"{OUTDIR}/05_case_study.png")
    print("✅ 05_case_study")
    
    browser.close()

print(f"\nDone! Check {OUTDIR}/")
