#!/usr/bin/env python3
"""
PharmaClaw POC v2 — Video timed to narration.
1. Generate TTS first to get exact durations
2. Record video with scene lengths matching audio
3. Merge
"""
import asyncio, os, time, subprocess, json, threading, http.server, functools
from playwright.sync_api import sync_playwright

FFMPEG = os.path.expanduser("~/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/bin/ffprobe")
WORKSPACE = "/home/democritus/.openclaw/workspace/pharmaclaw"
FRAME_DIR = os.path.join(WORKSPACE, "poc_v2_frames")
AUDIO_DIR = os.path.join(WORKSPACE, "poc_v2_audio")
SITE_DIR = WORKSPACE
PORT = 8765
VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+8%"  # A touch faster
WIDTH, HEIGHT = 1280, 800
VID_FPS = 4  # frames per second

for d in [FRAME_DIR, AUDIO_DIR]:
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))

# === NARRATION SEGMENTS ===
SEGMENTS = [
    ("s1_hook",
     "What if you could go from a single molecule, to a full drug discovery report, "
     "in under three minutes? This is PharmaClaw. Nine AI agents. One pipeline."),
    
    ("s2_pipeline",
     "PharmaClaw chains nine specialized agents. You feed it a SMILES string. "
     "Chemistry hits PubChem and RDKit. Pharmacology profiles ADME. "
     "Toxicology flags structural alerts. Synthesis plans retrosynthesis routes. "
     "And Market Intel pulls live FDA data. Every agent's output feeds the next."),
    
    ("s3_demo",
     "Let's run one. Sotorasib, Amgen's KRAS inhibitor for lung cancer. "
     "One click and the pipeline chains all agents. "
     "Chemistry pulled molecular weight 560 and five rings. "
     "FAERS shows 2,000 plus adverse event reports, diarrhea at 35 percent is the top signal. "
     "IP flags the Amgen patent through 2038, but suggests novel directions."),
    
    ("s4_pro",
     "Pro unlocks the full chain. Compare up to five candidates side-by-side. "
     "Batch 500 compounds from a CSV. Export team-ready PDF reports."),
    
    ("s5_cli",
     "Prefer the terminal? pip install pharmaclaw CLI. "
     "Nine agents, JSON in, JSON out. "
     "LangGraph orchestration runs the full pipeline with smart routing and consensus scoring."),
    
    ("s6_case",
     "In our case study, PharmaClaw designed three novel lung cancer compounds from scratch, "
     "targeting real FAERS safety gaps. The top pick passes Lipinski and is rated easy to synthesize."),
    
    ("s7_close",
     "Free to start. Pro at 49 a month. "
     "PharmaClaw. Real data, real chemistry, real results."),
]

# === STEP 1: Generate all TTS ===
async def gen_tts():
    import edge_tts
    durations = []
    for name, text in SEGMENTS:
        outfile = os.path.join(AUDIO_DIR, f"{name}.mp3")
        comm = edge_tts.Communicate(text, VOICE, rate=RATE)
        await comm.save(outfile)
        r = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration", "-of", "json", outfile],
                          capture_output=True, text=True)
        dur = float(json.loads(r.stdout)["format"]["duration"])
        durations.append((name, dur, outfile))
        print(f"  🎙️ {name}: {dur:.1f}s")
    return durations

print("=== Step 1: Generating narration ===")
audio_segments = asyncio.run(gen_tts())

# Add 1s buffer between segments
scene_durations = [(name, dur + 1.0, path) for name, dur, path in audio_segments]
total_duration = sum(d for _, d, _ in scene_durations)
print(f"\nTotal video duration: {total_duration:.1f}s")

# === STEP 2: Record video timed to narration ===
print("\n=== Step 2: Recording video ===")

# Start server
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE_DIR)
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

def scroll_to(page, sel, offset=-50, steps=20):
    y = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top + window.scrollY + ({offset})")
    cur = page.evaluate("window.scrollY")
    for i in range(steps):
        t = (i+1)/steps; ease = t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0, {int(cur + (y-cur)*ease)})")
        snap(page, 0.03)

def scroll_down(page, px, steps=15):
    cur = page.evaluate("window.scrollY")
    for i in range(steps):
        t = (i+1)/steps; ease = t*t*(3-2*t)
        page.evaluate(f"window.scrollTo(0, {int(cur + px*ease)})")
        snap(page, 0.03)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
    page.goto(f"http://localhost:{PORT}", wait_until="domcontentloaded", timeout=30000)
    time.sleep(2)
    
    # Scene 1: Hero (dur from TTS)
    s1_dur = scene_durations[0][1]
    print(f"  Scene 1: Hero ({s1_dur:.1f}s)")
    hold(page, s1_dur)
    
    # Scene 2: Pipeline
    s2_dur = scene_durations[1][1]
    print(f"  Scene 2: Pipeline ({s2_dur:.1f}s)")
    scroll_to(page, "#about", steps=20)
    hold(page, s2_dur * 0.3)
    scroll_to(page, "#pipeline", steps=20)
    hold(page, s2_dur * 0.5)
    
    # Scene 3: Demo
    s3_dur = scene_durations[2][1]
    print(f"  Scene 3: Demo ({s3_dur:.1f}s)")
    scroll_to(page, "#demo", steps=20)
    hold(page, 1.5)
    page.click("text=Sotorasib")
    hold(page, 0.5)
    page.click("#runBtn")
    hold(page, 0.5)
    time.sleep(3.5)
    hold(page, s3_dur * 0.3)
    scroll_down(page, 350, steps=15)
    hold(page, s3_dur * 0.3)
    
    # Scene 4: Pro Features
    s4_dur = scene_durations[3][1]
    print(f"  Scene 4: Pro ({s4_dur:.1f}s)")
    scroll_to(page, "#pro-features", steps=20)
    hold(page, s4_dur * 0.4)
    scroll_down(page, 500, steps=15)
    hold(page, s4_dur * 0.4)
    
    # Scene 5: CLI
    s5_dur = scene_durations[4][1]
    print(f"  Scene 5: CLI ({s5_dur:.1f}s)")
    scroll_to(page, "#cli", steps=20)
    hold(page, s5_dur * 0.4)
    scroll_down(page, 500, steps=15)
    hold(page, s5_dur * 0.3)
    
    # Scene 6: Case Study
    s6_dur = scene_durations[5][1]
    print(f"  Scene 6: Case Study ({s6_dur:.1f}s)")
    scroll_to(page, "#case-study", steps=20)
    hold(page, s6_dur * 0.25)
    scroll_down(page, 500, steps=15)
    hold(page, s6_dur * 0.25)
    scroll_down(page, 500, steps=15)
    hold(page, s6_dur * 0.25)
    
    # Scene 7: Close
    s7_dur = scene_durations[6][1]
    print(f"  Scene 7: Close ({s7_dur:.1f}s)")
    scroll_to(page, "#pricing", steps=20)
    hold(page, s7_dur * 0.5)
    scroll_to(page, "nav", offset=0, steps=30)
    hold(page, s7_dur * 0.3)
    
    browser.close()

print(f"\n✅ {frame_num} frames captured")

# === STEP 3: Encode video ===
print("\n=== Step 3: Encoding video ===")
VIDEO_ONLY = os.path.join(WORKSPACE, "poc_v2_video.mp4")
subprocess.run([FFMPEG, "-y",
    "-framerate", str(VID_FPS),
    "-i", f"{FRAME_DIR}/frame_%05d.png",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2",
    "-preset", "medium", "-crf", "20", "-r", "30",
    VIDEO_ONLY], capture_output=True, text=True)

# === STEP 4: Merge audio + video ===
print("=== Step 4: Merging narration with video ===")

# Build concat audio with proper timing
filter_inputs = []
filter_parts = []
offset_ms = 0
for i, (name, dur, path) in enumerate(scene_durations):
    filter_inputs.extend(["-i", path])
    filter_parts.append(f"[{i+1}:a]adelay={int(offset_ms)}|{int(offset_ms)},apad=pad_dur=1[a{i}]")
    offset_ms += int(dur * 1000)

mix_inputs = "".join(f"[a{i}]" for i in range(len(scene_durations)))
filter_parts.append(f"{mix_inputs}amix=inputs={len(scene_durations)}:normalize=0[aout]")
filter_str = ";".join(filter_parts)

FINAL = os.path.join(WORKSPACE, "poc_demo_narrated_v2.mp4")
cmd = [FFMPEG, "-y", "-i", VIDEO_ONLY]
for _, _, path in scene_durations:
    cmd.extend(["-i", path])
cmd.extend([
    "-filter_complex", filter_str,
    "-map", "0:v", "-map", "[aout]",
    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
    "-shortest", FINAL
])

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    size = os.path.getsize(FINAL) / (1024*1024)
    r = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration", "-of", "json", FINAL],
                      capture_output=True, text=True)
    dur = json.loads(r.stdout)["format"]["duration"]
    print(f"\n🎬 FINAL VIDEO: {FINAL}")
    print(f"   Duration: {float(dur):.1f}s | Size: {size:.1f} MB")
    print(f"   Voice: {VOICE} | Rate: {RATE}")
else:
    print(f"❌ Error: {result.stderr[-500:]}")
