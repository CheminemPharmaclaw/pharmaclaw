---
name: pharmaclaw-toxicology-agent
description: Toxicology/Safety agent for predictive tox profiling on molecules/SMILES. Ames mutagenicity, hERG inhibition, hepatotoxicity, LD50, acute/chronic endpoints via RDKit descriptors + PubChem Tox21/FAERS. Chains chemistry-query &amp; market-intel. Triggers on: toxicology, tox, safety, hERG/Ames/hepatotox, LD50, mutagenicity, cardiotoxicity, drug safety profiling, Tox21.
---

# Pharma Toxicology Agent

## Overview
Predictive toxicology assessment for drug safety: mutagenicity, cardiotox, organ tox, lethality using RDKit alerts, PubChem bioassays, rule-based models. Integrates FAERS from market-intel for post-market signals.

## Quick Start
1. Input SMILES → chemistry-query for base props/fingerprints.
2. Screen for tox alerts (Ames, hERG via RDKit).
3. PubChem Tox21 assays + classifications.
4. Risk matrix: Low/Med/High per endpoint.
5. JSON report + heatmap viz.

Example: \"Tox profile for c1ccccc1C(=O)O\" (benzoic acid).

## Decision Tree
- SMILES? RDKit tox descriptors + structural alerts.
- Drug name? PubChem tox data + market-intel FAERS.
- High-risk flags? Recommend analogs/retrosynth via chemistry-query.

## Key Endpoints
| Endpoint | Method | Risk Flags |
|----------|--------|------------|
| Ames     | RDKit  | + mutagen  |
| hERG     | Descriptors | IC50 &lt;10uM |
| Hepatotox| Structural | Alerts     |
| LD50     | QSAR proxy | logLD50 est|
| Skin/eye | PubChem | GHS class  |

## Structural Alerts
- PAINS filters for false positives.
- Reactive groups (epoxides, nitroso).

## Post-Market
Chain market-intel for FAERS counts/trends on similar structures (Morgan FP similarity).

## Resources
### references/
- tox_alerts.md: RDKit alert lists/Brenk/PAINS.
- tox21_assays.md: PubChem mappings.

### scripts/
- tox_screen.py: Batch tox descriptors/alerts.

Feed high-risk to IP/synthesis for safer derivatives.