#!/usr/bin/env python3
"""Pass 3: Scenes 6-7 (Case Study + Close) — ~72s of video"""
import os, time, json, threading, http.server, functools, glob
from playwright.sync_api import sync_playwright

WORKSPACE = "/home/democritus/.openclaw/workspace/pharmaclaw"
FRAME_DIR = os.path.join(WORKSPACE, "full_frames")
PORT = 8765
WIDTH, HEIGHT = 1280, 800
FPS = 3

existing = glob.glob(os.path.join(FRAME_DIR, "frame_*.png"))
frame_num = len(existing)
print(f"Continuing from frame {frame_num}")

with open(os.path.join(WORKSPACE, "full_demo_timing.json")) as f:
    timing = {t["name"]: t["duration"] for t in json.load(f)}
GAP = 0.6

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WORKSPACE)
httpd = http.server.HTTPServer(("", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def snap(page, delay=0.08):
    global frame_num
    time.sleep(delay)
    page.screenshot(path=os.path.join(FRAME_DIR, f"frame_{frame_num:05d}.png"), full_page=False)
    frame_num += 1

def hold(page, secs):
    for _ in range(max(1, int(secs * FPS))):
        snap(page, 1/FPS)

def scroll_to(page, sel, offset=-50, steps=18):
    y = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top+window.scrollY+({offset})")
    cur = page.evaluate("window.scrollY")
    for i in range(steps):
        t=(i+1)/steps; e=t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0,{int(cur+(y-cur)*e)})")
        snap(page, 0.03)

def scroll_down(page, px, steps=12):
    cur = page.evaluate("window.scrollY")
    for i in range(steps):
        t=(i+1)/steps; e=t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0,{int(cur+px*e)})")
        snap(page, 0.03)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
    page.goto(f"http://localhost:{PORT}", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    
    # Navigate to case study
    scroll_to(page, "#case-study", steps=5)
    time.sleep(0.5)
    
    # === SCENE 6a: Case intro (5.3s) ===
    d = timing["s6_case_intro"] + GAP
    print(f"S6a Case intro: {d:.1f}s")
    hold(page, d * 0.7)
    
    # === SCENE 6b: FAERS (12.6s) ===
    d = timing["s6_case_faers"] + GAP
    print(f"S6b FAERS: {d:.1f}s")
    scroll_down(page, 450)
    hold(page, d * 0.6)
    
    # === SCENE 6c: Compounds (17.1s) ===
    d = timing["s6_case_compounds"] + GAP
    print(f"S6c Compounds: {d:.1f}s")
    scroll_down(page, 450)
    hold(page, d * 0.4)
    scroll_down(page, 300)
    hold(page, d * 0.3)
    
    # === SCENE 6d: Comparison (15.5s) ===
    d = timing["s6_case_compare"] + GAP
    print(f"S6d Compare: {d:.1f}s")
    scroll_down(page, 450)
    hold(page, d * 0.35)
    scroll_down(page, 400)
    hold(page, d * 0.35)
    
    # === SCENE 7: Close (19.5s) ===
    d = timing["s7_close"] + GAP
    print(f"S7 Close: {d:.1f}s")
    scroll_to(page, "#pricing")
    hold(page, d * 0.4)
    scroll_to(page, "nav", offset=0, steps=25)
    hold(page, d * 0.35)
    
    browser.close()

start_frame = len(existing)
new_frames = frame_num - start_frame
print(f"\n✅ Pass 3: {new_frames} new frames ({new_frames/FPS:.1f}s), total {frame_num}")
