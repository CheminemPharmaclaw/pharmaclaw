#!/usr/bin/env python3
"""
PharmaClaw Full YouTube Demo — Step 1: Generate all TTS narration.
Run this first, then run the recording passes.
"""
import asyncio, os, subprocess, json

FFMPEG = os.path.expanduser("~/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/bin/ffprobe")
WORKSPACE = "/home/democritus/.openclaw/workspace/pharmaclaw"
AUDIO_DIR = os.path.join(WORKSPACE, "full_demo_audio")
VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+5%"

os.makedirs(AUDIO_DIR, exist_ok=True)

SEGMENTS = [
    ("s1_hook",
     "What if you could go from a single molecule — to a full drug discovery report — "
     "chemistry, ADME, toxicology, synthesis, IP analysis, and market safety data — "
     "in under three minutes? "
     "This is PharmaClaw. Nine AI agents. One pipeline. Let me show you."),
    
    ("s2_pipeline",
     "PharmaClaw chains nine specialized agents. "
     "You feed it a SMILES string or a drug name. "
     "Chemistry Query hits PubChem and RDKit for molecular properties. "
     "Cheminformatics generates 3D conformers and pharmacophores. "
     "Pharmacology runs ADME profiling — Lipinski rules, BBB permeability, CYP inhibition. "
     "Toxicology flags structural alerts. "
     "Then Synthesis plans retrosynthesis routes. "
     "Catalyst Design recommends reaction conditions. "
     "Literature searches PubMed. "
     "IP checks freedom to operate. "
     "And Market Intel pulls live FDA adverse event data. "
     "Every agent's output feeds the next. That's the chain."),
    
    ("s3_demo_intro",
     "Let's run one live. "
     "I'll pick sotorasib — Amgen's KRAS G12C inhibitor, approved for lung cancer in 2021."),
    
    ("s3_demo_report",
     "The pipeline chains all agents. "
     "Chemistry Query pulled the compound from PubChem — molecular weight 560, LogP 4.0, "
     "five rings, high complexity. "
     "Retrosynthesis suggests a pyridopyrimidinone core with acryloyl piperazine coupling."),
    
    ("s3_demo_faers",
     "FAERS data — this is live FDA adverse event reporting — shows over two thousand reports since approval. "
     "Diarrhea at 35 percent is the top signal. Hepatotoxicity at 20 percent."),
    
    ("s3_demo_ip",
     "IP analysis flags the Amgen patent running through 2038. High freedom-to-operate risk. "
     "But it also suggests novel directions — deuterated analogs, acrylamide variants, "
     "combination strategies. "
     "That's a full drug intelligence report from one click."),
    
    ("s4_pro",
     "The Free tier gives you Chemistry Query and Pharmacology. Pro unlocks the full chain. "
     "Compound Comparison lets you rank two to five candidates side-by-side. "
     "Batch Mode processes up to 500 SMILES from a CSV. "
     "PDF Export generates color-coded reports with 2D structures — "
     "ready for your team meeting. "
     "And Watch Lists monitor FDA FAERS for new safety signals on your compounds automatically."),
    
    ("s5_cli",
     "If you prefer the command line — and let's be honest, most of us do — "
     "there's the PharmaClaw CLI. "
     "Pip install pharmaclaw-cli and you have all nine agents in your terminal. "
     "JSON in, JSON out. Pipe them together with standard Unix tools."),
    
    ("s5_langgraph",
     "The real power is LangGraph orchestration. "
     "Run pharmaclaw langgraph with a workflow flag. "
     "Full runs all nine agents with conditional routing. "
     "If toxicology flags something serious, it automatically reroutes to pharmacology "
     "for optimization suggestions. "
     "Consensus scoring rates the candidate zero to ten with specific warnings and recommendations. "
     "Sotorasib scored seven out of ten — viable with modifications. "
     "It flagged IP risk and CYP3A4 inhibition."),
    
    ("s6_case_intro",
     "Here's what happens when you ask PharmaClaw to design a novel lung cancer drug from scratch."),
    
    ("s6_case_faers",
     "The pipeline analyzed the EGFR inhibitor class, "
     "pulled real FAERS data — 29,000 adverse event reports for osimertinib — "
     "and identified the top two safety gaps: diarrhea and rash."),
    
    ("s6_case_compounds",
     "Then it designed three novel compounds targeting those gaps. "
     "PharmaClaw-2, the top pick, uses an N-methylpiperazine side chain to reduce GI toxicity. "
     "It passes Lipinski, has the best composite score, and is rated easy for synthesis."),
    
    ("s6_case_compare",
     "Head-to-head against approved drugs — gefitinib, erlotinib, afatinib, osimertinib — "
     "PharmaClaw-2 is competitive on every metric. "
     "Question to novel drug candidates. Three minutes. Under four cents in compute."),
    
    ("s7_close",
     "Free to start. Pro at 49 dollars a month — 29 if you're one of the first hundred. "
     "Enterprise for teams that need on-prem and custom agents. "
     "PharmaClaw. Nine agents. One pipeline. Real data, real chemistry, real results. "
     "Link in the description. Try it free on ClawHub."),
]

async def generate_all():
    import edge_tts
    results = []
    for name, text in SEGMENTS:
        outfile = os.path.join(AUDIO_DIR, f"{name}.mp3")
        comm = edge_tts.Communicate(text, VOICE, rate=RATE)
        await comm.save(outfile)
        r = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration", 
                           "-of", "csv=p=0", outfile], capture_output=True, text=True)
        dur = float(r.stdout.strip())
        results.append((name, dur, outfile))
        print(f"  🎙️ {name}: {dur:.1f}s")
    return results

print("=== Generating Full Narration ===")
segments = asyncio.run(generate_all())

# Generate silence gap
silence = os.path.join(AUDIO_DIR, "silence.mp3")
subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
               "-t", "0.6", "-c:a", "libmp3lame", silence], capture_output=True)

# Build concat file
concat_file = os.path.join(AUDIO_DIR, "concat.txt")
with open(concat_file, "w") as f:
    for i, (name, dur, path) in enumerate(segments):
        f.write(f"file '{path}'\n")
        if i < len(segments) - 1:
            f.write(f"file '{silence}'\n")

# Concat full audio
full_audio = os.path.join(WORKSPACE, "full_demo_audio.mp3")
subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
               "-c:a", "libmp3lame", "-q:a", "2", full_audio], capture_output=True)

r = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
                   "-of", "csv=p=0", full_audio], capture_output=True, text=True)
total_dur = float(r.stdout.strip())

print(f"\n✅ Full narration: {total_dur:.1f}s ({total_dur/60:.1f} min)")
print(f"   Saved: {full_audio}")

# Save segment timing for the recorder
import json as j
timing = []
offset = 0.0
for name, dur, path in segments:
    timing.append({"name": name, "start": round(offset, 2), "duration": round(dur, 2)})
    offset += dur + 0.6  # 0.6s silence gap
with open(os.path.join(WORKSPACE, "full_demo_timing.json"), "w") as f:
    j.dump(timing, f, indent=2)
print(f"   Timing: full_demo_timing.json")

# Print scene breakdown
print(f"\n=== Scene Breakdown ===")
scenes = {
    "Scene 1 — Hook": ["s1_hook"],
    "Scene 2 — Pipeline": ["s2_pipeline"],
    "Scene 3 — Live Demo": ["s3_demo_intro", "s3_demo_report", "s3_demo_faers", "s3_demo_ip"],
    "Scene 4 — Pro Features": ["s4_pro"],
    "Scene 5 — CLI": ["s5_cli", "s5_langgraph"],
    "Scene 6 — Case Study": ["s6_case_intro", "s6_case_faers", "s6_case_compounds", "s6_case_compare"],
    "Scene 7 — Close": ["s7_close"],
}
for scene_name, seg_names in scenes.items():
    scene_dur = sum(d for n, d, _ in segments if n in seg_names) + 0.6 * (len(seg_names) - 1)
    print(f"  {scene_name}: {scene_dur:.1f}s")
