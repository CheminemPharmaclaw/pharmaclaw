#!/usr/bin/env python3
"""
Full demo recording — ALL scenes in one pass.
Key optimization: Use 2fps capture with minimal delay. 
273s of video = 546 frames. At 0.15s/frame = 82s recording time.
"""
import os, time, json, threading, http.server, functools
from playwright.sync_api import sync_playwright

WORKSPACE = "/home/democritus/.openclaw/workspace/pharmaclaw"
FRAME_DIR = os.path.join(WORKSPACE, "full_frames")
PORT = 8765
WIDTH, HEIGHT = 1280, 800
FPS = 2  # Lower capture FPS = faster recording

os.makedirs(FRAME_DIR, exist_ok=True)
for f in os.listdir(FRAME_DIR):
    if f.startswith("frame_"):
        os.remove(os.path.join(FRAME_DIR, f))

with open(os.path.join(WORKSPACE, "full_demo_timing.json")) as f:
    timing = {t["name"]: t["duration"] for t in json.load(f)}
GAP = 0.6

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WORKSPACE)
httpd = http.server.HTTPServer(("", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

frame_num = 0
DELAY = 0.12  # Fast capture

def snap(page):
    global frame_num
    page.screenshot(path=os.path.join(FRAME_DIR, f"frame_{frame_num:05d}.png"), full_page=False)
    frame_num += 1
    time.sleep(DELAY)

def hold(page, secs):
    """Hold for N seconds worth of frames."""
    n = max(1, int(secs * FPS))
    for _ in range(n):
        snap(page)

def scroll_to(page, sel, offset=-50):
    y = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top+window.scrollY+({offset})")
    cur = page.evaluate("window.scrollY")
    steps = 12
    for i in range(steps):
        t=(i+1)/steps; e=t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0,{int(cur+(y-cur)*e)})")
        snap(page)

def scroll_down(page, px):
    cur = page.evaluate("window.scrollY")
    steps = 8
    for i in range(steps):
        t=(i+1)/steps; e=t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0,{int(cur+px*e)})")
        snap(page)

print("Recording full demo...")
t0 = time.time()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
    page.goto(f"http://localhost:{PORT}", wait_until="domcontentloaded", timeout=30000)
    time.sleep(1.5)
    
    # S1: Hook (17.7s + gap)
    print("S1 Hook")
    hold(page, timing["s1_hook"] + GAP)
    
    # S2: Pipeline (46.3s)
    print("S2 Pipeline")
    d = timing["s2_pipeline"] + GAP
    scroll_to(page, "#about")
    hold(page, d * 0.15)
    scroll_down(page, 300)
    hold(page, d * 0.1)
    scroll_to(page, "#pipeline")
    hold(page, d * 0.5)
    
    # S3a: Demo intro (8.3s)
    print("S3 Demo")
    scroll_to(page, "#demo")
    hold(page, 2)
    page.click("text=Sotorasib")
    hold(page, 1)
    page.click("#runBtn")
    hold(page, 1)
    time.sleep(3.5)
    
    # S3b: Report (17.5s)
    d = timing["s3_demo_report"] + GAP
    hold(page, d * 0.45)
    scroll_down(page, 250)
    hold(page, d * 0.3)
    
    # S3c: FAERS (14.3s)
    d = timing["s3_demo_faers"] + GAP
    scroll_down(page, 200)
    hold(page, d * 0.6)
    
    # S3d: IP (16.5s)
    d = timing["s3_demo_ip"] + GAP
    scroll_down(page, 200)
    hold(page, d * 0.6)
    
    # S4: Pro Features (26.7s)
    print("S4 Pro")
    d = timing["s4_pro"] + GAP
    scroll_to(page, "#pro-features")
    hold(page, d * 0.2)
    scroll_down(page, 400)
    hold(page, d * 0.2)
    scroll_down(page, 350)
    hold(page, d * 0.2)
    scroll_down(page, 300)
    hold(page, d * 0.15)
    
    # S5a: CLI (15.3s)
    print("S5 CLI")
    d = timing["s5_cli"] + GAP
    scroll_to(page, "#cli")
    hold(page, d * 0.55)
    scroll_down(page, 300)
    hold(page, d * 0.15)
    
    # S5b: LangGraph (32.9s)
    d = timing["s5_langgraph"] + GAP
    scroll_down(page, 400)
    hold(page, d * 0.2)
    scroll_down(page, 400)
    hold(page, d * 0.2)
    scroll_down(page, 350)
    hold(page, d * 0.2)
    scroll_down(page, 300)
    hold(page, d * 0.15)
    
    # S6a: Case intro (5.3s)
    print("S6 Case Study")
    d = timing["s6_case_intro"] + GAP
    scroll_to(page, "#case-study")
    hold(page, d * 0.5)
    
    # S6b: FAERS (12.6s)
    d = timing["s6_case_faers"] + GAP
    scroll_down(page, 450)
    hold(page, d * 0.5)
    
    # S6c: Compounds (17.1s)
    d = timing["s6_case_compounds"] + GAP
    scroll_down(page, 450)
    hold(page, d * 0.3)
    scroll_down(page, 300)
    hold(page, d * 0.25)
    
    # S6d: Compare (15.5s)
    d = timing["s6_case_compare"] + GAP
    scroll_down(page, 450)
    hold(page, d * 0.3)
    scroll_down(page, 350)
    hold(page, d * 0.25)
    
    # S7: Close (19.5s)
    print("S7 Close")
    d = timing["s7_close"] + GAP
    scroll_to(page, "#pricing")
    hold(page, d * 0.35)
    scroll_to(page, "nav", offset=0)
    hold(page, d * 0.35)
    
    browser.close()

elapsed = time.time() - t0
print(f"\n✅ {frame_num} frames in {elapsed:.0f}s (video: {frame_num/FPS:.0f}s at {FPS}fps)")
