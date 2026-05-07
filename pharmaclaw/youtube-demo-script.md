# PharmaClaw YouTube Demo Script
**Target Length:** 4–5 minutes  
**Tone:** Confident, no-hype, let the product speak  
**Audience:** Med chemists, pharma researchers, AI-curious scientists, VCs  

---

## SCENE 1 — The Hook (0:00–0:25)
**[Screen: pharmaclaw.com hero section]**

> **NARRATION:**  
> "What if you could go from a single molecule to a full drug discovery report — chemistry, ADME, toxicology, synthesis, IP analysis, and market safety data — in under 3 minutes?"
>
> "This is PharmaClaw. 9 AI agents. One pipeline. Let me show you."

**[Action: Slow scroll down past the hero to reveal the pipeline visual]**

---

## SCENE 2 — The Pipeline (0:25–0:55)
**[Screen: Pipeline section — the 9-agent chain visual]**

> **NARRATION:**  
> "PharmaClaw chains 9 specialized agents. You feed it a SMILES string or a drug name. Chemistry Query hits PubChem and RDKit for molecular properties. Cheminformatics generates 3D conformers and pharmacophores. Pharmacology runs ADME profiling — Lipinski, BBB permeability, CYP inhibition. Toxicology flags structural alerts."
>
> "Then it gets interesting — Synthesis plans retrosynthesis routes, Catalyst Design recommends reaction conditions, Literature searches PubMed, IP checks freedom-to-operate, and Market Intel pulls live FDA adverse event data."
>
> "Every agent's output feeds the next. That's the chain."

**[Action: Hover over each agent icon as it's mentioned]**

---

## SCENE 3 — Live Demo (0:55–2:15)
**[Screen: Scroll down to Demo section]**

> **NARRATION:**  
> "Let's run one. I'll pick sotorasib — Amgen's KRAS G12C inhibitor, approved for lung cancer in 2021."

**[Action: Click "Sotorasib" button → Click "Generate Report"]**

> **NARRATION (while loading):**  
> "The pipeline is chaining all agents now — chemistry, cheminformatics, pharmacology, toxicology, synthesis, IP, and market intel."

**[Action: Report appears after ~3.5s]**

> **NARRATION:**  
> "Here's the full report. Chemistry Query pulled the compound from PubChem — molecular weight 560, LogP 4.0, five rings, high complexity. Retrosynthesis suggests a pyridopyrimidinone core with acryloyl piperazine coupling."
>
> "FAERS data — this is live FDA adverse event reporting — shows 2,000+ reports since approval. Diarrhea at 35% is the top signal, hepatotoxicity at 20%."
>
> "And IP analysis flags the Amgen patent running through 2038. High FTO risk. But it also suggests novel directions — deuterated analogs, acrylamide variants, combination strategies."
>
> "That's a full drug intelligence report from one click."

**[Action: Scroll through the report slowly]**

---

## SCENE 4 — Pro Features (2:15–2:50)
**[Screen: Scroll to Pro Features section]**

> **NARRATION:**  
> "Free tier gives you Chemistry Query and Pharmacology. Pro unlocks the full chain."
>
> "Compound Comparison lets you rank 2 to 5 candidates side-by-side. Batch Mode processes up to 500 SMILES from a CSV. PDF Export generates color-coded reports with 2D structures — ready for your team meeting."
>
> "And Watch Lists monitor FDA FAERS for new safety signals on your compounds automatically."

**[Action: Scroll through the pro feature cards, pause on the comparison table]**

---

## SCENE 5 — The CLI (2:50–3:30)
**[Screen: Scroll to CLI section — the terminal mockup]**

> **NARRATION:**  
> "If you prefer the command line — and let's be honest, most of us do — there's the PharmaClaw CLI."
>
> "`pip install pharmaclaw-cli` and you have all 9 agents in your terminal. JSON in, JSON out. Pipe them together with standard Unix tools."
>
> "The real power is LangGraph orchestration. Run `pharmaclaw langgraph` with a workflow flag — full runs all 9 agents with conditional routing. If toxicology flags something serious, it automatically reroutes to pharmacology for optimization suggestions."
>
> "Consensus scoring rates the candidate 0 to 10 with specific warnings and recommendations. Sotorasib scored 7 out of 10 — 'viable with modifications.' Flagged IP risk and CYP3A4 inhibition."

**[Action: Highlight the terminal demo, then scroll to LangGraph features and scoring grid]**

---

## SCENE 6 — Case Study (3:30–4:15)
**[Screen: Scroll to Case Study section]**

> **NARRATION:**  
> "Here's what happens when you ask PharmaClaw to design a novel lung cancer drug from scratch."
>
> "The pipeline analyzed the EGFR inhibitor class, pulled real FAERS data — 29,000 adverse event reports for osimertinib — and identified the top two safety gaps: diarrhea and rash."
>
> "Then it designed three novel compounds targeting those gaps. PharmaClaw-2, the top pick, uses an N-methylpiperazine side chain to reduce GI toxicity. It passes Lipinski, has the best composite score, and is rated 'easy' for synthesis."
>
> "Head-to-head against approved drugs — gefitinib, erlotinib, afatinib, osimertinib — PharmaClaw-2 is competitive on every metric."
>
> "Question to novel drug candidates. Three minutes. Under 4 cents in compute."

**[Action: Scroll through case study steps — FAERS data, 3 compound cards, comparison table, recommendation]**

---

## SCENE 7 — Close (4:15–4:40)
**[Screen: Scroll to Pricing, then back to hero]**

> **NARRATION:**  
> "Free to start. Pro at $49 a month — $29 if you're one of the first 100. Enterprise for teams that need on-prem and custom agents."
>
> "PharmaClaw. 9 agents. One pipeline. Real data, real chemistry, real results."
>
> "Link in the description. Try it free on ClawHub."

**[Action: End on hero section with the "Live Demo" and "Freemium Install" buttons visible]**

---

## PRODUCTION NOTES

### Visual Style
- Clean browser recording, no facecam
- Smooth scrolling between sections (not teleporting)
- Pause 1–2 seconds on key visuals (pipeline, report data, comparison table)
- Consider subtle zoom on important details (FAERS numbers, compound cards)

### Music
- Optional: Low ambient/electronic background, very subtle
- Or: No music, just narration (more professional for pharma audience)

### Thumbnail Ideas
- "9 AI Agents → 1 Drug Report" with pipeline visual
- Sotorasib structure + "3 Minutes to Drug Discovery"
- Terminal + molecule overlay — "PharmaClaw CLI"

### CTA / Description
- Link to pharmaclaw.com
- Link to ClawHub install
- "Try the demo yourself — click any drug on pharmaclaw.com"
- Mention founding member pricing

### Timing Budget
| Scene | Duration | Cumulative |
|-------|----------|------------|
| Hook | 25s | 0:25 |
| Pipeline | 30s | 0:55 |
| Live Demo | 80s | 2:15 |
| Pro Features | 35s | 2:50 |
| CLI | 40s | 3:30 |
| Case Study | 45s | 4:15 |
| Close | 25s | 4:40 |
