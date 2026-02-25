---
name: pharmaclaw-traction-agent
description: >-
  Traction Agent for Phase 1 monetization of pharma AI team (drug discovery/synthesis/tox/IP).
  Orchestrates MVP prototypes, community outreach, pilots/feedback via CEO Agent delegation
  (keywords: traction/pilot/demo/outreach). Generates plans/demos/metrics w/ RDKit/PubChem/spaCy.
  Use for growth workflows, chaining pharma agents for pharma-specific demos (SMILES synth/IP demos).
  Triggers on traction, monetize, pilot, demo, outreach, Phase 1 pharma business dev.
---

# Traction Agent

Phase 1 growth for PharmaClaw: MVP, demos, outreach, pilots, iterate. CEO delegates here for business tasks.

## Workflow (CEO routes keywords)

1. **Objectives/MVP**: Plan + RDKit synth demo.
2. **Prototypes**: Package pharma outputs (SMILES/IP) for GitHub/Streamlit.
3. **Outreach/Pilots**: Posts (X/Reddit), targets, CSV tracking.
4. **Assess**: NLP feedback, pandas dashboard.

Exec: `python scripts/ceo_agent.py 'traction pilot'`

## Resources

### scripts/
- `ceo_agent.py`: Router class, chains subs.
- `traction_agent.py`: Core steps/classes.
- Integrate: Replace mocks w/ sessions_spawn('chemistry-query', task)

### references/
- `pharma_pains.md`: Targets/MVP ideas.

### assets/
- `plan_template.md`: Phase1 MD.

OpenClaw: Spawn `sessions_spawn task=traction... label=ceo`

## Example
CEO.process_query('pilot demo') → step1-4 files.
