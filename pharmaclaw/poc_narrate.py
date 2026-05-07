#!/usr/bin/env python3
"""Generate TTS narration for PharmaClaw POC demo, then merge with video."""
import asyncio, os, subprocess, json

FFMPEG = os.path.expanduser("~/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/bin/ffprobe")
AUDIO_DIR = "/home/democritus/.openclaw/workspace/pharmaclaw/poc_audio"
VIDEO = "/home/democritus/.openclaw/workspace/pharmaclaw/poc_demo_final.mp4"
OUTPUT = "/home/democritus/.openclaw/workspace/pharmaclaw/poc_demo_narrated.mp4"
VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+5%"  # Slightly faster for professional feel

os.makedirs(AUDIO_DIR, exist_ok=True)

# Narration segments — timed to the 54s video
# Each tuple: (filename, start_time_seconds, narration_text)
SEGMENTS = [
    ("s1_hook", 0.0,
     "What if you could go from a single molecule to a full drug discovery report "
     "in under three minutes? This is PharmaClaw. Nine AI agents. One pipeline."),
    
    ("s2_pipeline", 8.0,
     "PharmaClaw chains nine specialized agents. Chemistry Query hits PubChem and RDKit. "
     "Pharmacology runs ADME profiling. Toxicology flags alerts. "
     "Synthesis plans routes. And Market Intel pulls live FDA adverse event data. "
     "Every agent's output feeds the next."),
    
    ("s3_demo", 20.0,
     "Let's run one. Sotorasib — Amgen's KRAS G12C inhibitor for lung cancer. "
     "One click, and the pipeline chains all agents. "
     "Chemistry pulled molecular weight 560, five rings, high complexity. "
     "FAERS shows over 2,000 adverse event reports. Diarrhea at 35 percent is the top signal. "
     "And IP flags Amgen's patent through 2038."),
    
    ("s4_pro", 36.0,
     "Pro unlocks the full chain. Compound comparison ranks candidates side-by-side. "
     "Batch mode handles 500 SMILES from a CSV. PDF export gives you team-ready reports."),
    
    ("s5_cli", 42.0,
     "For the command line: pip install pharmaclaw CLI. Nine agents in your terminal. "
     "LangGraph orchestration runs the full pipeline with conditional routing and consensus scoring."),
    
    ("s6_close", 50.0,
     "Free to start. Pro at 49 a month. PharmaClaw — real data, real chemistry, real results."),
]

async def generate_segment(name, text):
    """Generate a single TTS segment."""
    import edge_tts
    outfile = os.path.join(AUDIO_DIR, f"{name}.mp3")
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(outfile)
    
    # Get duration
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-show_entries", "format=duration", "-of", "json", outfile],
        capture_output=True, text=True
    )
    dur = json.loads(result.stdout)["format"]["duration"]
    print(f"  ✅ {name}: {float(dur):.1f}s → {outfile}")
    return outfile, float(dur)

async def main():
    print("Generating TTS segments...")
    segments_info = []
    for name, start, text in SEGMENTS:
        outfile, duration = await generate_segment(name, text)
        segments_info.append((name, start, duration, outfile))
    
    # Build ffmpeg filter to mix all audio segments at their start times
    print("\nMerging audio with video...")
    
    # First, create the combined audio track with proper timing
    filter_inputs = []
    filter_parts = []
    
    for i, (name, start, dur, path) in enumerate(segments_info):
        filter_inputs.extend(["-i", path])
        # Pad each segment with silence at the beginning to align it
        filter_parts.append(f"[{i+1}:a]adelay={int(start*1000)}|{int(start*1000)}[a{i}]")
    
    # Mix all delayed audio streams
    mix_inputs = "".join(f"[a{i}]" for i in range(len(segments_info)))
    filter_parts.append(f"{mix_inputs}amix=inputs={len(segments_info)}:normalize=0[aout]")
    
    filter_str = ";".join(filter_parts)
    
    cmd = [
        FFMPEG, "-y",
        "-i", VIDEO,  # input 0 = video
    ]
    # Add all audio inputs
    for _, _, _, path in segments_info:
        cmd.extend(["-i", path])
    
    cmd.extend([
        "-filter_complex", filter_str,
        "-map", "0:v",       # video from original
        "-map", "[aout]",    # mixed audio
        "-c:v", "copy",      # don't re-encode video
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        OUTPUT
    ])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        size = os.path.getsize(OUTPUT) / (1024*1024)
        # Get duration
        probe = subprocess.run(
            [FFPROBE, "-v", "quiet", "-show_entries", "format=duration", "-of", "json", OUTPUT],
            capture_output=True, text=True
        )
        dur = json.loads(probe.stdout)["format"]["duration"]
        print(f"\n✅ Final video: {OUTPUT}")
        print(f"   Duration: {float(dur):.1f}s | Size: {size:.1f} MB")
    else:
        print(f"❌ ffmpeg error:\n{result.stderr[-500:]}")

asyncio.run(main())
