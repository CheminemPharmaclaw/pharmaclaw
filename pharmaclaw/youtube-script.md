# PharmaClaw YouTube Video Script
## "AI Drug Discovery in Your Terminal — 8 Agents, One Pipeline"

**Target length:** 8–10 minutes
**Tone:** Confident, technical but accessible, a bit edgy. Think "indie dev shows Big Pharma how it's done."
**Audience:** Medicinal chemists, computational chemists, cheminformatics devs, AI/ML researchers, pharma startup founders

---

## INTRO (0:00 – 0:45)

**[Screen: pharmaclaw.com hero section]**

> What if you could run an entire drug discovery pipeline — from a single SMILES string to a scored, patent-checked, literature-backed drug candidate — in under 10 seconds?

> Not with a $500,000 Schrödinger license. Not with a team of 20. From your terminal.

> I'm going to show you PharmaClaw — 8 AI agents that chain together to do chemistry, pharmacology, toxicology, synthesis planning, catalyst design, literature mining, IP checks, and market intelligence. All open-source. All JSON. All composable.

> Let's go.

---

## THE PROBLEM (0:45 – 1:30)

**[Screen: scroll through pharmaclaw.com "Why PharmaClaw?" section]**

> Here's the reality in pharma right now. Tools like Schrödinger, ChemAxon, and Dotmatics cost $30K to $500K a year. They require specialized training. And they're siloed — your ADME tool doesn't talk to your retrosynthesis tool, which doesn't talk to your patent search.

> Researchers spend more time copying data between tools than actually doing science.

> PharmaClaw fixes that. One pipeline. Eight specialized agents. Everything talks to everything. And the free tier gives you 10 queries a day to prove it works.

**[Screen: briefly show the "Why PharmaClaw?" cards — Chemistry + Synthesis, Catalyst Design (NEW), ADME + Toxicology, Literature Mining (NEW), IP + Market Intel]**

---

## MEET THE TEAM (1:30 – 3:00)

**[Screen: pharmaclaw.com Pipeline section — show the horizontal agent flow]**

> Let me introduce the team. Eight agents, each a specialist.

**[Point to each agent in the pipeline visual as you mention them]**

> **Chemistry** 🧪 — Your starting point. Give it a SMILES string, it gives you molecular weight, LogP, TPSA, hydrogen bond donors and acceptors, aromatic rings. It also runs BRICS retrosynthesis to break your molecule into buyable precursors.

> **Pharmacology** 💊 — Full ADME profile. Lipinski Rule of Five, Veber rules, QED score, synthetic accessibility. Then it predicts BBB permeability, aqueous solubility, GI absorption, CYP3A4 inhibition risk, P-glycoprotein substrate likelihood, and plasma protein binding. Plus PAINS alerts.

> **Toxicology** ☠️ — Safety profiling. Lipinski and Veber violation counts, structural alerts, and an overall risk score: Low, Medium, or High.

> **Synthesis** 🔬 — Multi-step route planning using BRICS disconnections. It scores each route for feasibility — high, moderate, or challenging — based on step count and precursor complexity.

> **Catalyst Design** 🔧 — This one's unique. It recommends organometallic catalysts across 28 reaction types — Suzuki, Heck, Buchwald-Hartwig, metathesis, hydrogenation, you name it. Pd, Ru, Rh, Ir, Ni, Cu, Zr catalysts with conditions, loadings, and costs. And it designs novel ligand variants using steric, electronic, and bioisosteric modification strategies.

> **Literature Mining** 📚 — Searches PubMed and Semantic Scholar simultaneously. Returns papers with abstracts, DOIs, citation counts, and TLDR summaries. No API keys required.

> **IP Check** 💼 — Freedom-to-operate analysis. Computes Morgan fingerprint Tanimoto similarity against known drug patents. Tells you if your molecule is novel or if you're stepping on someone's IP. Suggests bioisosteric replacements to differentiate.

> **Market Intel** 📊 — Pulls real FDA FAERS adverse event data. How many reports? What are the top reactions? Yearly trends. This is live FDA data, not simulated.

---

## THE CLI (3:00 – 5:00)

**[Screen: pharmaclaw.com CLI section — the dark terminal demo]**

> Now here's where it gets interesting. Every agent is a terminal command.

**[Open a real terminal. Run commands live.]**

> Let's start simple. Molecular properties for aspirin:

```bash
pharmaclaw chemistry --smiles "CC(=O)Oc1ccccc1C(=O)O" --mode props
```

**[Show JSON output: MW, LogP, TPSA, etc.]**

> JSON output. Clean. Pipeable. Now let's check if it's safe:

```bash
pharmaclaw chemistry -s "CC(=O)Oc1ccccc1C(=O)O" | pharmaclaw toxicology
```

**[Show piped output with risk: "Low"]**

> See that? Chemistry output piped directly into toxicology. JSON in, JSON out. Any agent can talk to any other agent.

> Want a full ADME profile?

```bash
pharmaclaw pharmacology -s "CC(=O)Oc1ccccc1C(=O)O" --pretty
```

**[Show the full Lipinski, Veber, QED, ADME predictions output]**

> Lipinski pass, QED 0.55, moderate BBB permeability, high GI absorption, low CYP3A4 risk. All in one command.

> Need a catalyst for a Suzuki coupling?

```bash
pharmaclaw catalyst --reaction suzuki --scaffold PPh3 --strategy all
```

**[Show catalyst recommendation + ligand designs]**

> It recommends Pd(PPh3)4, gives you conditions — THF, 60-110°C, N2 atmosphere — and then designs novel ligand variants with steric and electronic modifications. Try getting that from ChatGPT.

---

## LANGGRAPH ORCHESTRATION (5:00 – 7:00)

**[Screen: pharmaclaw.com LangGraph section — show the flow diagram and scoring]**

> But the real power is orchestration. One command, all 8 agents, with smart routing.

**[Terminal: run the full pipeline]**

```bash
pharmaclaw langgraph \
  --smiles "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4" \
  --workflow full \
  --query "sotorasib KRAS G12C" \
  --drug sotorasib \
  --verbose
```

**[Show the pipeline running — each agent checking in]**

> Chemistry... Pharmacology... Toxicology... Synthesis... Catalyst... Literature... IP... Market Intel...

> And the result:

> **Score: 7.0 out of 10. GOOD — viable with modifications.**

> It found HIGH IP risk — because that SMILES *is* sotorasib, and it's already patented. It flagged CYP3A4 inhibition and low solubility. And it recommends bioisosteric modifications to create a novel derivative.

> This isn't a chatbot guessing. This is 8 specialized tools running real computations, checking real databases, and building consensus.

**[Screen: show the consensus scoring visual from the website — EXCELLENT / GOOD / FAIR / POOR]**

> The scoring factors in Lipinski violations, molecular weight, LogP, solubility, CYP3A4 risk, toxicology, synthesis feasibility, and IP risk. Everything weighted, everything transparent.

**[Briefly show different workflows]**

> And you don't always need all 8 agents. Quick screen — just chemistry and tox, 2 seconds. Safety focused — add pharmacology, 4 seconds. Synthesis focused — chemistry, synth, and catalyst. Pick what you need.

---

## THE CASE STUDY (7:00 – 8:30)

**[Screen: pharmaclaw.com Case Study section — "From Question to Novel Drug Candidates in 3 Minutes"]**

> Let me show you what happens when you ask PharmaClaw to create a novel lung cancer drug.

**[Walk through the case study on the website]**

> One prompt: "Create a novel lung cancer drug."

> The pipeline activates. All 9 stages. It analyzes real FDA FAERS data — 29,206 adverse event reports for osimertinib. Identifies diarrhea as the #1 safety concern with 6,134 reports. Rash as #2 with 3,667.

> Then it designs three novel compounds targeting those specific safety gaps.

**[Show the three compound cards]**

> PharmaClaw-1: chloroacetamide warhead to reduce skin toxicity. Lipinski pass, SA score 2.86.

> PharmaClaw-2: deuterated analog for metabolic stability. Targets the #1 adverse event — diarrhea.

> PharmaClaw-3: macrocyclic scaffold for selectivity. Completely different chemical space.

> Then it compares all three head-to-head with the reference drug. Tanimoto similarity, synthetic accessibility, novelty scores.

> Three minutes. Three novel candidates. Real data. No hallucinations.

---

## PRICING & GETTING STARTED (8:30 – 9:30)

**[Screen: pharmaclaw.com Pricing section]**

> Free tier: 10 queries a day. Chemistry, pharmacology, and toxicology. Enough to kick the tires.

> Pro: $49 a month. All 8 agents, unlimited queries, batch mode for up to 500 compounds, PDF reports, LangGraph orchestration. First 100 users lock in $29/month forever.

> Team: $199 a month for 5 seats. Shared workspace.

> Enterprise: custom pricing, on-prem, SSO, custom agents.

**[Terminal: show install]**

> Getting started:

```bash
pip install pharmaclaw-cli
pharmaclaw docs
```

> Or install individual agents from ClawHub:

```bash
clawhub install pharmaclaw-chemistry-query
```

> It's open-source. It runs on your machine. You bring your own LLM API key. No data leaves your environment unless you want it to.

---

## OUTRO (9:30 – 10:00)

**[Screen: pharmaclaw.com hero]**

> PharmaClaw. Eight agents. One terminal. Drug discovery that doesn't require a six-figure software license.

> If you're a medicinal chemist, a computational chemist, or anyone building in pharma AI — try it. Free tier, no credit card. Link in the description.

> And if you want to see me design a novel KRAS G12C inhibitor from scratch using this pipeline — subscribe and hit the bell. That's the next video.

> Thanks for watching. Go discover something.

---

## VIDEO DESCRIPTION (Copy-paste)

```
🧪 PharmaClaw — AI Drug Discovery Pipeline

8 AI agents for end-to-end drug discovery from your terminal:
• Chemistry (PubChem + RDKit)
• Pharmacology (ADME/PK profiling)
• Toxicology (safety alerts)
• Synthesis (retrosynthesis planning)
• Catalyst Design (28 reaction types)
• Literature Mining (PubMed + Semantic Scholar)
• IP Check (FTO + bioisosteres)
• Market Intel (FDA FAERS data)

🔗 LangGraph orchestration — dynamic routing, consensus scoring, self-correction

Try it free:
🌐 Website: https://pharmaclaw.com
📦 Install: pip install pharmaclaw-cli
🔧 ClawHub: https://clawhub.ai/Cheminem/pharmaclaw-chemistry-query
💻 GitHub: https://github.com/Cheminem/pharmaclaw

Built on OpenClaw: https://openclaw.ai

#DrugDiscovery #AI #Cheminformatics #Pharma #OpenSource #CLI #LangGraph
```

---

## PRODUCTION NOTES

**Screen recordings needed:**
1. pharmaclaw.com full scroll-through (hero → about → pipeline → demo → pro → CLI → case study → pricing)
2. Terminal session: individual agent commands (chemistry, pharmacology, toxicology, catalyst)
3. Terminal session: piping demo (chemistry | toxicology)
4. Terminal session: full LangGraph pipeline with --verbose
5. Terminal session: pip install + docs command

**Thumbnails ideas:**
- Split screen: terminal on left, molecule structure on right, "8 AI Agents" text
- Dark terminal background with green text showing "Score: 7.0/10 — GOOD"
- "Drug Discovery for $0" with PharmaClaw logo

**Music:** Lo-fi electronic or minimal synth. Nothing too aggressive. Think "hacker in a lab coat."

**Pacing:** Keep it fast. Cut dead air. Show real output, not slides. If you can screen-record the actual commands running live, that's gold.
