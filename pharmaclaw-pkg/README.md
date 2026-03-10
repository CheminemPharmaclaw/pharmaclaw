# PharmaClaw 🧪

**AI-powered drug discovery pipeline — 9 chained agents for end-to-end molecular analysis.**

[![PyPI](https://img.shields.io/pypi/v/pharmaclaw)](https://pypi.org/project/pharmaclaw/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)

## Install

```bash
pip install pharmaclaw
```

**With optional dependencies:**
```bash
pip install pharmaclaw[all]       # Everything
pip install pharmaclaw[pubchem]   # PubChem name resolution
pip install pharmaclaw[reports]   # PDF reports & plots
```

> **Note:** Requires RDKit. If `pip install rdkit` doesn't work for your platform, install via conda: `conda install -c conda-forge rdkit`

## Quick Start — Python API

```python
from pharmaclaw import chemistry, pharmacology, toxicology

# Molecular properties
props = chemistry.get_props("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
print(f"MW: {props['mw']}, LogP: {props['logp']}")

# ADME/PK profile
profile = pharmacology.profile("CC(=O)Oc1ccccc1C(=O)O")
print(f"Lipinski pass: {profile['report']['lipinski']['pass']}")
print(f"QED: {profile['report']['qed']}")

# Toxicology
tox = toxicology.analyze("CC(=O)Oc1ccccc1C(=O)O")
print(f"Risk: {tox['risk']}")
```

## Quick Start — CLI

```bash
# Molecular properties
pharmaclaw chemistry -s "CC(=O)Oc1ccccc1C(=O)O" --mode props --pretty

# Full ADME profile
pharmaclaw pharmacology -s "CC(=O)Oc1ccccc1C(=O)O" --pretty

# Retrosynthesis
pharmaclaw chemistry -s "CC(=O)Oc1ccccc1C(=O)O" --mode retro --depth 2

# Toxicology
pharmaclaw toxicology -s "c1ccccc1" --pretty

# 3D conformers
pharmaclaw cheminformatics -s "CCO" --mode conformers --num-confs 5

# Catalyst design
pharmaclaw catalyst --reaction suzuki --scaffold PPh3

# Literature search
pharmaclaw literature -q "KRAS G12C inhibitors" --source pubmed

# IP/FTO analysis
pharmaclaw ip -s "CCO" --bioisosteres --pretty

# FAERS adverse events
pharmaclaw market -d sotorasib --pretty

# Full pipeline (all agents)
pharmaclaw orchestrate -s "CC(=O)Oc1ccccc1C(=O)O" --pretty
```

## Agent Chaining (Piping)

All CLI commands output JSON. Pipe between agents:

```bash
pharmaclaw chemistry -s "CCO" | pharmaclaw toxicology
pharmaclaw chemistry -s "CCO" | pharmaclaw ip
```

## The 9 Agents

| Agent | What it does |
|-------|-------------|
| 🧪 **Chemistry** | Molecular properties, retrosynthesis (BRICS), fingerprints, similarity, scaffolds, MCS, PubChem queries |
| 🧬 **Cheminformatics** | 3D conformer generation (ETKDG+MMFF), RECAP fragmentation, stereoisomer enumeration, format conversion |
| 💊 **Pharmacology** | ADME/PK profiling — Lipinski, Veber, QED, SA Score, BBB, solubility, CYP3A4, P-gp, PAINS |
| ☠️ **Toxicology** | Safety profiling, structural alerts, PAINS detection, risk scoring |
| 🔬 **Synthesis** | Multi-step retrosynthetic route planning with feasibility scoring |
| 🔧 **Catalyst** | Organometallic catalyst recommendation (12 catalysts, 28 reaction types) + novel ligand design |
| 📚 **Literature** | PubMed + Semantic Scholar search with TLDRs and citation counts |
| 💼 **IP Check** | Freedom-to-Operate (FTO) via Tanimoto similarity + bioisostere suggestions |
| 📊 **Market Intel** | FDA FAERS adverse event queries, reaction trends, yearly counts |

## Python API Reference

Every agent is importable:

```python
from pharmaclaw import chemistry, pharmacology, toxicology, synthesis
from pharmaclaw import catalyst, literature, ip_check, market, cheminformatics

# Chemistry
chemistry.get_props(smiles)
chemistry.get_retro(smiles, depth=2)
chemistry.get_plan(smiles, steps=3)
chemistry.get_fingerprint(smiles)
chemistry.get_similarity(query, targets)
chemistry.standardize(smiles)
chemistry.scaffold_analysis(smiles)
chemistry.mcs(smiles_list)
chemistry.draw_molecule(smiles, output="mol.svg")

# Pharmacology
pharmacology.profile(smiles)

# Toxicology
toxicology.analyze(smiles)

# Synthesis
synthesis.plan_synthesis(smiles, steps=3)

# Catalyst
catalyst.recommend("suzuki")
catalyst.design_ligand("PPh3", strategy="all")

# Literature
literature.search("KRAS inhibitors", source="both")

# IP
ip_check.fto_analysis(smiles, threshold=0.85)
ip_check.bioisostere_suggestions(smiles)

# Market
market.query_faers("sotorasib")

# Cheminformatics
cheminformatics.generate_conformers(smiles, num_confs=10)
cheminformatics.recap_fragment(smiles)
cheminformatics.enumerate_stereoisomers(smiles)
cheminformatics.convert_format(smiles, "inchi")
```

## Tiers

| Tier | Queries/day | Agents | Price |
|------|-------------|--------|-------|
| Free | 10 | Chemistry, Pharmacology, Toxicology | $0 |
| Pro | Unlimited | All 9 + chaining + batch | $49/mo ($29 founding) |
| Team | Unlimited | + shared workspace | $199/mo |
| Enterprise | Unlimited | + on-prem, SSO, custom agents | Custom |

```bash
pharmaclaw config --tier pro --set-key YOUR_KEY
```

## Contributing

PRs welcome! This is open source because we believe drug discovery tools should be accessible to every scientist.

```bash
git clone https://github.com/CheminemPharmaclaw/pharmaclaw.git
cd pharmaclaw
pip install -e ".[dev]"
pytest
```

## License

MIT — use it, fork it, save lives with it.

## Links

- 🌐 [pharmaclaw.com](https://pharmaclaw.com)
- 📦 [PyPI](https://pypi.org/project/pharmaclaw/)
- 💻 [GitHub](https://github.com/CheminemPharmaclaw/pharmaclaw)
- 💬 [Discord](https://discord.com/invite/clawd)
