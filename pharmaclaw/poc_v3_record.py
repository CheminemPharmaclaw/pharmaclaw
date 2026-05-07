#!/usr/bin/env python3
"""Record video frames timed exactly to pre-generated narration."""
import os, time, subprocess, json, threading, http.server, functools
from playwright.sync_api import sync_playwright

FFPROBE = os.path.expanduser("~/bin/ffprobe")
WORKSPACE = "/home/democritus/.openclaw/workspace/pharmaclaw"
FRAME_DIR = os.path.join(WORKSPACE, "poc_v3_frames")
AUDIO_DIR = os.path.join(WORKSPACE, "poc_v2_audio")  # reuse existing TTS
PORT = 8765
WIDTH, HEIGHT = 1280, 800
VID_FPS = 4

os.makedirs(FRAME_DIR, exist_ok=True)
for f in os.listdir(FRAME_DIR):
    os.remove(os.path.join(FRAME_DIR, f))

# Get audio durations
def get_dur(name):
    r = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0",
                       os.path.join(AUDIO_DIR, f"{name}.mp3")], capture_output=True, text=True)
    return float(r.stdout.strip())

durations = {n: get_dur(n) for n in ["s1_hook","s2_pipeline","s3_demo","s4_pro","s5_cli","s6_case","s7_close"]}
GAP = 0.8  # silence between segments

print("Scene durations (from TTS):")
for k, v in durations.items():
    print(f"  {k}: {v:.1f}s (+{GAP}s gap)")
print(f"  Total: {sum(durations.values()) + GAP*6:.1f}s")

# Server
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=WORKSPACE)
httpd = http.server.HTTPServer(("", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()

frame_num = 0
def snap(page, delay=0.1):
    global frame_num
    time.sleep(delay)
    page.screenshot(path=os.path.join(FRAME_DIR, f"frame_{frame_num:05d}.png"), full_page=False)
    frame_num += 1

def hold(page, secs):
    n = max(1, int(secs * VID_FPS))
    for _ in range(n):
        snap(page, 1/VID_FPS)

def scroll_to(page, sel, offset=-50):
    y = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top + window.scrollY + ({offset})")
    cur = page.evaluate("window.scrollY")
    for i in range(20):
        t = (i+1)/20; ease = t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0, {int(cur + (y-cur)*ease)})")
        snap(page, 0.03)

def scroll_down(page, px):
    cur = page.evaluate("window.scrollY")
    for i in range(12):
        t = (i+1)/12; ease = t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0, {int(cur + px*ease)})")
        snap(page, 0.03)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
    page.goto(f"http://localhost:{PORT}", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    
    # S1: Hero
    d = durations["s1_hook"] + GAP
    print(f"\nS1 Hero: {d:.1f}s ({int(d*VID_FPS)} frames)")
    hold(page, d)
    
    # S2: Pipeline  
    d = durations["s2_pipeline"] + GAP
    print(f"S2 Pipeline: {d:.1f}s")
    scroll_to(page, "#about")
    hold(page, d * 0.35)
    scroll_to(page, "#pipeline")
    hold(page, d * 0.45)
    
    # S3: Demo
    d = durations["s3_demo"] + GAP
    print(f"S3 Demo: {d:.1f}s")
    scroll_to(page, "#demo")
    hold(page, 1.5)
    page.click("text=Sotorasib")
    hold(page, 0.8)
    page.click("#runBtn")
    hold(page, 0.8)
    time.sleep(3.5)  # JS animation
    remaining = d - 5.0  # subtract scroll + click time
    hold(page, remaining * 0.4)
    scroll_down(page, 300)
    hold(page, remaining * 0.4)
    
    # S4: Pro Features
    d = durations["s4_pro"] + GAP
    print(f"S4 Pro: {d:.1f}s")
    scroll_to(page, "#pro-features")
    hold(page, d * 0.4)
    scroll_down(page, 500)
    hold(page, d * 0.35)
    
    # S5: CLI
    d = durations["s5_cli"] + GAP
    print(f"S5 CLI: {d:.1f}s")
    scroll_to(page, "#cli")
    hold(page, d * 0.45)
    scroll_down(page, 400)
    hold(page, d * 0.3)
    
    # S6: Case Study
    d = durations["s6_case"] + GAP
    print(f"S6 Case: {d:.1f}s")
    scroll_to(page, "#case-study")
    hold(page, d * 0.25)
    scroll_down(page, 500)
    hold(page, d * 0.25)
    scroll_down(page, 500)
    hold(page, d * 0.2)
    
    # S7: Close  
    d = durations["s7_close"] + GAP
    print(f"S7 Close: {d:.1f}s")
    scroll_to(page, "#pricing")
    hold(page, d * 0.45)
    scroll_to(page, "nav", offset=0)
    hold(page, d * 0.25)
    
    browser.close()

print(f"\n✅ {frame_num} frames → {frame_num/VID_FPS:.1f}s at {VID_FPS}fps")
