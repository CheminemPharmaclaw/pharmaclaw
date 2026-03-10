#!/usr/bin/env python3
"""Pass 1: Scenes 1-3 (Hook + Pipeline + Demo) — ~120s of video"""
import os, time, json, threading, http.server, functools
from playwright.sync_api import sync_playwright

WORKSPACE = "/home/democritus/.openclaw/workspace/pharmaclaw"
FRAME_DIR = os.path.join(WORKSPACE, "full_frames")
PORT = 8765
WIDTH, HEIGHT = 1280, 800
FPS = 3

os.makedirs(FRAME_DIR, exist_ok=True)

# Load timing
with open(os.path.join(WORKSPACE, "full_demo_timing.json")) as f:
    timing = {t["name"]: t["duration"] for t in json.load(f)}
GAP = 0.6

# Server
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WORKSPACE)
httpd = http.server.HTTPServer(("", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

frame_num = 0
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
    
    # === SCENE 1: Hook (17.7s) ===
    d = timing["s1_hook"] + GAP
    print(f"S1 Hook: {d:.1f}s")
    hold(page, d)
    
    # === SCENE 2: Pipeline (46.3s) ===
    d = timing["s2_pipeline"] + GAP
    print(f"S2 Pipeline: {d:.1f}s")
    scroll_to(page, "#about")
    hold(page, d * 0.2)
    scroll_down(page, 300)
    hold(page, d * 0.15)
    scroll_to(page, "#pipeline")
    hold(page, d * 0.45)
    
    # === SCENE 3: Demo (58.4s) ===
    # 3a: Intro (8.3s)
    d = timing["s3_demo_intro"] + GAP
    print(f"S3a Demo intro: {d:.1f}s")
    scroll_to(page, "#demo")
    hold(page, d * 0.3)
    page.click("text=Sotorasib")
    hold(page, d * 0.2)
    page.click("#runBtn")
    hold(page, 0.5)
    time.sleep(3.5)
    
    # 3b: Report (17.5s)
    d = timing["s3_demo_report"] + GAP
    print(f"S3b Report: {d:.1f}s")
    hold(page, d * 0.5)
    scroll_down(page, 250)
    hold(page, d * 0.3)
    
    # 3c: FAERS (14.3s)
    d = timing["s3_demo_faers"] + GAP
    print(f"S3c FAERS: {d:.1f}s")
    scroll_down(page, 200)
    hold(page, d * 0.7)
    
    # 3d: IP (16.5s)
    d = timing["s3_demo_ip"] + GAP
    print(f"S3d IP: {d:.1f}s")
    scroll_down(page, 200)
    hold(page, d * 0.7)
    
    browser.close()

print(f"\n✅ Pass 1: {frame_num} frames ({frame_num/FPS:.1f}s)")
