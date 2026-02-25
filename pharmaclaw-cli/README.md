# 🧪 PharmaClaw CLI v1.0.0

**Drug discovery at your fingertips.** Unified command-line interface for the PharmaClaw agent team — 8 specialized agents, 4 orchestration workflows, JSON-native for human and AI use.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Website](https://img.shields.io/badge/web-pharmaclaw.com-purple.svg)](https://pharmaclaw.com)
[![ClawHub](https://img.shields.io/badge/skills-clawhub.com-orange.svg)](https://clawhub.com)

---

## Table of Contents

- [Install](#install)
- [Quick Start](#quick-start)
- [Agents](#agents)
  - [Chemistry 🧪](#chemistry-)
  - [Pharmacology 💊](#pharmacology-)
  - [Toxicology ☠️](#toxicology-)
  - [Synthesis 🔬](#synthesis-)
  - [Catalyst Design 🔧](#catalyst-design-)
  - [Literature Mining 📚](#literature-mining-)
  - [IP Check 💼](#ip-check-)
  - [Market Intel 📊](#market-intel-)
- [LangGraph Orchestration](#langgraph-orchestration-)
- [Agent Chaining (Piping)](#agent-chaining-piping)
- [Utility Commands](#utility-commands)
- [For AI Agents](#for-ai-agents)
- [Tiers & Rate Limits](#tiers--rate-limits)
- [Configuration](#configuration)
- [Requirements](#requirements)

---

## Install

```bash
# From PyPI
pip install pharmaclaw-cli

# From source
cd pharmaclaw-cli && pip install -e .

# Verify
pharmaclaw --version
```

**Dependencies:** Python 3.10+, RDKit, click, pubchempy, requests, langchain, langgraph

---

## Quick Start

```bash
# What is this molecule?
pharmaclaw chemistry --smiles "CC(=O)Oc1ccccc1C(=O)O" --mode props

# Is it safe?
pharmaclaw toxicology --smiles "CC(=O)Oc1ccccc1C(=O)O"

# Run the full 8-agent pipeline with a score
pharmaclaw langgraph --smiles "CC(=O)Oc1ccccc1C(=O)O" --workflow full --verbose
```

---

## Agents

### Chemistry 🧪

Molecular properties, retrosynthesis, PubChem queries, fingerprints, reactions, visualization.

```bash
# Molecular properties (MW, LogP, TPSA, HBD, HBA, rotatable bonds, aromatic rings)
pharmaclaw chemistry --smiles "CC(=O)Oc1ccccc1C(=O)O" --mode props

# BRICS retrosynthesis — break a molecule into precursors
pharmaclaw chemistry --smiles "CC(=O)Oc1ccccc1C(=O)O" --mode retro --depth 2

# Multi-step synthesis plan
pharmaclaw chemistry --smiles "CC(=O)Oc1ccccc1C(=O)O" --mode plan --steps 3

# Morgan fingerprint
pharmaclaw chemistry --smiles "CCO" --mode fingerprint

# Tanimoto similarity between molecules
pharmaclaw chemistry --smiles "CCO" --mode similarity --target-smiles "CCCO,CCCCO"

# 2D structure visualization (SVG or PNG)
pharmaclaw chemistry --smiles "c1ccccc1" --mode viz --format svg --output benzene.svg

# PubChem compound lookup
pharmaclaw chemistry --compound "aspirin" --mode pubchem --query-type info

# PubChem similar compounds
pharmaclaw chemistry --compound "ibuprofen" --mode pubchem --query-type similar

# Forward reaction simulation
pharmaclaw chemistry --mode reaction --template suzuki --reactants "c1ccccc1Br,c1ccccc1B(O)O"
```

**Output example (props):**
```json
{
  "agent": "chemistry",
  "command": "props",
  "smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "mw": 180.042259,
  "logp": 1.3101,
  "tpsa": 63.6,
  "hbd": 1,
  "hba": 4,
  "rotb": 3,
  "arom_rings": 1
}
```

| Option | Description |
|--------|-------------|
| `--smiles, -s` | SMILES string |
| `--mode, -m` | `props` `retro` `plan` `viz` `fingerprint` `similarity` `pubchem` `reaction` |
| `--depth` | Retrosynthesis depth (default: 1) |
| `--steps` | Synthesis plan steps (default: 3) |
| `--compound` | Compound name for PubChem |
| `--query-type` | PubChem: `info` `structure` `synthesis` `similar` |
| `--target-smiles` | Comma-separated SMILES for similarity |
| `--template` | Reaction template: `amide` `ester` `suzuki` |
| `--output, -o` | Output file for viz |
| `--format` | `png` or `svg` (default: svg) |

---

### Pharmacology 💊

Full ADME/PK profiling: Lipinski Rule of Five, Veber rules, QED, SA Score, BBB permeability, aqueous solubility, GI absorption, CYP3A4 inhibition, P-glycoprotein substrate prediction, plasma protein binding, PAINS alerts.

```bash
# Full ADME profile
pharmaclaw pharmacology --smiles "CC(=O)Oc1ccccc1C(=O)O"

# Pretty-printed output
pharmaclaw pharmacology --smiles "CC(=O)Oc1ccccc1C(=O)O" --pretty
```

**Output includes:**
```json
{
  "agent": "pharmacology",
  "report": {
    "descriptors": { "mw": 180.04, "logp": 1.31, "tpsa": 63.6, "hbd": 1, "hba": 4 },
    "lipinski": { "pass": true, "violations": 0 },
    "veber": { "pass": true },
    "qed": 0.5506,
    "sa_score": 1.61,
    "adme": {
      "bbb": { "prediction": "moderate" },
      "solubility": { "logS_estimate": -2.16, "class": "moderate" },
      "gi_absorption": { "prediction": "high" },
      "cyp3a4_inhibition": { "risk": "low" },
      "pgp_substrate": { "prediction": "unlikely" },
      "plasma_protein_binding": { "prediction": "moderate-low" }
    },
    "pains": { "alert": false }
  },
  "risks": [],
  "recommend_next": ["toxicology", "ip-expansion"]
}
```

| Option | Description |
|--------|-------------|
| `--smiles, -s` | SMILES string (required) |
| `--pretty` | Pretty-print JSON |

---

### Toxicology ☠️

Safety profiling with Lipinski/Veber violation counts, QED, PAINS structural alerts, and overall risk scoring.

```bash
# Toxicology assessment
pharmaclaw toxicology --smiles "c1ccccc1"

# Assess a drug candidate
pharmaclaw toxicology --smiles "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4"
```

**Output example:**
```json
{
  "agent": "toxicology",
  "lipinski_viol": 0,
  "veber_viol": 0,
  "qed": 0.594,
  "pains": 0,
  "risk": "Low",
  "props": {
    "mw": 424.8, "logp": 3.99, "tpsa": 75.4,
    "hbd": 1, "hba": 6, "rotb": 4, "rings": 4, "arom": 2
  }
}
```

| Risk Level | Meaning |
|------------|---------|
| **Low** | No Lipinski violations, no PAINS alerts |
| **Medium/High** | Lipinski violations and/or PAINS structural alerts detected |

---

### Synthesis 🔬

Multi-step retrosynthesis route planning with BRICS disconnections and feasibility scoring.

```bash
# Plan a 3-step synthesis
pharmaclaw synthesis --smiles "CC(=O)Oc1ccccc1C(=O)O" --steps 3

# Deeper retrosynthesis
pharmaclaw synthesis --smiles "CC1=NN(C(=O)C1)C2CC2" --steps 5 --depth 3
```

**Output includes:**
```json
{
  "agent": "synthesis",
  "route": [
    {
      "step": 1,
      "precursors": ["CC(=O)O", "Oc1ccccc1C(=O)O"],
      "cond": "BRICS template (ester/amide/etc disconnects)",
      "product": "CC(=O)Oc1ccccc1C(=O)O"
    }
  ],
  "feasibility": {
    "score": "high",
    "confidence": 0.75,
    "steps": 1,
    "total_precursors": 2,
    "note": "BRICS-based disconnection; real yields require experimental validation"
  }
}
```

| Feasibility | Criteria |
|-------------|----------|
| **high** | ≤3 steps, ≤10 precursors |
| **moderate** | ≤5 steps |
| **challenging** | >5 steps |

---

### Catalyst Design 🔧

Organometallic catalyst recommendation for 28 reaction types + novel ligand design with RDKit optimization.

```bash
# Recommend catalysts for a Suzuki coupling
pharmaclaw catalyst --reaction suzuki

# With substrate constraint
pharmaclaw catalyst --reaction buchwald_hartwig --substrate "ClC1=CC=CC=C1"

# Enantioselective preference
pharmaclaw catalyst --reaction hydrogenation --enantioselective

# Design novel ligand variants from a scaffold
pharmaclaw catalyst --scaffold PPh3 --strategy all

# Specific modification strategy
pharmaclaw catalyst --scaffold NHC_IMes --strategy electronic

# Both: recommend catalyst AND design ligands
pharmaclaw catalyst --reaction suzuki --scaffold PPh3 --strategy steric
```

**Supported reaction types:**
`suzuki`, `heck`, `sonogashira`, `negishi`, `kumada`, `stille`, `buchwald_hartwig`, `c_n_coupling`, `olefin_metathesis`, `ring_closing_metathesis`, `hydrogenation`, `asymmetric_hydrogenation`, `click_CuAAC`, `carbonylation`, `borylation`, and 13 more.

**Supported scaffolds:**
`PPh3`, `PCy3`, `dppe`, `dppp`, `NHC_IMes`, `NHC_IPr` (or any SMILES)

**Ligand design strategies:**
| Strategy | What it does |
|----------|-------------|
| `steric` | Add ortho-methyl, iPr, tBu, cyclohexyl, adamantyl for cone angle tuning |
| `electronic` | Add para-CF3, OMe, NMe2, F, NO2 for σ-donor/acceptor tuning |
| `bioisosteric` | P→As, P→N, phosphine→NHC, phenyl→pyridyl/thienyl |
| `all` | All of the above |

---

### Literature Mining 📚

Search PubMed and Semantic Scholar for papers with abstracts, DOIs, citations, and TLDR summaries.

```bash
# Search PubMed
pharmaclaw literature --query "KRAS G12C inhibitors 2026" --source pubmed

# Search Semantic Scholar (better for ML/AI papers)
pharmaclaw literature --query "graph neural networks drug discovery" --source scholar

# Search both (default)
pharmaclaw literature --query "sotorasib clinical trials" --max-results 10

# Recent papers only (last 3 years)
pharmaclaw literature --query "PROTAC degraders" --years 3
```

| Option | Description |
|--------|-------------|
| `--query, -q` | Search query (required) |
| `--source` | `pubmed`, `scholar`, or `both` (default: both) |
| `--max-results` | Number of papers (default: 10, max: 50) |
| `--years` | Limit to recent N years |

---

### IP Check 💼

Freedom-to-Operate analysis using Morgan fingerprint Tanimoto similarity against known drug patents, plus bioisostere suggestions for IP differentiation.

```bash
# FTO analysis against reference patents
pharmaclaw ip --smiles "CCO" --threshold 0.85

# Include bioisostere suggestions
pharmaclaw ip --smiles "CC1=NN(C(=O)C1)C2CC2" --bioisosteres

# Compare against specific molecules
pharmaclaw ip --smiles "CCO" --compare "CCCO,CCCCO,c1ccccc1O"

# Lower threshold for stricter analysis
pharmaclaw ip --smiles "CCO" --threshold 0.65
```

**Output example:**
```json
{
  "agent": "ip",
  "overall_risk": "LOW",
  "max_similarity": 0.0698,
  "comparisons": [
    { "reference_smiles": "...", "tanimoto": 0.0698, "risk": "LOW" }
  ],
  "recommendation": "LOW RISK: Tanimoto 0.070. Novel chemical space. Proceed with patent filing."
}
```

| Risk Level | Tanimoto | Recommendation |
|------------|----------|----------------|
| **LOW** | <0.50 | Novel space — proceed with filing |
| **MODERATE** | 0.50–0.85 | Consider additional differentiation |
| **HIGH** | ≥0.85 | Structural modifications required before filing |

---

### Market Intel 📊

FDA FAERS (Adverse Event Reporting System) data, market trends, and optional prediction market integration.

```bash
# FAERS adverse events for a drug
pharmaclaw market --drug sotorasib

# By SMILES (auto-resolves via PubChem)
pharmaclaw market --drug "CC(=O)Oc1ccccc1C(=O)O"

# Include prediction market data (requires Polymarket CLI)
pharmaclaw market --drug sotorasib --include-preds

# Limit events returned
pharmaclaw market --drug ibuprofen --limit 50
```

| Option | Description |
|--------|-------------|
| `--drug, -d` | Drug name or SMILES (required) |
| `--limit` | Max events to return (default: 20) |
| `--include-preds` | Include prediction market data |

---

## LangGraph Orchestration 🔗

Stateful multi-agent pipelines powered by LangGraph with dynamic routing, self-correction, and consensus scoring.

```bash
# Full pipeline — all 8 agents with conditional routing
pharmaclaw langgraph --smiles "CC(=O)Oc1ccccc1C(=O)O" --workflow full --verbose

# Quick screen — chemistry + toxicology only
pharmaclaw langgraph --smiles "CCO" --workflow quick

# Safety-focused — chemistry + pharmacology + toxicology
pharmaclaw langgraph --smiles "CCO" --workflow safety

# Synthesis-focused — chemistry + synthesis + catalyst
pharmaclaw langgraph --smiles "CCO" --workflow synthesis

# Full with literature + market intel
pharmaclaw langgraph \
  --smiles "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4" \
  --workflow full \
  --query "sotorasib KRAS G12C" \
  --drug sotorasib \
  --verbose --pretty
```

### Workflows

| Workflow | Agents | Use Case | Speed |
|----------|--------|----------|-------|
| **`full`** | All 8 + conditional routing | Complete drug candidate evaluation | ~10s |
| **`quick`** | Chemistry → Toxicology | Fast screening of many compounds | ~2s |
| **`safety`** | Chemistry → Pharmacology → Toxicology | Safety-focused profiling | ~4s |
| **`synthesis`** | Chemistry → Synthesis → Catalyst | Route planning & catalyst selection | ~5s |

### How It Works

```
                    ┌─────────────┐
                    │  Chemistry  │ props + retrosynthesis
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │Pharmacology │ ADME/PK/PAINS
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                ┌───│ Toxicology  │ risk assessment
                │   └──────┬──────┘
     HIGH tox?  │          │ LOW tox
     reroute    │          │
         ┌──────▼──────┐   │
         │Pharmacology │   │  (derivative suggestions)
         │ (retry)     │   │
         └──────┬──────┘   │
                └──────┬───┘
                ┌──────▼──────┐
                │  Synthesis  │ route planning
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │  Catalyst   │ catalyst + ligand design
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │ Literature  │ PubMed papers
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │   IP Check  │ FTO + bioisosteres
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │ Market Intel│ FAERS (if --drug given)
                └──────┬──────┘
                       │
                ┌──────▼──────┐
                │  Consensus  │ score 0-10 + verdict
                └─────────────┘
```

### Consensus Scoring

The pipeline produces a **0–10 score** with verdict and actionable recommendations:

| Score | Verdict |
|-------|---------|
| 8–10 | **EXCELLENT** — strong drug candidate |
| 6–7.9 | **GOOD** — viable with modifications |
| 4–5.9 | **FAIR** — significant improvements needed |
| 0–3.9 | **POOR** — major concerns, consider alternative scaffolds |

**Scoring factors:** Lipinski violations, MW, LogP, solubility, CYP3A4 risk, tox risk, synthesis feasibility, IP risk.

**Example output (sotorasib):**
```json
{
  "consensus": {
    "score": 7.0,
    "verdict": "GOOD — viable with modifications",
    "warnings": ["HIGH IP risk — apply bioisosteric modifications"],
    "recommendations": [
      "Consider prodrug or salt form for solubility",
      "CYP3A4 inhibition risk — check DDI potential",
      "Use bioisostere suggestions to generate novel derivatives"
    ],
    "agents_consulted": ["chemistry","pharmacology","toxicology","synthesis","catalyst","literature","ip","market"]
  }
}
```

---

## Agent Chaining (Piping)

All commands output JSON to stdout. Pipe between any agents:

```bash
# Chemistry → Toxicology
pharmaclaw chemistry -s "CCO" | pharmaclaw toxicology

# Chemistry → IP Check
pharmaclaw chemistry -s "CCO" | pharmaclaw ip

# Chemistry → Pharmacology
pharmaclaw chemistry -s "CCO" | pharmaclaw pharmacology
```

When piping, the downstream agent reads the `smiles` field from the upstream JSON automatically. No extra flags needed.

---

## Utility Commands

### Compare ⚖️ — Side-by-side compound analysis

```bash
# Compare 2-10 compounds (chemistry + toxicology for each)
pharmaclaw compare --smiles "CCO,CCCO,c1ccccc1O"
```

### Report 📄 — Full pipeline to file

```bash
# Run 6 agents and save to JSON
pharmaclaw report --smiles "CC(=O)Oc1ccccc1C(=O)O" --output aspirin_report.json
```

### Batch 📦 — CSV batch processing

```bash
# Process up to 500 compounds from CSV
pharmaclaw batch --file compounds.csv --agents chemistry,toxicology,pharmacology --output results.json
```

CSV must have a column named `smiles`, `SMILES`, or `Smiles`.

### Config ⚙️ — Manage API key and tier

```bash
# Show current config
pharmaclaw config --show

# Set tier and API key
pharmaclaw config --tier pro --set-key YOUR_API_KEY
```

### Docs 📖 — Built-in documentation

```bash
pharmaclaw docs
```

---

## For AI Agents

PharmaClaw CLI is designed for **agent-to-agent** use. Every command:

- Outputs **structured JSON** to stdout
- Sends errors to stderr
- Returns **non-zero exit codes** on failure
- Supports **stdin piping** (reads `smiles` from upstream JSON)

### Calling from Python

```python
import subprocess, json

result = subprocess.run(
    ["pharmaclaw", "chemistry", "-s", "CCO", "--mode", "props"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
print(data["mw"])  # 46.0684
```

### Calling from Bash / Shell Scripts

```bash
# Get MW and pipe to jq
pharmaclaw chemistry -s "CCO" | jq '.mw'

# Chain agents in a one-liner
pharmaclaw chemistry -s "CCO" | pharmaclaw toxicology | jq '.risk'
```

### Calling from LangChain / LangGraph

```python
from pharmaclaw_cli.orchestration.tools import chemistry_props, toxicology_analyze

# As LangChain tools
result = chemistry_props.invoke({"smiles": "CCO"})
tox = toxicology_analyze.invoke({"smiles": "CCO"})
```

### Calling from Other AI Frameworks

Any agent framework that can run shell commands can use PharmaClaw:

```
Input:  pharmaclaw langgraph --smiles "SMILES_HERE" --workflow quick
Output: JSON with score, verdict, warnings, recommendations
```

---

## Tiers & Rate Limits

| Tier | Price | Queries/Day | Access |
|------|-------|-------------|--------|
| **Free** | $0 | 10 | Chemistry, Pharmacology, Toxicology |
| **Pro** | $49/mo | Unlimited | All 8 agents + chaining + batch + LangGraph |
| **Team** | $199/mo | Unlimited | + shared workspace, admin dashboard |
| **Enterprise** | Custom | Unlimited | + on-prem, SSO/SAML, custom agents |

Rate limits are tracked locally at `~/.pharmaclaw/usage.json` and reset daily (UTC).

---

## Configuration

Config is stored at `~/.pharmaclaw/config.json`:

```json
{
  "tier": "free",
  "api_key": null
}
```

Usage tracking at `~/.pharmaclaw/usage.json`:

```json
{
  "date": "2026-02-25",
  "count": 3
}
```

---

## Requirements

| Package | Purpose |
|---------|---------|
| Python 3.10+ | Runtime |
| [RDKit](https://www.rdkit.org/) | Cheminformatics (props, retro, fingerprints) |
| [click](https://click.palletsprojects.com/) | CLI framework |
| [pubchempy](https://pubchempy.readthedocs.io/) | PubChem API queries |
| [requests](https://requests.readthedocs.io/) | HTTP for PubMed, FAERS, Semantic Scholar |
| [langchain](https://python.langchain.com/) | Tool wrappers for LangGraph |
| [langgraph](https://langchain-ai.github.io/langgraph/) | Stateful agent orchestration |

---

## Project Structure

```
pharmaclaw-cli/
├── pharmaclaw_cli.py          # Main CLI entrypoint (click)
├── agents/                    # Agent wrappers (subprocess → JSON)
│   ├── chemistry.py
│   ├── pharmacology.py
│   ├── toxicology.py
│   ├── synthesis.py
│   ├── catalyst.py
│   ├── literature.py
│   ├── ip_check.py
│   └── market.py
├── orchestration/             # LangGraph multi-agent pipelines
│   ├── cheminem_orchestrator.py   # StateGraph workflows
│   └── tools.py                   # 13 LangChain @tool wrappers
├── utils/
│   ├── auth.py                # Tier-based rate limiting
│   ├── validators.py          # SMILES validation
│   └── piping.py              # JSON stdin/stdout helpers
├── tests/
│   ├── test_cli.py            # 9 CLI tests
│   └── test_langgraph.py      # 5 LangGraph tests
├── setup.py                   # pip install pharmaclaw-cli
└── README.md                  # This file
```

---

## Links

- **Website:** [pharmaclaw.com](https://pharmaclaw.com)
- **ClawHub Skills:** [clawhub.com](https://clawhub.com)
- **Support:** cheminem602@gmail.com
- **OpenClaw:** [openclaw.ai](https://openclaw.ai)

---

*Built by the PharmaClaw team. Save lives through novel drug discoveries.* 🧬
