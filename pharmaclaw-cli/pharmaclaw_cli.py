#!/usr/bin/env python3
"""
PharmaClaw CLI v1.0.0 — Unified command-line interface for the PharmaClaw drug discovery agent team.

Usage:
    pharmaclaw chemistry --smiles "CCO" --mode props
    pharmaclaw pharmacology --smiles "CC(=O)Oc1ccccc1C(=O)O"
    pharmaclaw toxicology --smiles "c1ccccc1"
    pharmaclaw synthesis --smiles "CC1=NN(C(=O)C1)C2CC2" --steps 3
    pharmaclaw catalyst --reaction suzuki --scaffold PPh3
    pharmaclaw literature --query "KRAS G12C inhibitors 2026"
    pharmaclaw ip --smiles "CCO" --threshold 0.85
    pharmaclaw market --drug sotorasib
    pharmaclaw orchestrate --smiles "CC1=NN(C(=O)C1)C2CC2"
    pharmaclaw compare --smiles "CCO,CCCO,CCCCO"
    pharmaclaw report --smiles "CCO" --output report.json

Pipe commands: pharmaclaw chemistry --smiles X | pharmaclaw toxicology
"""

__version__ = "1.0.0"

import click
import json
import sys
import os

# Add parent dir so agents/ and utils/ are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.piping import read_stdin_json, emit_json, emit_error
from utils.auth import require_auth, load_config, save_config, get_remaining_queries


def get_smiles_from_args_or_stdin(smiles_arg):
    """Get SMILES from explicit arg or piped stdin JSON."""
    if smiles_arg:
        return smiles_arg
    stdin_data = read_stdin_json()
    if stdin_data:
        # Look for smiles in common keys
        for key in ("smiles", "query_smiles", "canonical_smiles"):
            if key in stdin_data:
                return stdin_data[key]
        # Look in nested props
        if "props" in stdin_data and isinstance(stdin_data["props"], dict):
            return stdin_data.get("smiles")
    return None


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version")
@click.pass_context
def pharmaclaw(ctx, version):
    """🧪 PharmaClaw CLI — Drug discovery at your fingertips.

    Unified CLI for Chemistry, Pharmacology, Toxicology, Synthesis,
    Catalyst Design, Literature Mining, IP Check, and Market Intel agents.

    All outputs are JSON for easy piping and agent chaining.
    """
    if version:
        click.echo(json.dumps({"name": "pharmaclaw-cli", "version": __version__, "agents": 8}))
        ctx.exit()
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ─────────────────────────────────────────────
# CHEMISTRY
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--mode", "-m", default="props",
              type=click.Choice(["props", "retro", "plan", "viz", "fingerprint", "similarity", "pubchem", "reaction"]),
              help="Analysis mode")
@click.option("--depth", default=1, type=int, help="Retrosynthesis depth")
@click.option("--steps", default=3, type=int, help="Synthesis plan steps")
@click.option("--compound", help="Compound name for PubChem lookup")
@click.option("--query-type", default="info", type=click.Choice(["info", "structure", "synthesis", "similar"]))
@click.option("--target-smiles", help="Comma-separated SMILES for similarity comparison")
@click.option("--template", help="Reaction template name (amide, ester, suzuki)")
@click.option("--reactants", help="Comma-separated reactant SMILES")
@click.option("--output", "-o", help="Output file for viz")
@click.option("--format", "fmt", default="svg", type=click.Choice(["png", "svg"]))
@click.option("--pretty", is_flag=True, help="Pretty-print JSON")
@require_auth
def chemistry(smiles, mode, depth, steps, compound, query_type, target_smiles, template, reactants, output, fmt, pretty):
    """🧪 Chemistry Agent — Molecular properties, retrosynthesis, PubChem queries."""
    from agents.chemistry import get_props, get_retro, get_plan, get_fingerprint, get_similarity, get_draw, query_pubchem, run_reaction

    smiles = get_smiles_from_args_or_stdin(smiles)

    if mode == "pubchem":
        if not compound and not smiles:
            emit_error("--compound or --smiles required for pubchem mode")
            sys.exit(1)
        result = query_pubchem(compound or smiles, query_type)
    elif mode == "reaction":
        if not template:
            emit_error("--template required for reaction mode")
            sys.exit(1)
        rcts = reactants.split(",") if reactants else []
        result = run_reaction(template, rcts)
    elif mode == "similarity":
        if not smiles or not target_smiles:
            emit_error("--smiles and --target-smiles required for similarity mode")
            sys.exit(1)
        result = get_similarity(smiles, target_smiles)
    elif mode == "viz":
        if not smiles:
            emit_error("--smiles required")
            sys.exit(1)
        result = get_draw(smiles, output, fmt)
    elif mode == "fingerprint":
        if not smiles:
            emit_error("--smiles required")
            sys.exit(1)
        result = get_fingerprint(smiles)
    elif mode == "retro":
        if not smiles:
            emit_error("--smiles required")
            sys.exit(1)
        result = get_retro(smiles, depth)
    elif mode == "plan":
        if not smiles:
            emit_error("--smiles required")
            sys.exit(1)
        result = get_plan(smiles, steps)
    else:  # props
        if not smiles:
            emit_error("--smiles required")
            sys.exit(1)
        result = get_props(smiles)

    emit_json(result, pretty)


# ─────────────────────────────────────────────
# PHARMACOLOGY
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--pretty", is_flag=True)
@require_auth
def pharmacology(smiles, pretty):
    """💊 Pharmacology Agent — ADME/PK profiling (Lipinski, Veber, QED, BBB, CYP3A4)."""
    from agents.pharmacology import profile

    smiles = get_smiles_from_args_or_stdin(smiles)
    if not smiles:
        emit_error("--smiles required")
        sys.exit(1)
    result = profile(smiles)
    emit_json(result, pretty)


# ─────────────────────────────────────────────
# TOXICOLOGY
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--pretty", is_flag=True)
@require_auth
def toxicology(smiles, pretty):
    """☠️ Toxicology Agent — Safety profiling, structural alerts, risk scoring."""
    from agents.toxicology import analyze

    smiles = get_smiles_from_args_or_stdin(smiles)
    if not smiles:
        emit_error("--smiles required")
        sys.exit(1)
    result = analyze(smiles)
    emit_json(result, pretty)


# ─────────────────────────────────────────────
# SYNTHESIS
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--target", "-t", help="Target name or SMILES")
@click.option("--steps", default=3, type=int, help="Number of synthesis steps")
@click.option("--depth", default=2, type=int, help="Retrosynthesis depth")
@click.option("--pretty", is_flag=True)
@require_auth
def synthesis(smiles, target, steps, depth, pretty):
    """🔬 Synthesis Agent — Multi-step route planning, feasibility scoring."""
    from agents.synthesis import plan_synthesis

    smiles = get_smiles_from_args_or_stdin(smiles)
    if not smiles:
        emit_error("--smiles required")
        sys.exit(1)
    result = plan_synthesis(smiles, target, depth, steps)
    emit_json(result, pretty)


# ─────────────────────────────────────────────
# CATALYST
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--reaction", "-r", help="Reaction type (suzuki, heck, buchwald_hartwig, etc.)")
@click.option("--substrate", help="Substrate SMILES")
@click.option("--scaffold", help="Ligand scaffold for design (PPh3, NHC_IMes, etc.)")
@click.option("--strategy", default="all", type=click.Choice(["steric", "electronic", "bioisosteric", "all"]))
@click.option("--constraints", help="JSON constraints string")
@click.option("--enantioselective", is_flag=True)
@click.option("--pretty", is_flag=True)
@require_auth
def catalyst(reaction, substrate, scaffold, strategy, constraints, enantioselective, pretty):
    """🔧 Catalyst Design Agent — Catalyst recommendation + novel ligand design."""
    from agents.catalyst import recommend, design_ligand

    results = {"agent": "catalyst"}

    if reaction:
        results["recommendation"] = recommend(reaction, substrate, constraints, enantioselective)

    if scaffold:
        results["ligand_design"] = design_ligand(scaffold, strategy)

    if not reaction and not scaffold:
        emit_error("--reaction and/or --scaffold required")
        sys.exit(1)

    emit_json(results, pretty)


# ─────────────────────────────────────────────
# LITERATURE
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.option("--source", default="both", type=click.Choice(["pubmed", "scholar", "both"]))
@click.option("--max-results", default=10, type=int)
@click.option("--years", type=int, help="Limit to recent N years")
@click.option("--pretty", is_flag=True)
@require_auth
def literature(query, source, max_results, years, pretty):
    """📚 Literature Agent — PubMed + Semantic Scholar search with TLDRs."""
    from agents.literature import search

    result = search(query, source, max_results, years)
    emit_json(result, pretty)


# ─────────────────────────────────────────────
# IP CHECK
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", required=True, help="Query SMILES")
@click.option("--compare", help="Comma-separated SMILES to compare against")
@click.option("--threshold", default=0.85, type=float, help="Tanimoto threshold for FTO risk")
@click.option("--bioisosteres", is_flag=True, help="Include bioisostere suggestions")
@click.option("--pretty", is_flag=True)
@require_auth
def ip(smiles, compare, threshold, bioisosteres, pretty):
    """💼 IP Check Agent — FTO analysis, similarity search, bioisostere suggestions."""
    from agents.ip_check import fto_analysis, bioisostere_suggestions

    compare_list = [s.strip() for s in compare.split(",")] if compare else None
    result = fto_analysis(smiles, compare_list, threshold)

    if bioisosteres:
        result["bioisosteres"] = bioisostere_suggestions(smiles)

    emit_json(result, pretty)


# ─────────────────────────────────────────────
# MARKET INTEL
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--drug", "-d", required=True, help="Drug name or SMILES")
@click.option("--limit", default=20, type=int, help="Max events to return")
@click.option("--include-preds", is_flag=True, help="Include prediction market data")
@click.option("--pretty", is_flag=True)
@require_auth
def market(drug, limit, include_preds, pretty):
    """📊 Market Intel Agent — FAERS adverse events, trends, competitive intel."""
    from agents.market import query_faers

    result = query_faers(drug, limit, include_preds)
    emit_json(result, pretty)


# ─────────────────────────────────────────────
# ORCHESTRATE (chains all agents)
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--query", "-q", help="Natural language query (for literature)")
@click.option("--drug", "-d", help="Drug name (for market intel)")
@click.option("--reaction", "-r", help="Reaction type (for catalyst)")
@click.option("--pretty", is_flag=True)
@require_auth
def orchestrate(smiles, query, drug, reaction, pretty):
    """🎯 Orchestrate — Chain all agents on a single molecule for full analysis."""
    from agents.chemistry import get_props, get_retro
    from agents.pharmacology import profile as pharm_profile
    from agents.toxicology import analyze as tox_analyze
    from agents.synthesis import plan_synthesis
    from agents.ip_check import fto_analysis, bioisostere_suggestions
    from agents.market import query_faers
    from agents.literature import search as lit_search

    smiles = get_smiles_from_args_or_stdin(smiles)
    if not smiles:
        emit_error("--smiles required for orchestration")
        sys.exit(1)

    click.echo("🧪 Running full PharmaClaw pipeline...", err=True)

    result = {
        "agent": "orchestrator",
        "version": __version__,
        "smiles": smiles,
        "pipeline": {}
    }

    # 1. Chemistry
    click.echo("  [1/7] Chemistry — molecular properties...", err=True)
    result["pipeline"]["chemistry"] = get_props(smiles)

    # 2. Pharmacology
    click.echo("  [2/7] Pharmacology — ADME/PK profiling...", err=True)
    result["pipeline"]["pharmacology"] = pharm_profile(smiles)

    # 3. Toxicology
    click.echo("  [3/7] Toxicology — safety profiling...", err=True)
    result["pipeline"]["toxicology"] = tox_analyze(smiles)

    # 4. Synthesis
    click.echo("  [4/7] Synthesis — route planning...", err=True)
    result["pipeline"]["synthesis"] = plan_synthesis(smiles)

    # 5. IP Check
    click.echo("  [5/7] IP — freedom-to-operate...", err=True)
    ip_result = fto_analysis(smiles)
    ip_result["bioisosteres"] = bioisostere_suggestions(smiles)
    result["pipeline"]["ip"] = ip_result

    # 6. Literature
    if query:
        click.echo("  [6/7] Literature — searching...", err=True)
        result["pipeline"]["literature"] = lit_search(query, "both", 5)
    else:
        click.echo("  [6/7] Literature — skipped (no --query)", err=True)

    # 7. Market Intel
    if drug:
        click.echo("  [7/7] Market Intel — FAERS query...", err=True)
        result["pipeline"]["market"] = query_faers(drug, 10)
    else:
        click.echo("  [7/7] Market Intel — skipped (no --drug)", err=True)

    # Summary
    result["summary"] = _build_summary(result["pipeline"])
    click.echo("✅ Pipeline complete.", err=True)
    emit_json(result, pretty)


def _build_summary(pipeline: dict) -> dict:
    """Build a human-readable summary from pipeline results."""
    summary = {}

    chem = pipeline.get("chemistry", {})
    if "mw" in chem:
        summary["molecular_weight"] = chem["mw"]
        summary["logP"] = chem.get("logp")

    pharm = pipeline.get("pharmacology", {})
    if "lipinski" in pharm:
        summary["lipinski_pass"] = pharm["lipinski"].get("pass")
    if "qed" in pharm:
        summary["qed"] = pharm["qed"]

    tox = pipeline.get("toxicology", {})
    summary["tox_risk"] = tox.get("risk", "unknown")

    synth = pipeline.get("synthesis", {})
    feas = synth.get("feasibility", {})
    summary["synthesis_feasibility"] = feas.get("score", "unknown")

    ip_data = pipeline.get("ip", {})
    summary["ip_risk"] = ip_data.get("overall_risk", "unknown")

    return summary


# ─────────────────────────────────────────────
# COMPARE (side-by-side)
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", required=True, help="Comma-separated SMILES (2-10)")
@click.option("--pretty", is_flag=True)
@require_auth
def compare(smiles, pretty):
    """⚖️ Compare — Side-by-side analysis of multiple compounds."""
    from agents.chemistry import get_props
    from agents.toxicology import analyze as tox_analyze

    smiles_list = [s.strip() for s in smiles.split(",") if s.strip()]
    if len(smiles_list) < 2:
        emit_error("Need at least 2 SMILES separated by commas")
        sys.exit(1)
    if len(smiles_list) > 10:
        emit_error("Maximum 10 compounds for comparison")
        sys.exit(1)

    compounds = []
    for smi in smiles_list:
        chem = get_props(smi)
        tox = tox_analyze(smi)
        compounds.append({
            "smiles": smi,
            "chemistry": chem,
            "toxicology": tox,
        })

    emit_json({"agent": "compare", "compounds": compounds, "count": len(compounds)}, pretty)


# ─────────────────────────────────────────────
# REPORT (full pipeline → file)
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", required=True, help="SMILES string")
@click.option("--output", "-o", default="pharmaclaw_report.json", help="Output file path")
@click.option("--query", "-q", help="Literature search query")
@click.option("--drug", "-d", help="Drug name for market intel")
@click.option("--pretty", is_flag=True)
@require_auth
def report(smiles, output, query, drug, pretty):
    """📄 Report — Full pipeline analysis saved to JSON file."""
    from agents.chemistry import get_props, get_retro
    from agents.pharmacology import profile as pharm_profile
    from agents.toxicology import analyze as tox_analyze
    from agents.synthesis import plan_synthesis
    from agents.ip_check import fto_analysis, bioisostere_suggestions

    result = {
        "agent": "report",
        "version": __version__,
        "smiles": smiles,
        "chemistry": get_props(smiles),
        "pharmacology": pharm_profile(smiles),
        "toxicology": tox_analyze(smiles),
        "synthesis": plan_synthesis(smiles),
        "ip": fto_analysis(smiles),
        "bioisosteres": bioisostere_suggestions(smiles),
    }

    with open(output, "w") as f:
        json.dump(result, f, indent=2, default=str)

    click.echo(f"📄 Report saved to {output}", err=True)
    emit_json({"status": "saved", "output": output, "agents_run": 6}, pretty)


# ─────────────────────────────────────────────
# BATCH
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--file", "-f", "input_file", required=True, type=click.Path(exists=True), help="CSV file with SMILES column")
@click.option("--agents", "-a", default="chemistry,toxicology", help="Comma-separated agents to run")
@click.option("--output", "-o", default="batch_results.json", help="Output file")
@click.option("--pretty", is_flag=True)
@require_auth
def batch(input_file, agents, output, pretty):
    """📦 Batch — Process CSV of compounds through selected agents."""
    import csv
    from agents.chemistry import get_props
    from agents.toxicology import analyze as tox_analyze
    from agents.pharmacology import profile as pharm_profile

    agent_list = [a.strip() for a in agents.split(",")]
    agent_map = {
        "chemistry": get_props,
        "toxicology": tox_analyze,
        "pharmacology": pharm_profile,
    }

    results = []
    with open(input_file, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            smi = row.get("smiles") or row.get("SMILES") or row.get("Smiles")
            if not smi:
                continue
            entry = {"index": i, "smiles": smi.strip()}
            for agent_name in agent_list:
                fn = agent_map.get(agent_name)
                if fn:
                    entry[agent_name] = fn(smi.strip())
            results.append(entry)
            if i >= 499:  # max 500
                break

    with open(output, "w") as f:
        json.dump(results, f, indent=2, default=str)

    click.echo(f"📦 Batch complete: {len(results)} compounds → {output}", err=True)
    emit_json({"status": "complete", "compounds": len(results), "output": output}, pretty)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--set-key", help="Set API key")
@click.option("--tier", type=click.Choice(["free", "pro", "team", "enterprise"]), help="Set tier")
@click.option("--show", is_flag=True, help="Show current config")
def config(set_key, tier, show):
    """⚙️ Config — Manage API key and tier settings."""
    cfg = load_config()

    if show or (not set_key and not tier):
        remaining = get_remaining_queries()
        cfg["remaining_queries"] = remaining if remaining is not None else "unlimited"
        emit_json(cfg, True)
        return

    if set_key:
        cfg["api_key"] = set_key
    if tier:
        cfg["tier"] = tier

    save_config(cfg)
    click.echo(f"✅ Config updated: tier={cfg.get('tier')}", err=True)
    emit_json(cfg, True)


# ─────────────────────────────────────────────
# DOCS
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# LANGGRAPH ORCHESTRATION
# ─────────────────────────────────────────────
@pharmaclaw.command()
@click.option("--smiles", "-s", required=True, help="SMILES string")
@click.option("--workflow", "-w", default="full",
              type=click.Choice(["full", "quick", "safety", "synthesis"]),
              help="Pipeline workflow")
@click.option("--query", "-q", help="Literature search query")
@click.option("--drug", "-d", help="Drug name for market intel")
@click.option("--verbose", "-v", is_flag=True)
@click.option("--pretty", is_flag=True)
@require_auth
def langgraph(smiles, workflow, query, drug, verbose, pretty):
    """🔗 LangGraph — Stateful multi-agent pipeline with dynamic routing and consensus scoring.

    Workflows:
      full      — All 8 agents with conditional routing (default)
      quick     — Chemistry + Toxicology → Consensus
      safety    — Chemistry + Pharmacology + Toxicology → Consensus
      synthesis — Chemistry + Synthesis + Catalyst → Consensus

    Features: self-correction, conditional routing (high tox → reroute),
    consensus scoring (0-10), and actionable recommendations.
    """
    from orchestration.cheminem_orchestrator import run_pipeline

    if verbose:
        click.echo(f"🔗 LangGraph {workflow} pipeline starting...", err=True)

    result = run_pipeline(
        smiles=smiles,
        workflow=workflow,
        query=query,
        drug_name=drug,
        verbose=verbose,
    )

    if verbose:
        consensus = result.get("consensus", {})
        click.echo(f"✅ Score: {consensus.get('score', '?')}/10 — {consensus.get('verdict', '')}", err=True)

    emit_json(result, pretty)


@pharmaclaw.command()
def docs():
    """📖 Show documentation and usage examples."""
    doc = """
╔══════════════════════════════════════════════════════════════╗
║                   🧪 PharmaClaw CLI v1.0.0                  ║
║           Drug Discovery at Your Fingertips                 ║
╚══════════════════════════════════════════════════════════════╝

AGENTS:
  chemistry     🧪  Molecular properties, retrosynthesis, PubChem
  pharmacology  💊  ADME/PK profiling, Lipinski, BBB, CYP3A4
  toxicology    ☠️   Safety profiling, PAINS, risk scoring
  synthesis     🔬  Multi-step route planning, feasibility
  catalyst      🔧  Catalyst recommendation, ligand design
  literature    📚  PubMed + Semantic Scholar search
  ip            💼  FTO analysis, bioisostere suggestions
  market        📊  FAERS adverse events, trends

UTILITIES:
  langgraph     🔗  LangGraph stateful pipeline (dynamic routing + consensus)
  orchestrate   🎯  Chain all agents on one molecule (simple sequential)
  compare       ⚖️   Side-by-side compound analysis
  report        📄  Full pipeline → JSON file
  batch         📦  CSV batch processing
  config        ⚙️   Manage API key and tier
  docs          📖  This help

EXAMPLES:
  # Get molecular properties
  pharmaclaw chemistry --smiles "CC(=O)Oc1ccccc1C(=O)O" --mode props

  # Full ADME profile
  pharmaclaw pharmacology --smiles "CC(=O)Oc1ccccc1C(=O)O"

  # Retrosynthesis
  pharmaclaw chemistry --smiles "CC(=O)Oc1ccccc1C(=O)O" --mode retro --depth 2

  # Pipe chemistry → toxicology
  pharmaclaw chemistry -s "CCO" | pharmaclaw toxicology

  # Full orchestration
  pharmaclaw orchestrate -s "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4" \\
    --query "sotorasib KRAS" --drug sotorasib

  # Catalyst design for Suzuki coupling
  pharmaclaw catalyst --reaction suzuki --scaffold PPh3 --strategy all

  # Batch processing
  pharmaclaw batch --file compounds.csv --agents chemistry,toxicology,pharmacology

  # Compare compounds
  pharmaclaw compare --smiles "CCO,CCCO,c1ccccc1O"

PIPING:
  All commands output JSON to stdout. Pipe between agents:
    pharmaclaw chemistry -s X | pharmaclaw toxicology
    pharmaclaw chemistry -s X | pharmaclaw ip

TIERS:
  Free       10 queries/day    chemistry + pharmacology + toxicology
  Pro        Unlimited         All 8 agents + chaining + batch
  Team       Unlimited         + shared workspace
  Enterprise Unlimited         + on-prem, SSO, custom agents

  Set tier: pharmaclaw config --tier pro --set-key YOUR_KEY

WEBSITE: https://pharmaclaw.com
DOCS:    https://pharmaclaw.com/docs
"""
    click.echo(doc)


if __name__ == "__main__":
    pharmaclaw()
