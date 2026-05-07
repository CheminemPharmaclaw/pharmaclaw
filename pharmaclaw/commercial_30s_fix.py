#!/usr/bin/env python3
"""
Fix audio overlap: rebuild audio track with sequential placement based on actual durations.
Then regenerate video frames to match new timings.
"""
import subprocess, os, json, shutil, math, random

WORK_DIR = "/home/democritus/.openclaw/workspace/pharmaclaw"
FRAMES_DIR = os.path.join(WORK_DIR, "commercial_frames")
AUDIO_DIR = os.path.join(WORK_DIR, "commercial_audio")
OUTPUT = os.path.join(WORK_DIR, "commercial_30s.mp4")
FPS = 30
WIDTH = 1920
HEIGHT = 1080
GAP = 0.3  # seconds gap between segments

# Clean frames
if os.path.exists(FRAMES_DIR):
    shutil.rmtree(FRAMES_DIR)
os.makedirs(FRAMES_DIR)

# ── Get actual audio durations ──
segments = [
    {"id": "s1_problem", "file": os.path.join(AUDIO_DIR, "s1_problem.mp3")},
    {"id": "s2_solution", "file": os.path.join(AUDIO_DIR, "s2_solution.mp3")},
    {"id": "s3_demo", "file": os.path.join(AUDIO_DIR, "s3_demo.mp3")},
    {"id": "s4_proof", "file": os.path.join(AUDIO_DIR, "s4_proof.mp3")},
    {"id": "s5_cta", "file": os.path.join(AUDIO_DIR, "s5_cta.mp3")},
]

print("=== Audio durations ===")
cursor = 0.2  # small lead-in
for seg in segments:
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", seg["file"]],
        capture_output=True, text=True
    )
    seg["dur"] = float(probe.stdout.strip())
    seg["start"] = cursor
    seg["end"] = cursor + seg["dur"]
    cursor = seg["end"] + GAP
    print(f"  {seg['id']}: start={seg['start']:.2f} dur={seg['dur']:.2f} end={seg['end']:.2f}")

TOTAL_DUR = max(30.0, cursor)
print(f"\n  Total needed: {cursor:.2f}s (target: 30s)")

# If total exceeds 30s, we need to trim gap or speed up
if cursor > 30.5:
    print("  WARNING: Content exceeds 30s, reducing gaps...")
    GAP = 0.15
    cursor = 0.15
    for seg in segments:
        seg["start"] = cursor
        seg["end"] = cursor + seg["dur"]
        cursor = seg["end"] + GAP
    TOTAL_DUR = max(30.0, cursor)
    print(f"  Adjusted total: {cursor:.2f}s")

TOTAL_DUR = max(30.0, TOTAL_DUR)

# ── Rebuild audio track (sequential, no overlap) ──
print("\n=== Rebuilding audio track ===")
full_audio = os.path.join(AUDIO_DIR, "full_narration_v2.mp3")

# Create silence base
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
    "-t", str(TOTAL_DUR + 1), "-c:a", "libmp3lame", "-q:a", "2",
    os.path.join(AUDIO_DIR, "silence_base_v2.mp3")
], check=True, capture_output=True)

# Overlay each segment at computed start time
filter_parts = []
inputs = ["-i", os.path.join(AUDIO_DIR, "silence_base_v2.mp3")]
for i, seg in enumerate(segments):
    inputs += ["-i", seg["file"]]
    delay_ms = int(seg["start"] * 1000)
    filter_parts.append(f"[{i+1}]adelay={delay_ms}|{delay_ms}[d{i}]")

mix_inputs = "[0]" + "".join(f"[d{i}]" for i in range(len(segments)))
filter_str = ";".join(filter_parts) + f";{mix_inputs}amix=inputs={len(segments)+1}:duration=first:dropout_transition=0[out]"

cmd = ["ffmpeg", "-y"] + inputs + [
    "-filter_complex", filter_str,
    "-map", "[out]",
    "-t", str(TOTAL_DUR),
    "-c:a", "libmp3lame", "-q:a", "2",
    full_audio
]
subprocess.run(cmd, check=True, capture_output=True)
print(f"  Audio: {full_audio}")

# ── Scene timing from audio ──
# Each scene matches its audio segment, with visual transitions
scene_times = []
for seg in segments:
    scene_times.append((seg["start"], seg["end"]))
    
print("\n=== Scene timings ===")
labels = ["PROBLEM", "SOLUTION", "DEMO", "PROOF", "CTA"]
for i, (start, end) in enumerate(scene_times):
    print(f"  {labels[i]}: {start:.2f}s - {end:.2f}s ({end-start:.2f}s)")

# ── Constants for visuals ──
AGENT_NAMES = [
    "Chemistry Query", "Cheminformatics", "Pharmacology",
    "Toxicology", "Catalyst Design", "Literature",
    "IP Expansion", "Market Intel", "AlphaFold"
]
AGENT_ICONS = ["⚗️", "🔬", "💊", "☠️", "🧲", "📚", "📜", "📊", "🧬"]
AGENT_COLORS = [
    "#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe",
    "#43e97b", "#fa709a", "#fee140", "#a18cd1"
]

# ── Generate frames ──
print("\n=== Generating frames ===")
total_frames = int(TOTAL_DUR * FPS)

def get_scene_for_time(t):
    """Return scene index and progress within that scene"""
    for i, (start, end) in enumerate(scene_times):
        if t < end + GAP/2 or i == len(scene_times) - 1:
            progress = max(0, min(1, (t - start) / (end - start))) if end > start else 0
            return i, progress
    return len(scene_times) - 1, 1.0

for fn in range(total_frames):
    t = fn / FPS
    scene_idx, progress = get_scene_for_time(t)
    
    if scene_idx == 0:
        # SCENE 1: THE PROBLEM
        text_opacity = min(1.0, progress / 0.4)
        fail_opacity = max(0, min(1.0, (progress - 0.5) / 0.3))
        
        random.seed(42)
        dots_html = ""
        for d in range(20):
            x, y = random.randint(5, 95), random.randint(5, 95)
            size = random.randint(2, 6)
            op = 0.1 + 0.15 * math.sin(progress * 6.28 + d)
            dots_html += f'<div style="position:absolute;left:{x}%;top:{y}%;width:{size}px;height:{size}px;background:rgba(102,126,234,{op:.2f});border-radius:50%"></div>'
        
        lines_svg = '<svg style="position:absolute;inset:0;width:100%;height:100%;opacity:0.08"><defs><filter id="glow"><feGaussianBlur stdDeviation="2"/></filter></defs>'
        random.seed(43)
        for _ in range(15):
            x1,y1 = random.randint(0,1920), random.randint(0,1080)
            x2,y2 = random.randint(0,1920), random.randint(0,1080)
            lines_svg += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#667eea" stroke-width="1" filter="url(#glow)"/>'
        lines_svg += '</svg>'
        
        html = f'''<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e,#0f0f23);
              display:flex;align-items:center;justify-content:center;font-family:'Segoe UI',system-ui,sans-serif;
              position:relative;overflow:hidden}}
        </style></head><body>
        {lines_svg}{dots_html}
        <div style="text-align:center;z-index:10;position:relative">
          <div style="font-size:64px;font-weight:800;color:white;opacity:{text_opacity:.3f};text-shadow:0 0 40px rgba(102,126,234,0.5)">
            Drug discovery takes <span style="color:#667eea">10 years</span><br>and <span style="color:#667eea">$2 billion</span>.</div>
          <div style="font-size:58px;font-weight:700;color:#f5576c;opacity:{fail_opacity:.3f};margin-top:30px;text-shadow:0 0 30px rgba(245,87,108,0.5)">Most candidates fail.</div>
          <div style="font-size:28px;color:rgba(255,255,255,0.5);margin-top:20px;opacity:{text_opacity:.3f}">90% failure rate in clinical trials</div>
        </div></body></html>'''

    elif scene_idx == 1:
        # SCENE 2: THE SOLUTION
        logo_opacity = min(1.0, progress / 0.15)
        sub_opacity = min(1.0, max(0, (progress - 0.08) / 0.15))
        
        agents_html = '<div style="display:flex;gap:16px;margin-top:50px;justify-content:center;flex-wrap:wrap;max-width:1400px">'
        for a_idx in range(9):
            ap = (progress - 0.15 - a_idx * 0.07)
            ao = min(1.0, max(0, ap / 0.08))
            glow = f"0 0 20px {AGENT_COLORS[a_idx]}80" if ao > 0.5 else "none"
            scale = 0.8 + 0.2 * ao
            agents_html += f'''<div style="background:rgba(255,255,255,0.05);border:2px solid {AGENT_COLORS[a_idx]}{int(ao*255):02x};
                border-radius:16px;padding:20px 16px;width:140px;text-align:center;opacity:{ao:.2f};
                transform:scale({scale:.2f});box-shadow:{glow}">
                <div style="font-size:36px;margin-bottom:8px">{AGENT_ICONS[a_idx]}</div>
                <div style="font-size:13px;font-weight:700;color:{AGENT_COLORS[a_idx]}">{AGENT_NAMES[a_idx]}</div>
            </div>'''
        agents_html += '</div>'
        
        arrow_width = min(100, max(0, (progress - 0.25) * 150))
        html = f'''<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e,#0f0f23);
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
        </style></head><body>
        <div style="font-size:72px;font-weight:900;background:linear-gradient(135deg,#667eea,#764ba2);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;opacity:{logo_opacity:.2f}">PharmaClaw 🧪</div>
        <div style="font-size:32px;color:rgba(255,255,255,0.8);margin-top:15px;font-weight:300;opacity:{sub_opacity:.2f}">
            <span style="font-weight:700;color:#667eea">9 AI agents</span> · One pipeline</div>
        {agents_html}
        <div style="margin-top:30px;position:relative;height:4px;width:80%;max-width:1200px">
            <div style="position:absolute;left:0;top:0;height:100%;width:{arrow_width:.1f}%;
                 background:linear-gradient(90deg,#667eea,#764ba2,#f093fb);border-radius:2px;
                 box-shadow:0 0 15px rgba(102,126,234,0.5)"></div>
        </div></body></html>'''

    elif scene_idx == 2:
        # SCENE 3: THE DEMO
        if progress < 0.3:
            smiles = "CC1=CC2=C(S1)C(=O)N(C2=O)C3CCC(CC3)NC(=O)C4=CC=NC=C4"
            typed_len = int(len(smiles) * progress / 0.3)
            typed = smiles[:typed_len]
            cursor = "▎" if (fn % 10) < 5 else ""
            html = f'''<!DOCTYPE html><html><head><style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e);
                  display:flex;flex-direction:column;align-items:center;justify-content:center;
                  font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
            </style></head><body>
            <div style="font-size:42px;color:white;margin-bottom:40px;font-weight:600">Feed it a molecule.</div>
            <div style="background:rgba(255,255,255,0.05);border:2px solid #667eea;border-radius:16px;padding:30px 40px;max-width:1200px;width:80%">
              <div style="color:rgba(255,255,255,0.5);font-size:20px;margin-bottom:12px">SMILES Input</div>
              <div style="color:#43e97b;font-size:28px;font-family:'Courier New',monospace;word-break:break-all">{typed}{cursor}</div>
            </div></body></html>'''
        elif progress < 0.5:
            pp = (progress - 0.3) / 0.2
            active = int(pp * 9)
            agents_html = '<div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center">'
            for a_idx in range(9):
                if a_idx < active:
                    color, icon_extra = "#43e97b", "✓"
                elif a_idx == active:
                    color, icon_extra = "#667eea", ("⟳" if (fn % 8) < 4 else "↻")
                else:
                    color, icon_extra = "rgba(255,255,255,0.2)", ""
                agents_html += f'<div style="padding:12px 18px;border:2px solid {color};border-radius:12px;text-align:center;min-width:120px"><span style="font-size:14px;color:{color};font-weight:700">{AGENT_NAMES[a_idx]} {icon_extra}</span></div>'
            agents_html += '</div>'
            bw = pp * 100
            html = f'''<!DOCTYPE html><html><head><style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e);
                  display:flex;flex-direction:column;align-items:center;justify-content:center;
                  font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden;gap:40px}}
            </style></head><body>
            <div style="font-size:42px;color:white;font-weight:600">Pipeline running...</div>
            {agents_html}
            <div style="width:60%;height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden">
              <div style="width:{bw:.1f}%;height:100%;background:linear-gradient(90deg,#667eea,#43e97b);border-radius:3px"></div>
            </div></body></html>'''
        else:
            ro = min(1.0, (progress - 0.5) / 0.15)
            scroll = (progress - 0.5) * 400
            html = f'''<!DOCTYPE html><html><head><style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e);
                  display:flex;align-items:center;justify-content:center;
                  font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
            .g{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}}
            .c{{background:rgba(255,255,255,0.05);border-radius:12px;padding:20px;border:1px solid rgba(255,255,255,0.1)}}
            </style></head><body>
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(102,126,234,0.3);border-radius:20px;padding:40px;width:85%;max-width:1400px;opacity:{ro:.2f};transform:translateY(-{scroll:.0f}px)">
              <div style="font-size:36px;color:white;font-weight:700;margin-bottom:25px;border-bottom:2px solid #667eea;padding-bottom:15px">📋 Drug Intelligence Report — Sotorasib</div>
              <div class="g">
                <div class="c"><div style="color:#667eea;font-size:16px;font-weight:700;margin-bottom:10px">Molecular Weight</div><div style="color:white;font-size:28px;font-weight:800">560.6</div><div style="color:rgba(255,255,255,0.5);font-size:13px;margin-top:5px">g/mol</div></div>
                <div class="c"><div style="color:#667eea;font-size:16px;font-weight:700;margin-bottom:10px">LogP</div><div style="color:white;font-size:28px;font-weight:800">4.0</div><div style="color:#43e97b;font-size:14px;font-weight:600;margin-top:5px">✓ Lipinski OK</div></div>
                <div class="c"><div style="color:#667eea;font-size:16px;font-weight:700;margin-bottom:10px">TPSA</div><div style="color:white;font-size:28px;font-weight:800">92.1 Å²</div><div style="color:#43e97b;font-size:14px;font-weight:600;margin-top:5px">✓ Good absorption</div></div>
                <div class="c"><div style="color:#667eea;font-size:16px;font-weight:700;margin-bottom:10px">QED Score</div><div style="color:white;font-size:28px;font-weight:800">0.48</div><div style="color:rgba(255,255,255,0.5);font-size:13px;margin-top:5px">Drug-likeness</div></div>
                <div class="c"><div style="color:#667eea;font-size:16px;font-weight:700;margin-bottom:10px">FAERS Reports</div><div style="color:white;font-size:28px;font-weight:800">2,847</div><div style="color:#f5576c;font-size:14px;font-weight:600;margin-top:5px">⚠ Diarrhea 35%</div></div>
                <div class="c"><div style="color:#667eea;font-size:16px;font-weight:700;margin-bottom:10px">IP Risk</div><div style="color:white;font-size:28px;font-weight:800">HIGH</div><div style="color:#f5576c;font-size:14px;font-weight:600;margin-top:5px">⚠ Patent → 2038</div></div>
              </div>
            </div></body></html>'''

    elif scene_idx == 3:
        # SCENE 4: THE PROOF
        tools = [("🧪","RDKit","Open-source cheminformatics"),("🔎","PubChem","400M+ compounds"),("🏛️","FDA / FAERS","Live safety data"),("📖","PubMed","36M+ articles")]
        text_opacity = min(1.0, progress / 0.2)
        
        tools_html = '<div style="display:flex;gap:30px;margin-top:40px;justify-content:center">'
        for t_idx, (icon, name, desc) in enumerate(tools):
            to = min(1.0, max(0, (progress - t_idx * 0.1) / 0.12))
            tools_html += f'''<div style="background:rgba(255,255,255,0.05);border:1px solid rgba(102,126,234,{to*0.5:.2f});
                border-radius:16px;padding:30px 25px;text-align:center;width:200px;opacity:{to:.2f}">
                <div style="font-size:48px;margin-bottom:12px">{icon}</div>
                <div style="font-size:22px;color:white;font-weight:700">{name}</div>
                <div style="font-size:14px;color:rgba(255,255,255,0.5);margin-top:6px">{desc}</div>
            </div>'''
        tools_html += '</div>'
        
        bo = min(1.0, max(0, (progress - 0.5) / 0.2))
        bs = 0.8 + 0.2 * bo
        html = f'''<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e);
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
        </style></head><body>
        <div style="font-size:48px;color:white;font-weight:700;opacity:{text_opacity:.2f}">Built by <span style="color:#667eea">chemists</span>.</div>
        {tools_html}
        <div style="margin-top:50px;background:linear-gradient(135deg,#43e97b,#38f9d7);padding:18px 50px;border-radius:50px;opacity:{bo:.2f};transform:scale({bs:.2f});box-shadow:0 0 30px rgba(67,233,123,{bo*0.4:.2f})">
            <span style="font-size:28px;font-weight:800;color:#0f0f23">Free to start →</span>
        </div></body></html>'''

    else:
        # SCENE 5: CTA
        opacity = min(1.0, progress / 0.3)
        gi = 0.3 + 0.2 * math.sin(progress * 6.28)
        html = f'''<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e,#0f0f23);
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
        </style></head><body>
        <div style="font-size:96px;font-weight:900;background:linear-gradient(135deg,#667eea,#764ba2);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;opacity:{opacity:.2f}">PharmaClaw</div>
        <div style="font-size:20px;margin-top:10px;opacity:{opacity*0.7:.2f}">🧪</div>
        <div style="font-size:36px;color:rgba(255,255,255,0.9);margin-top:30px;font-weight:300;
             letter-spacing:4px;opacity:{opacity:.2f};text-shadow:0 0 30px rgba(102,126,234,{gi:.2f})">pharmaclaw.com</div>
        </body></html>'''
    
    with open(os.path.join(FRAMES_DIR, f"frame_{fn:05d}.html"), "w") as f:
        f.write(html)

print(f"  Generated {total_frames} HTML frames")

# ── Render HTML → PNG ──
print("\n=== Rendering HTML → PNG ===")
render_script = os.path.join(WORK_DIR, "commercial_render_v2.py")
with open(render_script, "w") as f:
    f.write(f'''#!/usr/bin/env python3
import asyncio, os, glob
from playwright.async_api import async_playwright

async def render_all():
    html_files = sorted(glob.glob(os.path.join("{FRAMES_DIR}", "frame_*.html")))
    print(f"  Rendering {{len(html_files)}} frames...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={{"width": {WIDTH}, "height": {HEIGHT}}})
        for idx, hf in enumerate(html_files):
            await page.goto(f"file://{{hf}}")
            await page.screenshot(path=hf.replace(".html", ".png"))
            if idx % 150 == 0:
                print(f"    {{idx}}/{{len(html_files)}}")
        await browser.close()
    print(f"  Done.")

asyncio.run(render_all())
''')
subprocess.run(["python3", render_script], check=True)

# Clean HTML
for f in os.listdir(FRAMES_DIR):
    if f.endswith(".html"):
        os.remove(os.path.join(FRAMES_DIR, f))

# ── Assemble final video ──
print("\n=== Assembling video ===")
subprocess.run([
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(FRAMES_DIR, "frame_%05d.png"),
    "-i", full_audio,
    "-c:v", "libx264", "-preset", "slow", "-crf", "18",
    "-c:a", "aac", "-b:a", "192k",
    "-pix_fmt", "yuv420p",
    "-t", str(TOTAL_DUR),
    "-shortest",
    OUTPUT
], check=True)

probe = subprocess.run(
    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", OUTPUT],
    capture_output=True, text=True
)
print(f"\n✅ Commercial rebuilt: {OUTPUT}")
print(f"   Duration: {float(probe.stdout.strip()):.1f}s")
print(f"   Size: {os.path.getsize(OUTPUT) / 1024 / 1024:.1f}MB")
print(f"   Audio segments are now sequential — no overlap!")
