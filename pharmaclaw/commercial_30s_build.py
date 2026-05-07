#!/usr/bin/env python3
"""
PharmaClaw 30-Second Commercial Builder
Generates HTML frames → screenshots → edge-tts audio → ffmpeg assembly
"""
import subprocess, json, os, shutil, time, math

WORK_DIR = "/home/democritus/.openclaw/workspace/pharmaclaw"
FRAMES_DIR = os.path.join(WORK_DIR, "commercial_frames")
AUDIO_DIR = os.path.join(WORK_DIR, "commercial_audio")
OUTPUT = os.path.join(WORK_DIR, "commercial_30s.mp4")
FPS = 30
WIDTH = 1920
HEIGHT = 1080
VOICE = "en-US-AndrewMultilingualNeural"

# Clean up
for d in [FRAMES_DIR, AUDIO_DIR]:
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)

# ── NARRATION SEGMENTS ──
segments = [
    {
        "id": "s1_problem",
        "text": "Drug discovery takes 10 years and 2 billion dollars. Most candidates fail.",
        "start": 0.0,
        "end": 5.0,
    },
    {
        "id": "s2_solution",
        "text": "PharmaClaw chains 9 AI agents into one pipeline — chemistry, ADME, toxicology, synthesis, IP, and market intel.",
        "start": 5.0,
        "end": 12.5,
    },
    {
        "id": "s3_demo",
        "text": "Feed it a molecule. Get a full drug intelligence report — in under 3 minutes.",
        "start": 12.5,
        "end": 20.0,
    },
    {
        "id": "s4_proof",
        "text": "Built by chemists. Powered by RDKit, PubChem, and FDA data. Free to start.",
        "start": 20.0,
        "end": 27.0,
    },
    {
        "id": "s5_cta",
        "text": "PharmaClaw dot com.",
        "start": 27.0,
        "end": 30.0,
    },
]

# ── STEP 1: Generate audio segments ──
print("=== STEP 1: Generating audio ===")
for seg in segments:
    out_mp3 = os.path.join(AUDIO_DIR, f"{seg['id']}.mp3")
    cmd = [
        "edge-tts",
        "--voice", VOICE,
        "--rate", "+5%",
        "--text", seg["text"],
        "--write-media", out_mp3,
    ]
    print(f"  TTS: {seg['id']}")
    subprocess.run(cmd, check=True, capture_output=True)
    # Get actual duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", out_mp3],
        capture_output=True, text=True
    )
    seg["audio_dur"] = float(probe.stdout.strip())
    print(f"    Duration: {seg['audio_dur']:.2f}s")

# ── STEP 2: Concatenate audio with proper timing ──
print("\n=== STEP 2: Building full audio track ===")
# Build a complex ffmpeg filter to place each segment at the right time
full_audio = os.path.join(AUDIO_DIR, "full_narration.mp3")

# Create silence base track (31 seconds to be safe)
subprocess.run([
    "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
    "-t", "31", "-c:a", "libmp3lame", "-q:a", "2",
    os.path.join(AUDIO_DIR, "silence_base.mp3")
], check=True, capture_output=True)

# Overlay each segment at its start time
filter_parts = []
inputs = ["-i", os.path.join(AUDIO_DIR, "silence_base.mp3")]
for i, seg in enumerate(segments):
    inputs += ["-i", os.path.join(AUDIO_DIR, f"{seg['id']}.mp3")]
    delay_ms = int(seg["start"] * 1000)
    filter_parts.append(f"[{i+1}]adelay={delay_ms}|{delay_ms}[d{i}]")

mix_inputs = "[0]" + "".join(f"[d{i}]" for i in range(len(segments)))
filter_str = ";".join(filter_parts) + f";{mix_inputs}amix=inputs={len(segments)+1}:duration=first:dropout_transition=0[out]"

cmd = ["ffmpeg", "-y"] + inputs + [
    "-filter_complex", filter_str,
    "-map", "[out]",
    "-t", "30",
    "-c:a", "libmp3lame", "-q:a", "2",
    full_audio
]
subprocess.run(cmd, check=True, capture_output=True)
print(f"  Full audio: {full_audio}")

# ── STEP 3: Generate HTML frames ──
print("\n=== STEP 3: Generating HTML frames ===")

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

def generate_scene1_frames(frame_start, frame_end):
    """THE PROBLEM - Dark bg, bold text fade in, molecule wireframe"""
    total = frame_end - frame_start
    for i in range(total):
        fn = frame_start + i
        progress = i / total
        
        # Text fade in over first 40% of scene
        text_opacity = min(1.0, progress / 0.4)
        # "Most candidates fail" appears at 60%
        fail_opacity = max(0, min(1.0, (progress - 0.5) / 0.3))
        
        # Molecule wireframe dots
        dots_html = ""
        import random
        random.seed(42)  # deterministic
        for d in range(20):
            x = random.randint(5, 95)
            y = random.randint(5, 95)
            size = random.randint(2, 6)
            op = 0.1 + 0.15 * math.sin(progress * 6.28 + d)
            dots_html += f'<div style="position:absolute;left:{x}%;top:{y}%;width:{size}px;height:{size}px;background:rgba(102,126,234,{op:.2f});border-radius:50%"></div>'
        
        # Connection lines
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
        .main-text{{text-align:center;z-index:10;position:relative}}
        .line1{{font-size:64px;font-weight:800;color:white;opacity:{text_opacity:.3f};
                text-shadow:0 0 40px rgba(102,126,234,0.5)}}
        .line2{{font-size:58px;font-weight:700;color:#f5576c;opacity:{fail_opacity:.3f};
                margin-top:30px;text-shadow:0 0 30px rgba(245,87,108,0.5)}}
        .stat{{font-size:28px;color:rgba(255,255,255,0.5);margin-top:20px;opacity:{text_opacity:.3f}}}
        </style></head><body>
        {lines_svg}
        {dots_html}
        <div class="main-text">
          <div class="line1">Drug discovery takes <span style="color:#667eea">10 years</span><br>and <span style="color:#667eea">$2 billion</span>.</div>
          <div class="line2">Most candidates fail.</div>
          <div class="stat">90% failure rate in clinical trials</div>
        </div>
        </body></html>'''
        
        with open(os.path.join(FRAMES_DIR, f"frame_{fn:05d}.html"), "w") as f:
            f.write(html)

def generate_scene2_frames(frame_start, frame_end):
    """THE SOLUTION - Logo reveal + 9 agents light up in sequence"""
    total = frame_end - frame_start
    for i in range(total):
        fn = frame_start + i
        progress = i / total
        
        # Logo fades in first 20%
        logo_opacity = min(1.0, progress / 0.2)
        # "9 AI agents" subtitle
        sub_opacity = min(1.0, max(0, (progress - 0.1) / 0.2))
        
        # Agents light up in sequence from 25% to 85%
        agents_html = '<div style="display:flex;gap:16px;margin-top:50px;justify-content:center;flex-wrap:wrap;max-width:1400px">'
        for a_idx in range(9):
            agent_progress = (progress - 0.2 - a_idx * 0.065)
            agent_opacity = min(1.0, max(0, agent_progress / 0.08))
            glow = f"0 0 20px {AGENT_COLORS[a_idx]}80" if agent_opacity > 0.5 else "none"
            scale = 0.8 + 0.2 * agent_opacity
            
            agents_html += f'''<div style="background:rgba(255,255,255,0.05);border:2px solid {AGENT_COLORS[a_idx]}{int(agent_opacity*255):02x};
                border-radius:16px;padding:20px 16px;width:140px;text-align:center;opacity:{agent_opacity:.2f};
                transform:scale({scale:.2f});box-shadow:{glow};transition:all 0.3s">
                <div style="font-size:36px;margin-bottom:8px">{AGENT_ICONS[a_idx]}</div>
                <div style="font-size:13px;font-weight:700;color:{AGENT_COLORS[a_idx]}">{AGENT_NAMES[a_idx]}</div>
            </div>'''
        agents_html += '</div>'
        
        # Pipeline arrow
        arrow_width = min(100, max(0, (progress - 0.3) * 200))
        arrow_html = f'''<div style="margin-top:30px;position:relative;height:4px;width:80%;max-width:1200px">
            <div style="position:absolute;left:0;top:0;height:100%;width:{arrow_width:.1f}%;
                 background:linear-gradient(90deg,#667eea,#764ba2,#f093fb);border-radius:2px;
                 box-shadow:0 0 15px rgba(102,126,234,0.5)"></div>
        </div>'''
        
        html = f'''<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e,#0f0f23);
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
        </style></head><body>
        <div style="font-size:72px;font-weight:900;background:linear-gradient(135deg,#667eea,#764ba2);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;opacity:{logo_opacity:.2f};
             text-shadow:none">PharmaClaw 🧪</div>
        <div style="font-size:32px;color:rgba(255,255,255,0.8);margin-top:15px;font-weight:300;opacity:{sub_opacity:.2f}">
            <span style="font-weight:700;color:#667eea">9 AI agents</span> · One pipeline</div>
        {agents_html}
        {arrow_html}
        </body></html>'''
        
        with open(os.path.join(FRAMES_DIR, f"frame_{fn:05d}.html"), "w") as f:
            f.write(html)

def generate_scene3_frames(frame_start, frame_end):
    """THE DEMO - SMILES input → report flash → scrolling results"""
    total = frame_end - frame_start
    for i in range(total):
        fn = frame_start + i
        progress = i / total
        
        # Phase 1 (0-30%): SMILES input typing
        # Phase 2 (30-50%): Processing animation
        # Phase 3 (50-100%): Report results flash
        
        if progress < 0.3:
            # SMILES typing
            smiles = "CC1=CC2=C(S1)C(=O)N(C2=O)C3CCC(CC3)NC(=O)C4=CC=NC=C4"
            typed_len = int(len(smiles) * progress / 0.3)
            typed = smiles[:typed_len]
            cursor = "▎" if (i % 10) < 5 else ""
            
            html = f'''<!DOCTYPE html><html><head><style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e);
                  display:flex;flex-direction:column;align-items:center;justify-content:center;
                  font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
            .input-box{{background:rgba(255,255,255,0.05);border:2px solid #667eea;border-radius:16px;
                       padding:30px 40px;max-width:1200px;width:80%}}
            .label{{color:rgba(255,255,255,0.5);font-size:20px;margin-bottom:12px}}
            .smiles{{color:#43e97b;font-size:28px;font-family:'Courier New',monospace;word-break:break-all}}
            </style></head><body>
            <div style="font-size:42px;color:white;margin-bottom:40px;font-weight:600">Feed it a molecule.</div>
            <div class="input-box">
              <div class="label">SMILES Input</div>
              <div class="smiles">{typed}{cursor}</div>
            </div>
            </body></html>'''
            
        elif progress < 0.5:
            # Processing animation
            proc_progress = (progress - 0.3) / 0.2
            active_agent = int(proc_progress * 9)
            
            agents_html = '<div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center">'
            for a_idx in range(9):
                if a_idx < active_agent:
                    color = "#43e97b"
                    icon_extra = "✓"
                elif a_idx == active_agent:
                    color = "#667eea"
                    icon_extra = "⟳" if (i % 8) < 4 else "↻"
                else:
                    color = "rgba(255,255,255,0.2)"
                    icon_extra = ""
                agents_html += f'''<div style="padding:12px 18px;border:2px solid {color};border-radius:12px;
                    text-align:center;min-width:120px">
                    <span style="font-size:14px;color:{color};font-weight:700">{AGENT_NAMES[a_idx]} {icon_extra}</span>
                </div>'''
            agents_html += '</div>'
            
            bar_width = proc_progress * 100
            html = f'''<!DOCTYPE html><html><head><style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e);
                  display:flex;flex-direction:column;align-items:center;justify-content:center;
                  font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden;gap:40px}}
            </style></head><body>
            <div style="font-size:42px;color:white;font-weight:600">Pipeline running...</div>
            {agents_html}
            <div style="width:60%;height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden">
              <div style="width:{bar_width:.1f}%;height:100%;background:linear-gradient(90deg,#667eea,#43e97b);border-radius:3px"></div>
            </div>
            </body></html>'''
        else:
            # Report results
            report_opacity = min(1.0, (progress - 0.5) / 0.15)
            scroll_offset = (progress - 0.5) * 400
            
            html = f'''<!DOCTYPE html><html><head><style>
            *{{margin:0;padding:0;box-sizing:border-box}}
            body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e);
                  display:flex;align-items:center;justify-content:center;
                  font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
            .report{{background:rgba(255,255,255,0.03);border:1px solid rgba(102,126,234,0.3);
                    border-radius:20px;padding:40px;width:85%;max-width:1400px;opacity:{report_opacity:.2f};
                    transform:translateY(-{scroll_offset:.0f}px)}}
            .header{{font-size:36px;color:white;font-weight:700;margin-bottom:25px;
                    border-bottom:2px solid #667eea;padding-bottom:15px}}
            .grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px}}
            .card{{background:rgba(255,255,255,0.05);border-radius:12px;padding:20px;border:1px solid rgba(255,255,255,0.1)}}
            .card-title{{color:#667eea;font-size:16px;font-weight:700;margin-bottom:10px}}
            .card-value{{color:white;font-size:28px;font-weight:800}}
            .card-sub{{color:rgba(255,255,255,0.5);font-size:13px;margin-top:5px}}
            .tag-pass{{color:#43e97b;font-size:14px;font-weight:600}} .tag-warn{{color:#f5576c;font-size:14px;font-weight:600}}
            </style></head><body>
            <div class="report">
              <div class="header">📋 Drug Intelligence Report — Sotorasib</div>
              <div class="grid">
                <div class="card"><div class="card-title">Molecular Weight</div><div class="card-value">560.6</div><div class="card-sub">g/mol</div></div>
                <div class="card"><div class="card-title">LogP</div><div class="card-value">4.0</div><div class="card-sub"><span class="tag-pass">✓ Lipinski OK</span></div></div>
                <div class="card"><div class="card-title">TPSA</div><div class="card-value">92.1 Å²</div><div class="card-sub"><span class="tag-pass">✓ Good absorption</span></div></div>
                <div class="card"><div class="card-title">QED Score</div><div class="card-value">0.48</div><div class="card-sub">Drug-likeness</div></div>
                <div class="card"><div class="card-title">FAERS Reports</div><div class="card-value">2,847</div><div class="card-sub"><span class="tag-warn">⚠ Diarrhea 35%</span></div></div>
                <div class="card"><div class="card-title">IP Risk</div><div class="card-value">HIGH</div><div class="card-sub"><span class="tag-warn">⚠ Patent → 2038</span></div></div>
              </div>
            </div>
            </body></html>'''
        
        with open(os.path.join(FRAMES_DIR, f"frame_{fn:05d}.html"), "w") as f:
            f.write(html)

def generate_scene4_frames(frame_start, frame_end):
    """THE PROOF - Tool logos + 'Free to start'"""
    total = frame_end - frame_start
    for i in range(total):
        fn = frame_start + i
        progress = i / total
        
        tools = [
            ("🧪", "RDKit", "Open-source cheminformatics"),
            ("🔎", "PubChem", "400M+ compounds"),
            ("🏛️", "FDA / FAERS", "Live safety data"),
            ("📖", "PubMed", "36M+ articles"),
        ]
        
        tools_html = '<div style="display:flex;gap:30px;margin-top:40px;justify-content:center">'
        for t_idx, (icon, name, desc) in enumerate(tools):
            t_opacity = min(1.0, max(0, (progress - t_idx * 0.12) / 0.15))
            tools_html += f'''<div style="background:rgba(255,255,255,0.05);border:1px solid rgba(102,126,234,{t_opacity*0.5:.2f});
                border-radius:16px;padding:30px 25px;text-align:center;width:200px;opacity:{t_opacity:.2f}">
                <div style="font-size:48px;margin-bottom:12px">{icon}</div>
                <div style="font-size:22px;color:white;font-weight:700">{name}</div>
                <div style="font-size:14px;color:rgba(255,255,255,0.5);margin-top:6px">{desc}</div>
            </div>'''
        tools_html += '</div>'
        
        # "Built by chemists" + "Free to start"
        text_opacity = min(1.0, progress / 0.25)
        badge_opacity = min(1.0, max(0, (progress - 0.5) / 0.2))
        badge_scale = 0.8 + 0.2 * badge_opacity
        glow = f"0 0 30px rgba(67,233,123,{badge_opacity * 0.4:.2f})"
        
        html = f'''<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e);
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
        </style></head><body>
        <div style="font-size:48px;color:white;font-weight:700;opacity:{text_opacity:.2f}">
            Built by <span style="color:#667eea">chemists</span>.</div>
        {tools_html}
        <div style="margin-top:50px;background:linear-gradient(135deg,#43e97b,#38f9d7);
             padding:18px 50px;border-radius:50px;opacity:{badge_opacity:.2f};
             transform:scale({badge_scale:.2f});box-shadow:{glow}">
            <span style="font-size:28px;font-weight:800;color:#0f0f23">Free to start →</span>
        </div>
        </body></html>'''
        
        with open(os.path.join(FRAMES_DIR, f"frame_{fn:05d}.html"), "w") as f:
            f.write(html)

def generate_scene5_frames(frame_start, frame_end):
    """CTA - Logo + URL"""
    total = frame_end - frame_start
    for i in range(total):
        fn = frame_start + i
        progress = i / total
        
        opacity = min(1.0, progress / 0.3)
        glow_intensity = 0.3 + 0.2 * math.sin(progress * 6.28)
        
        html = f'''<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{width:{WIDTH}px;height:{HEIGHT}px;background:linear-gradient(135deg,#0f0f23,#1a1a3e,#0f0f23);
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden}}
        </style></head><body>
        <div style="font-size:96px;font-weight:900;background:linear-gradient(135deg,#667eea,#764ba2);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;opacity:{opacity:.2f}">
            PharmaClaw</div>
        <div style="font-size:20px;margin-top:10px;opacity:{opacity * 0.7:.2f}">🧪</div>
        <div style="font-size:36px;color:rgba(255,255,255,0.9);margin-top:30px;font-weight:300;
             letter-spacing:4px;opacity:{opacity:.2f};
             text-shadow:0 0 30px rgba(102,126,234,{glow_intensity:.2f})">
            pharmaclaw.com</div>
        </body></html>'''
        
        with open(os.path.join(FRAMES_DIR, f"frame_{fn:05d}.html"), "w") as f:
            f.write(html)

# Generate all scene frames
# Scene timings (in frames at 30fps)
scenes = [
    (generate_scene1_frames, 0, 5.0),      # 0:00-0:05
    (generate_scene2_frames, 5.0, 12.5),    # 0:05-0:12.5
    (generate_scene3_frames, 12.5, 20.0),   # 0:12.5-0:20
    (generate_scene4_frames, 20.0, 27.0),   # 0:20-0:27
    (generate_scene5_frames, 27.0, 30.0),   # 0:27-0:30
]

for gen_func, start_sec, end_sec in scenes:
    f_start = int(start_sec * FPS)
    f_end = int(end_sec * FPS)
    print(f"  Generating {gen_func.__name__}: frames {f_start}-{f_end} ({end_sec-start_sec:.1f}s)")
    gen_func(f_start, f_end)

total_frames = int(30.0 * FPS)
print(f"\n  Total HTML frames: {total_frames}")

# ── STEP 4: Render HTML to PNG ──
print("\n=== STEP 4: Rendering HTML → PNG via Playwright ===")
render_script = os.path.join(WORK_DIR, "commercial_render.py")

with open(render_script, "w") as f:
    f.write(f'''#!/usr/bin/env python3
import asyncio, os, glob
from playwright.async_api import async_playwright

FRAMES_DIR = "{FRAMES_DIR}"
WIDTH = {WIDTH}
HEIGHT = {HEIGHT}

async def render_all():
    html_files = sorted(glob.glob(os.path.join(FRAMES_DIR, "frame_*.html")))
    print(f"  Rendering {{len(html_files)}} frames...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={{"width": WIDTH, "height": HEIGHT}})
        
        for idx, html_file in enumerate(html_files):
            png_file = html_file.replace(".html", ".png")
            await page.goto(f"file://{{html_file}}")
            await page.screenshot(path=png_file)
            if idx % 100 == 0:
                print(f"    {{idx}}/{{len(html_files)}} rendered")
        
        await browser.close()
    print(f"  Done rendering {{len(html_files)}} frames.")

asyncio.run(render_all())
''')

subprocess.run(["python3", render_script], check=True)

# Clean up HTML files to save space
for html_file in sorted(os.listdir(FRAMES_DIR)):
    if html_file.endswith(".html"):
        os.remove(os.path.join(FRAMES_DIR, html_file))

# ── STEP 5: Assemble video ──
print("\n=== STEP 5: Assembling final video ===")
subprocess.run([
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", os.path.join(FRAMES_DIR, "frame_%05d.png"),
    "-i", full_audio,
    "-c:v", "libx264", "-preset", "slow", "-crf", "18",
    "-c:a", "aac", "-b:a", "192k",
    "-pix_fmt", "yuv420p",
    "-t", "30",
    "-shortest",
    OUTPUT
], check=True)

# Final duration check
probe = subprocess.run(
    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", OUTPUT],
    capture_output=True, text=True
)
print(f"\n✅ Commercial built: {OUTPUT}")
print(f"   Duration: {float(probe.stdout.strip()):.1f}s")
print(f"   Size: {os.path.getsize(OUTPUT) / 1024 / 1024:.1f}MB")
