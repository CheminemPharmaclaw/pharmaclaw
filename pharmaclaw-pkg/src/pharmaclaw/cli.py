#!/usr/bin/env python3
"""
PharmaClaw CLI v1.0.0 — Drug discovery at your fingertips.

Usage:
    pharmaclaw chemistry --smiles "CCO" --mode props
    pharmaclaw pharmacology --smiles "CC(=O)Oc1ccccc1C(=O)O"
    pharmaclaw toxicology --smiles "c1ccccc1"
    pharmaclaw orchestrate --smiles "CC1=NN(C(=O)C1)C2CC2"
    pharmaclaw chemistry -s X | pharmaclaw toxicology
"""

import click
import json
import sys

from pharmaclaw import __version__
from pharmaclaw.utils.piping import read_stdin_json, emit_json, emit_error
from pharmaclaw.utils.auth import require_auth, load_config, save_config, get_remaining_queries


def _get_smiles(smiles_arg):
    """Get SMILES from explicit arg or piped stdin JSON."""
    if smiles_arg:
        return smiles_arg
    stdin_data = read_stdin_json()
    if stdin_data:
        for key in ("smiles", "query_smiles", "canonical_smiles"):
            if key in stdin_data:
                return stdin_data[key]
    return None


# ── Main Group ─────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version")
@click.pass_context
def pharmaclaw(ctx, version):
    """🧪 PharmaClaw CLI — Drug discovery at your fingertips.

    9 chained agents: Chemistry, Cheminformatics, Pharmacology, Toxicology,
    Synthesis, Catalyst Design, Literature, IP Check, Market Intel.

    All outputs are JSON for easy piping and agent chaining.
    """
    if version:
        click.echo(json.dumps({"name": "pharmaclaw", "version": __version__, "agents": 9}))
        ctx.exit()
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ── Chemistry ──────────────────────────────────────────────

@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--mode", "-m", default="props",
              type=click.Choice(["props", "retro", "plan", "viz", "fingerprint", "similarity",
                                 "standardize", "scaffold", "mcs", "xyz"]))
@click.option("--depth", default=1, type=int, help="Retrosynthesis depth")
@click.option("--steps", default=3, type=int, help="Synthesis plan steps")
@click.option("--target-smiles", help="Comma-separated SMILES for similarity")
@click.option("--output", "-o", help="Output file for viz")
@click.option("--format", "fmt", default="svg", type=click.Choice(["png", "svg"]))
@click.option("--pretty", is_flag=True)
@require_auth
def chemistry(smiles, mode, depth, steps, target_smiles, output, fmt, pretty):
    """🧪 Chemistry — Molecular properties, retrosynthesis, fingerprints, viz."""
    from pharmaclaw.core import chemistry as chem

    smiles = _get_smiles(smiles)

    if mode == "props":
        if not smiles: emit_error("--smiles required"); sys.exit(1)
        result = chem.get_props(smiles)
    elif mode == "retro":
        if not smiles: emit_error("--smiles required"); sys.exit(1)
        result = chem.get_retro(smiles, depth)
    elif mode == "plan":
        if not smiles: emit_error("--smiles required"); sys.exit(1)
        result = chem.get_plan(smiles, steps)
    elif mode == "fingerprint":
        if not smiles: emit_error("--smiles required"); sys.exit(1)
        result = chem.get_fingerprint(smiles)
    elif mode == "similarity":
        if not smiles or not target_smiles:
            emit_error("--smiles and --target-smiles required"); sys.exit(1)
        result = chem.get_similarity(smiles, target_smiles)
    elif mode == "viz":
        if not smiles: emit_error("--smiles required"); sys.exit(1)
        result = chem.draw_molecule(smiles, output, fmt)
    elif mode == "standardize":
        if not smiles: emit_error("--smiles required"); sys.exit(1)
        result = chem.standardize(smiles)
    elif mode == "scaffold":
        if not smiles: emit_error("--smiles required"); sys.exit(1)
        result = chem.scaffold_analysis(smiles)
    elif mode == "mcs":
        if not smiles: emit_error("--smiles required (comma-separated)"); sys.exit(1)
        result = chem.mcs([s.strip() for s in smiles.split(",")])
    elif mode == "xyz":
        if not smiles: emit_error("--smiles required"); sys.exit(1)
        result = chem.get_xyz(smiles)
    else:
        emit_error(f"Unknown mode: {mode}"); sys.exit(1)

    emit_json(result, pretty)


# ── Pharmacology ───────────────────────────────────────────

@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--pretty", is_flag=True)
@require_auth
def pharmacology(smiles, pretty):
    """💊 Pharmacology — ADME/PK profiling (Lipinski, Veber, QED, BBB, CYP3A4)."""
    from pharmaclaw.core.pharmacology import profile

    smiles = _get_smiles(smiles)
    if not smiles: emit_error("--smiles required"); sys.exit(1)
    emit_json(profile(smiles), pretty)


# ── Toxicology ─────────────────────────────────────────────

@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--pretty", is_flag=True)
@require_auth
def toxicology(smiles, pretty):
    """☠️ Toxicology — Safety profiling, structural alerts, risk scoring."""
    from pharmaclaw.core.toxicology import analyze

    smiles = _get_smiles(smiles)
    if not smiles: emit_error("--smiles required"); sys.exit(1)
    emit_json(analyze(smiles), pretty)


# ── Synthesis ──────────────────────────────────────────────

@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--steps", default=3, type=int)
@click.option("--depth", default=2, type=int)
@click.option("--pretty", is_flag=True)
@require_auth
def synthesis(smiles, steps, depth, pretty):
    """🔬 Synthesis — Multi-step route planning, feasibility scoring."""
    from pharmaclaw.core.synthesis import plan_synthesis

    smiles = _get_smiles(smiles)
    if not smiles: emit_error("--smiles required"); sys.exit(1)
    emit_json(plan_synthesis(smiles, depth=depth, steps=steps), pretty)


# ── Catalyst ───────────────────────────────────────────────

@pharmaclaw.command()
@click.option("--reaction", "-r", help="Reaction type (suzuki, heck, etc.)")
@click.option("--scaffold", help="Ligand scaffold (PPh3, NHC_IMes, etc.)")
@click.option("--strategy", default="all", type=click.Choice(["steric", "electronic", "bioisosteric", "all"]))
@click.option("--enantioselective", is_flag=True)
@click.option("--pretty", is_flag=True)
@require_auth
def catalyst(reaction, scaffold, strategy, enantioselective, pretty):
    """🔧 Catalyst — Catalyst recommendation + novel ligand design."""
    from pharmaclaw.core.catalyst import recommend, design_ligand

    results = {"agent": "catalyst"}
    if reaction:
        results["recommendation"] = recommend(reaction, enantioselective=enantioselective)
    if scaffold:
        results["ligand_design"] = design_ligand(scaffold, strategy)
    if not reaction and not scaffold:
        emit_error("--reaction and/or --scaffold required"); sys.exit(1)
    emit_json(results, pretty)


# ── Literature ─────────────────────────────────────────────

@pharmaclaw.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.option("--source", default="both", type=click.Choice(["pubmed", "scholar", "both"]))
@click.option("--max-results", default=10, type=int)
@click.option("--years", type=int, help="Limit to recent N years")
@click.option("--pretty", is_flag=True)
@require_auth
def literature(query, source, max_results, years, pretty):
    """📚 Literature — PubMed + Semantic Scholar search."""
    from pharmaclaw.core.literature import search

    emit_json(search(query, source, max_results, years), pretty)


# ── IP Check ──────────────────────────────────────────────

@pharmaclaw.command()
@click.option("--smiles", "-s", required=True)
@click.option("--compare", help="Comma-separated SMILES to compare")
@click.option("--threshold", default=0.85, type=float)
@click.option("--bioisosteres", is_flag=True)
@click.option("--pretty", is_flag=True)
@require_auth
def ip(smiles, compare, threshold, bioisosteres, pretty):
    """💼 IP Check — FTO analysis, similarity search, bioisostere suggestions."""
    from pharmaclaw.core.ip_check import fto_analysis, bioisostere_suggestions

    compare_list = [s.strip() for s in compare.split(",")] if compare else None
    result = fto_analysis(smiles, compare_list, threshold)
    if bioisosteres:
        result["bioisosteres"] = bioisostere_suggestions(smiles)
    emit_json(result, pretty)


# ── Market Intel ──────────────────────────────────────────

@pharmaclaw.command()
@click.option("--drug", "-d", required=True)
@click.option("--limit", default=20, type=int)
@click.option("--pretty", is_flag=True)
@require_auth
def market(drug, limit, pretty):
    """📊 Market Intel — FAERS adverse events, trends."""
    from pharmaclaw.core.market import query_faers

    emit_json(query_faers(drug, limit), pretty)


# ── Cheminformatics ───────────────────────────────────────

@pharmaclaw.command()
@click.option("--smiles", "-s", required=True)
@click.option("--mode", "-m", default="conformers",
              type=click.Choice(["conformers", "recap", "stereoisomers", "convert"]))
@click.option("--num-confs", default=10, type=int)
@click.option("--target-format", default="inchi")
@click.option("--pretty", is_flag=True)
@require_auth
def cheminformatics(smiles, mode, num_confs, target_format, pretty):
    """🧬 Cheminformatics — 3D conformers, RECAP, stereoisomers, format conversion."""
    from pharmaclaw.core import cheminformatics as ci

    if mode == "conformers":
        result = ci.generate_conformers(smiles, num_confs=num_confs)
    elif mode == "recap":
        result = ci.recap_fragment(smiles)
    elif mode == "stereoisomers":
        result = ci.enumerate_stereoisomers(smiles)
    elif mode == "convert":
        result = ci.convert_format(smiles, target_format)
    else:
        emit_error(f"Unknown mode: {mode}"); sys.exit(1)
    emit_json(result, pretty)


# ── Orchestrate ───────────────────────────────────────────

@pharmaclaw.command()
@click.option("--smiles", "-s", help="SMILES string")
@click.option("--query", "-q", help="Literature search query")
@click.option("--drug", "-d", help="Drug name for market intel")
@click.option("--pretty", is_flag=True)
@require_auth
def orchestrate(smiles, query, drug, pretty):
    """🎯 Orchestrate — Chain all agents on a single molecule."""
    from pharmaclaw.core.chemistry import get_props
    from pharmaclaw.core.pharmacology import profile as pharm_profile
    from pharmaclaw.core.toxicology import analyze as tox_analyze
    from pharmaclaw.core.synthesis import plan_synthesis
    from pharmaclaw.core.ip_check import fto_analysis, bioisostere_suggestions

    smiles = _get_smiles(smiles)
    if not smiles: emit_error("--smiles required"); sys.exit(1)

    click.echo("🧪 Running full PharmaClaw pipeline...", err=True)
    result = {
        "agent": "orchestrator",
        "version": __version__,
        "smiles": smiles,
        "pipeline": {},
    }

    click.echo("  [1/7] Chemistry...", err=True)
    result["pipeline"]["chemistry"] = get_props(smiles)

    click.echo("  [2/7] Pharmacology...", err=True)
    result["pipeline"]["pharmacology"] = pharm_profile(smiles)

    click.echo("  [3/7] Toxicology...", err=True)
    result["pipeline"]["toxicology"] = tox_analyze(smiles)

    click.echo("  [4/7] Synthesis...", err=True)
    result["pipeline"]["synthesis"] = plan_synthesis(smiles)

    click.echo("  [5/7] IP...", err=True)
    ip_result = fto_analysis(smiles)
    ip_result["bioisosteres"] = bioisostere_suggestions(smiles)
    result["pipeline"]["ip"] = ip_result

    if query:
        click.echo("  [6/7] Literature...", err=True)
        from pharmaclaw.core.literature import search as lit_search
        result["pipeline"]["literature"] = lit_search(query, "both", 5)
    else:
        click.echo("  [6/7] Literature — skipped (no --query)", err=True)

    if drug:
        click.echo("  [7/7] Market Intel...", err=True)
        from pharmaclaw.core.market import query_faers
        result["pipeline"]["market"] = query_faers(drug, 10)
    else:
        click.echo("  [7/7] Market Intel — skipped (no --drug)", err=True)

    # Summary
    pipeline = result["pipeline"]
    chem = pipeline.get("chemistry", {})
    pharm = pipeline.get("pharmacology", {})
    tox = pipeline.get("toxicology", {})
    synth = pipeline.get("synthesis", {})
    ip_data = pipeline.get("ip", {})

    result["summary"] = {
        "molecular_weight": chem.get("mw"),
        "logP": chem.get("logp"),
        "lipinski_pass": pharm.get("report", {}).get("lipinski", {}).get("pass"),
        "qed": pharm.get("report", {}).get("qed"),
        "tox_risk": tox.get("risk", "unknown"),
        "synthesis_feasibility": synth.get("feasibility", {}).get("score", "unknown"),
        "ip_risk": ip_data.get("overall_risk", "unknown"),
    }

    click.echo("✅ Pipeline complete.", err=True)
    emit_json(result, pretty)


# ── Compare ───────────────────────────────────────────────

@pharmaclaw.command()
@click.option("--smiles", "-s", required=True, help="Comma-separated SMILES (2-10)")
@click.option("--pretty", is_flag=True)
@require_auth
def compare(smiles, pretty):
    """⚖️ Compare — Side-by-side analysis of multiple compounds."""
    from pharmaclaw.core.chemistry import get_props
    from pharmaclaw.core.toxicology import analyze as tox_analyze

    smiles_list = [s.strip() for s in smiles.split(",") if s.strip()]
    if len(smiles_list) < 2:
        emit_error("Need at least 2 SMILES separated by commas"); sys.exit(1)
    if len(smiles_list) > 10:
        emit_error("Maximum 10 compounds"); sys.exit(1)

    compounds = []
    for smi in smiles_list:
        compounds.append({
            "smiles": smi,
            "chemistry": get_props(smi),
            "toxicology": tox_analyze(smi),
        })
    emit_json({"agent": "compare", "compounds": compounds, "count": len(compounds)}, pretty)


# ── Config ────────────────────────────────────────────────

@pharmaclaw.command()
@click.option("--set-key", help="Set API key")
@click.option("--tier", type=click.Choice(["free", "pro", "team", "enterprise"]))
@click.option("--show", is_flag=True)
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


# ── Setup (interactive) ───────────────────────────────────

@pharmaclaw.command()
@click.option("--api-key", help="LLM API key (or enter interactively)")
@click.option("--model", default="gpt-4o-mini", help="Default model")
@click.option("--provider", help="Provider hint (openai, anthropic, ollama)")
def setup(api_key, model, provider):
    """🚀 Setup — Interactive first-time configuration.

    Sets your LLM API key and preferred model so the AI agents work.
    """
    cfg = load_config()

    if not api_key:
        click.echo("\n🧪 PharmaClaw Setup\n")
        click.echo("To use AI agents, you need an LLM API key.")
        click.echo("Supported: OpenAI, Anthropic, Google, Ollama (local), Mistral, and more.\n")
        click.echo("Examples:")
        click.echo("  OpenAI:    sk-proj-...")
        click.echo("  Anthropic: sk-ant-...")
        click.echo("  Ollama:    (leave blank — runs locally)\n")
        api_key = click.prompt("Enter your API key", default="", show_default=False)

    if not model or model == "gpt-4o-mini":
        click.echo("\nRecommended models:")
        click.echo("  gpt-4o-mini    — Fast & cheap (OpenAI, ~$0.15/1M tokens)")
        click.echo("  gpt-4o         — Best quality (OpenAI, ~$2.50/1M tokens)")
        click.echo("  claude-sonnet-4-20250514 — Great for science (Anthropic)")
        click.echo("  ollama/llama3  — Free, runs locally")
        model = click.prompt("Model", default="gpt-4o-mini")

    cfg["llm_api_key"] = api_key if api_key else None
    cfg["llm_model"] = model
    if provider:
        cfg["llm_provider"] = provider
    save_config(cfg)

    click.echo(f"\n✅ Configuration saved to ~/.pharmaclaw/config.json")
    click.echo(f"   Model: {model}")
    click.echo(f"   Key:   {'***' + api_key[-4:] if api_key and len(api_key) > 4 else '(none — using Ollama?)'}")
    click.echo(f"\nTry it:  pharmaclaw ask \"What are the properties of aspirin?\"")
    click.echo(f"         pharmaclaw pipeline \"Analyze sotorasib as a KRAS inhibitor\"\n")


# ── Ask (single agent) ───────────────────────────────────

@pharmaclaw.command()
@click.argument("question")
@click.option("--agent", "-a", default="chemistry",
              type=click.Choice(["chemistry", "pharmacology", "toxicology", "synthesis",
                                 "catalyst", "literature", "ip", "market"]))
@click.option("--model", "-m", help="Override model")
@click.option("--api-key", help="Override API key")
@click.option("--verbose", "-v", is_flag=True)
@click.option("--pretty", is_flag=True)
def ask(question, agent, model, api_key, verbose, pretty):
    """💬 Ask — Ask an AI agent a question in natural language.

    Examples:
        pharmaclaw ask "What are the properties of aspirin?"
        pharmaclaw ask "Profile ibuprofen for ADME" --agent pharmacology
        pharmaclaw ask "Is benzene toxic?" --agent toxicology
    """
    cfg = load_config()
    key = api_key or cfg.get("llm_api_key")
    mdl = model or cfg.get("llm_model", "gpt-4o-mini")

    agent_map = {
        "chemistry": "pharmaclaw.agents.chemistry_agent:ChemistryAgent",
        "pharmacology": "pharmaclaw.agents.pharmacology_agent:PharmacologyAgent",
        "toxicology": "pharmaclaw.agents.toxicology_agent:ToxicologyAgent",
        "synthesis": "pharmaclaw.agents.synthesis_agent:SynthesisAgent",
        "catalyst": "pharmaclaw.agents.catalyst_agent:CatalystAgent",
        "literature": "pharmaclaw.agents.literature_agent:LiteratureAgent",
        "ip": "pharmaclaw.agents.ip_agent:IPAgent",
        "market": "pharmaclaw.agents.market_agent:MarketAgent",
    }

    module_path, class_name = agent_map[agent].rsplit(":", 1)
    import importlib
    mod = importlib.import_module(module_path)
    AgentClass = getattr(mod, class_name)

    a = AgentClass(api_key=key, model=mdl, verbose=verbose)
    result = a.ask(question)

    if pretty:
        emit_json(result, True)
    else:
        # Print natural language answer, with data available via --pretty
        click.echo(result.get("answer", ""))


# ── Pipeline (multi-agent) ────────────────────────────────

@pharmaclaw.command()
@click.argument("query")
@click.option("--model", "-m", help="Override model")
@click.option("--api-key", help="Override API key")
@click.option("--verbose", "-v", is_flag=True)
@click.option("--pretty", is_flag=True)
def pipeline(query, model, api_key, verbose, pretty):
    """🎯 Pipeline — Run full multi-agent analysis on a molecule or question.

    The AI orchestrator decides which agents to invoke, chains them together,
    and produces a unified report.

    Examples:
        pharmaclaw pipeline "Analyze CC(=O)Oc1ccccc1C(=O)O as a drug candidate"
        pharmaclaw pipeline "Full safety and IP analysis of sotorasib" --verbose
    """
    cfg = load_config()
    key = api_key or cfg.get("llm_api_key")
    mdl = model or cfg.get("llm_model", "gpt-4o-mini")

    from pharmaclaw.agents.pipeline import Pipeline as PipelineAgent
    pipe = PipelineAgent(api_key=key, model=mdl, verbose=verbose)
    result = pipe.run(query)

    if pretty:
        emit_json(result, True)
    else:
        click.echo(result.get("answer", ""))


# ── Docs ──────────────────────────────────────────────────

@pharmaclaw.command()
def docs():
    """📖 Show documentation and usage examples."""
    click.echo(f"""
╔══════════════════════════════════════════════════════════╗
║              🧪 PharmaClaw v{__version__}                     ║
║         Drug Discovery at Your Fingertips              ║
╚══════════════════════════════════════════════════════════╝

AGENTS:
  chemistry        🧪  Molecular properties, retrosynthesis, viz
  cheminformatics  🧬  3D conformers, RECAP, stereoisomers
  pharmacology     💊  ADME/PK profiling, Lipinski, BBB
  toxicology       ☠️   Safety profiling, PAINS, risk scoring
  synthesis        🔬  Multi-step route planning, feasibility
  catalyst         🔧  Catalyst recommendation, ligand design
  literature       📚  PubMed + Semantic Scholar search
  ip               💼  FTO analysis, bioisostere suggestions
  market           📊  FAERS adverse events, trends

AI AGENTS (pip install pharmaclaw[agents]):
  setup            🚀  Interactive first-time setup (API key + model)
  ask              💬  Ask any agent a question in natural language
  pipeline         🎯  Full multi-agent analysis with AI orchestration

UTILITIES:
  orchestrate      🔧  Chain all agents (no AI, direct computation)
  compare          ⚖️   Side-by-side compound analysis
  config           ⚙️   Manage API key and tier
  docs             📖  This help

EXAMPLES (computational — no API key needed):
  pharmaclaw chemistry -s "CC(=O)Oc1ccccc1C(=O)O" --mode props --pretty
  pharmaclaw pharmacology -s "CC(=O)Oc1ccccc1C(=O)O" --pretty
  pharmaclaw toxicology -s "c1ccccc1" --pretty
  pharmaclaw catalyst --reaction suzuki --scaffold PPh3
  pharmaclaw orchestrate -s "CCO" --pretty

EXAMPLES (AI agents — requires API key):
  pharmaclaw setup
  pharmaclaw ask "What are the properties of aspirin?"
  pharmaclaw ask "Profile ibuprofen for oral bioavailability" -a pharmacology
  pharmaclaw ask "Is sotorasib safe?" -a toxicology
  pharmaclaw pipeline "Full analysis of CC(=O)Oc1ccccc1C(=O)O" --verbose

PIPING:
  pharmaclaw chemistry -s CCO | pharmaclaw toxicology

PYTHON API (computational):
  >>> from pharmaclaw import chemistry, pharmacology
  >>> chemistry.get_props("CCO")
  >>> pharmacology.profile("CC(=O)Oc1ccccc1C(=O)O")

PYTHON API (AI agents):
  >>> from pharmaclaw.agents import ChemistryAgent, Pipeline
  >>> agent = ChemistryAgent(api_key="sk-...")
  >>> agent.ask("What are the ADME concerns with aspirin?")
  >>> pipe = Pipeline(api_key="sk-...")
  >>> pipe.run("Analyze sotorasib as a KRAS inhibitor")

Website: https://pharmaclaw.com
""")


if __name__ == "__main__":
    pharmaclaw()
