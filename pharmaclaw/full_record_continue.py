#!/usr/bin/env python3
"""Continue recording from scene 5 (CLI) onwards. Picks up frame numbering."""
import os, time, json, threading, http.server, functools, glob
from playwright.sync_api import sync_playwright

WORKSPACE = "/home/democritus/.openclaw/workspace/pharmaclaw"
FRAME_DIR = os.path.join(WORKSPACE, "full_frames")
PORT = 8765
WIDTH, HEIGHT = 1280, 800
FPS = 2
DELAY = 0.12

existing = sorted(glob.glob(os.path.join(FRAME_DIR, "frame_*.png")))
frame_num = len(existing)
print(f"Continuing from frame {frame_num} ({frame_num/FPS:.0f}s)")

with open(os.path.join(WORKSPACE, "full_demo_timing.json")) as f:
    timing = {t["name"]: t["duration"] for t in json.load(f)}
GAP = 0.6

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WORKSPACE)
httpd = http.server.HTTPServer(("", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def snap(page):
    global frame_num
    page.screenshot(path=os.path.join(FRAME_DIR, f"frame_{frame_num:05d}.png"), full_page=False)
    frame_num += 1
    time.sleep(DELAY)

def hold(page, secs):
    for _ in range(max(1, int(secs * FPS))):
        snap(page)

def scroll_to(page, sel, offset=-50):
    y = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top+window.scrollY+({offset})")
    cur = page.evaluate("window.scrollY")
    for i in range(12):
        t=(i+1)/12; e=t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0,{int(cur+(y-cur)*e)})")
        snap(page)

def scroll_down(page, px):
    cur = page.evaluate("window.scrollY")
    for i in range(8):
        t=(i+1)/8; e=t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0,{int(cur+px*e)})")
        snap(page)

t0 = time.time()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
    page.goto(f"http://localhost:{PORT}", wait_until="domcontentloaded", timeout=30000)
    time.sleep(1.5)
    
    # Jump to CLI section
    page.evaluate("document.querySelector('#cli').scrollIntoView()")
    time.sleep(0.5)
    
    # S5a: CLI (15.3s)
    d = timing["s5_cli"] + GAP
    print(f"S5a CLI: {d:.1f}s")
    hold(page, d * 0.55)
    scroll_down(page, 300)
    hold(page, d * 0.15)
    
    # S5b: LangGraph (32.9s)
    d = timing["s5_langgraph"] + GAP
    print(f"S5b LangGraph: {d:.1f}s")
    scroll_down(page, 400)
    hold(page, d * 0.2)
    scroll_down(page, 400)
    hold(page, d * 0.2)
    scroll_down(page, 350)
    hold(page, d * 0.2)
    scroll_down(page, 300)
    hold(page, d * 0.15)
    
    # S6a: Case intro (5.3s)
    d = timing["s6_case_intro"] + GAP
    print(f"S6a Case intro: {d:.1f}s")
    scroll_to(page, "#case-study")
    hold(page, d * 0.5)
    
    # S6b: FAERS (12.6s)
    d = timing["s6_case_faers"] + GAP
    print(f"S6b FAERS: {d:.1f}s")
    scroll_down(page, 450)
    hold(page, d * 0.5)
    
    # S6c: Compounds (17.1s)
    d = timing["s6_case_compounds"] + GAP
    print(f"S6c Compounds: {d:.1f}s")
    scroll_down(page, 450)
    hold(page, d * 0.3)
    scroll_down(page, 300)
    hold(page, d * 0.25)
    
    # S6d: Compare (15.5s)
    d = timing["s6_case_compare"] + GAP
    print(f"S6d Compare: {d:.1f}s")
    scroll_down(page, 450)
    hold(page, d * 0.3)
    scroll_down(page, 350)
    hold(page, d * 0.25)
    
    # S7: Close (19.5s)
    d = timing["s7_close"] + GAP
    print(f"S7 Close: {d:.1f}s")
    scroll_to(page, "#pricing")
    hold(page, d * 0.35)
    scroll_to(page, "nav", offset=0)
    hold(page, d * 0.35)
    
    browser.close()

elapsed = time.time() - t0
new = frame_num - len(existing)
print(f"\n✅ Added {new} frames in {elapsed:.0f}s")
print(f"   Total: {frame_num} frames → {frame_num/FPS:.0f}s at {FPS}fps")
