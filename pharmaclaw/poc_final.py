#!/usr/bin/env python3
"""PharmaClaw POC - Optimized for speed. ~35s video."""
import os, time, subprocess, threading, http.server, functools
from playwright.sync_api import sync_playwright

OUTDIR = "/home/democritus/.openclaw/workspace/pharmaclaw/poc_final_frames"
FFMPEG = os.path.expanduser("~/bin/ffmpeg")
SITE_DIR = "/home/democritus/.openclaw/workspace/pharmaclaw"
PORT = 8765
WIDTH, HEIGHT = 1280, 800
FPS = 3  # output fps

# Embedded server
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE_DIR)
httpd = http.server.HTTPServer(("", PORT), handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
URL = f"http://localhost:{PORT}"

os.makedirs(OUTDIR, exist_ok=True)
# Clean old frames
for f in os.listdir(OUTDIR):
    if f.startswith("frame_"): os.remove(os.path.join(OUTDIR, f))

frame_num = 0
def snap(page, delay=0.1):
    global frame_num
    time.sleep(delay)
    page.screenshot(path=os.path.join(OUTDIR, f"frame_{frame_num:05d}.png"), full_page=False)
    frame_num += 1

def hold(page, secs=2):
    for _ in range(int(secs * FPS)):
        snap(page, 1/FPS)

def scroll_to(page, sel, offset=-50):
    y = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top + window.scrollY + ({offset})")
    cur = page.evaluate("window.scrollY")
    for i in range(15):
        t = (i+1)/15; ease = t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0, {int(cur + (y-cur)*ease)})")
        snap(page, 0.04)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
    page.goto(URL, wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    
    print("Scene 1: Hero"); hold(page, 2.5)
    print("Scene 2: Pipeline"); scroll_to(page, "#pipeline"); hold(page, 2.5)
    print("Scene 3: Demo"); scroll_to(page, "#demo"); hold(page, 1)
    page.click("text=Sotorasib"); snap(page, 0.3)
    page.click("#runBtn"); hold(page, 0.5); time.sleep(3.5); hold(page, 2.5)
    print("Scene 4: Pro"); scroll_to(page, "#pro-features"); hold(page, 2)
    print("Scene 5: CLI"); scroll_to(page, "#cli"); hold(page, 2.5)
    print("Scene 6: Case Study"); scroll_to(page, "#case-study"); hold(page, 2)
    # Scroll down through case study
    cur = page.evaluate("window.scrollY")
    for i in range(15):
        page.evaluate(f"window.scrollTo(0, {int(cur + 800*(i+1)/15)})")
        snap(page, 0.04)
    hold(page, 2)
    print("Scene 7: Pricing"); scroll_to(page, "#pricing"); hold(page, 2.5)
    
    browser.close()

print(f"✅ {frame_num} frames captured")

# Encode
OUT = "/home/democritus/.openclaw/workspace/pharmaclaw/poc_demo_final.mp4"
r = subprocess.run([FFMPEG, "-y", "-framerate", str(FPS),
    "-i", f"{OUTDIR}/frame_%05d.png",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
    "-preset", "medium", "-crf", "20", "-r", "30", OUT],
    capture_output=True, text=True)
if r.returncode == 0:
    sz = os.path.getsize(OUT)/(1024*1024)
    print(f"✅ {OUT} ({sz:.1f} MB)")
else:
    print(f"❌ {r.stderr[-200:]}")
