#!/usr/bin/env python3
"""PharmaClaw YouTube Demo - Proof of Concept Recording
Captures sequential screenshots of pharmaclaw.com demo flow,
then stitches into video with ffmpeg.
"""
import os, time, subprocess, threading, http.server, functools
from playwright.sync_api import sync_playwright

OUTDIR = "/home/democritus/.openclaw/workspace/pharmaclaw/poc_frames"
FFMPEG = os.path.expanduser("~/bin/ffmpeg")
SITE_DIR = "/home/democritus/.openclaw/workspace/pharmaclaw"
PORT = 8765
URL = f"http://localhost:{PORT}"

# Start HTTP server in-process
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE_DIR)
httpd = http.server.HTTPServer(("", PORT), handler)
server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
server_thread.start()
print(f"HTTP server on port {PORT}")
WIDTH, HEIGHT = 1280, 800
FPS = 2  # frames per second for smooth-ish scrolling

os.makedirs(OUTDIR, exist_ok=True)

frame_num = 0

def snap(page, label="", delay=0.3):
    """Take a screenshot and increment frame counter."""
    global frame_num
    time.sleep(delay)
    path = os.path.join(OUTDIR, f"frame_{frame_num:05d}.png")
    page.screenshot(path=path, full_page=False)
    print(f"  [{frame_num:04d}] {label}")
    frame_num += 1
    return path

def hold(page, seconds=2, label="hold"):
    """Hold on current view for N seconds (at FPS rate)."""
    frames = int(seconds * FPS)
    for i in range(frames):
        snap(page, f"{label} ({i+1}/{frames})", delay=1/FPS)

def smooth_scroll(page, target_y, steps=20, label="scroll"):
    """Smoothly scroll to a Y position."""
    current_y = page.evaluate("window.scrollY")
    for i in range(steps):
        y = current_y + (target_y - current_y) * (i + 1) / steps
        page.evaluate(f"window.scrollTo(0, {int(y)})")
        snap(page, f"{label} step {i+1}/{steps}", delay=0.08)

def scroll_to_section(page, selector, label="section", offset=-100):
    """Scroll smoothly to a CSS selector."""
    target_y = page.evaluate(f"""
        (() => {{
            const el = document.querySelector('{selector}');
            if (!el) return 0;
            return el.getBoundingClientRect().top + window.scrollY + ({offset});
        }})()
    """)
    smooth_scroll(page, target_y, steps=25, label=label)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": WIDTH, "height": HEIGHT},
        device_scale_factor=2,  # retina-quality
    )
    page = context.new_page()
    
    print("Loading page...")
    page.goto(URL, wait_until="networkidle")
    time.sleep(2)
    
    # === SCENE 1: Hero ===
    print("\n=== SCENE 1: Hero ===")
    hold(page, 3, "hero")
    
    # === SCENE 2: Scroll to Pipeline ===
    print("\n=== SCENE 2: Pipeline ===")
    scroll_to_section(page, "#about", "about")
    hold(page, 2, "about section")
    scroll_to_section(page, "#pipeline", "pipeline")
    hold(page, 3, "pipeline visual")
    
    # === SCENE 3: Live Demo ===
    print("\n=== SCENE 3: Demo ===")
    scroll_to_section(page, "#demo", "demo section")
    hold(page, 1.5, "demo intro")
    
    # Click Sotorasib
    print("  Clicking Sotorasib...")
    page.click("text=Sotorasib")
    hold(page, 1, "sotorasib selected")
    
    # Click Generate Report
    print("  Clicking Generate Report...")
    page.click("#runBtn")
    hold(page, 1, "generating...")
    
    # Wait for report to appear
    time.sleep(4)
    hold(page, 3, "report loaded")
    
    # Scroll through the report
    report_el = page.query_selector("#demoOutput")
    if report_el:
        smooth_scroll(page, page.evaluate("window.scrollY") + 400, steps=15, label="report scroll")
        hold(page, 2, "report details")
    
    # === SCENE 4: Pro Features ===
    print("\n=== SCENE 4: Pro Features ===")
    scroll_to_section(page, "#pro-features", "pro features")
    hold(page, 2, "pro features")
    smooth_scroll(page, page.evaluate("window.scrollY") + 500, steps=15, label="pro scroll")
    hold(page, 2, "comparison table")
    
    # === SCENE 5: CLI ===
    print("\n=== SCENE 5: CLI ===")
    scroll_to_section(page, "#cli", "cli section")
    hold(page, 3, "cli terminal")
    smooth_scroll(page, page.evaluate("window.scrollY") + 600, steps=15, label="cli scroll")
    hold(page, 2, "agent commands")
    
    # === SCENE 6: Case Study ===
    print("\n=== SCENE 6: Case Study ===")
    scroll_to_section(page, "#case-study", "case study")
    hold(page, 2, "case study intro")
    smooth_scroll(page, page.evaluate("window.scrollY") + 500, steps=15, label="case scroll 1")
    hold(page, 2, "FAERS data")
    smooth_scroll(page, page.evaluate("window.scrollY") + 500, steps=15, label="case scroll 2")
    hold(page, 2, "novel compounds")
    smooth_scroll(page, page.evaluate("window.scrollY") + 500, steps=15, label="case scroll 3")
    hold(page, 2, "comparison + recommendation")
    
    # === SCENE 7: Pricing + Close ===
    print("\n=== SCENE 7: Close ===")
    scroll_to_section(page, "#pricing", "pricing")
    hold(page, 3, "pricing")
    
    # Scroll back to top
    smooth_scroll(page, 0, steps=30, label="back to hero")
    hold(page, 2, "final hero")
    
    browser.close()

print(f"\n✅ Captured {frame_num} frames in {OUTDIR}")

# Stitch into video
OUTPUT = "/home/democritus/.openclaw/workspace/pharmaclaw/poc_demo.mp4"
print(f"\nStitching video at {FPS} fps...")
cmd = [
    FFMPEG, "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(OUTDIR, "frame_%05d.png"),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
    "-preset", "medium",
    "-crf", "23",
    OUTPUT
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    size = os.path.getsize(OUTPUT) / (1024*1024)
    print(f"✅ Video saved: {OUTPUT} ({size:.1f} MB)")
else:
    print(f"❌ ffmpeg error: {result.stderr[-500:]}")
