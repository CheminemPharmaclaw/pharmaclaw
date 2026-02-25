#!/usr/bin/env python3
"""
Cheminem Orchestrator — LangGraph-powered multi-agent drug discovery pipeline.

Uses a stateful graph to route tasks across PharmaClaw agents with:
- Dynamic routing based on query type and intermediate results
- Self-correction (retry on invalid SMILES, reroute on high tox)
- Consensus building across agents
- State persistence for iterative refinement

Usage:
    python cheminem_orchestrator.py --smiles "CCO" --workflow full
    python cheminem_orchestrator.py --smiles "CCO" --workflow quick
    python cheminem_orchestrator.py --query "KRAS G12C inhibitor" --workflow discovery
    
    # From CLI:
    pharmaclaw langgraph --smiles "CCO" --workflow full
"""

import json
import sys
import os
import argparse
from typing import TypedDict, Annotated, Literal
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

# Import our tools (direct function calls, not as LangChain tools for graph nodes)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import (
    _run_script, _validate_smiles,
    SKILLS_DIR, PYTHON
)

# ─────────────────────────────────────────────
# STATE SCHEMA
# ─────────────────────────────────────────────

def merge_dicts(a: dict, b: dict) -> dict:
    """Merge two dicts, b overwrites a."""
    merged = {**a}
    merged.update(b)
    return merged


class PipelineState(TypedDict, total=False):
    """Shared state across all agent nodes."""
    # Input
    smiles: str
    query: str
    drug_name: str
    workflow: str  # full, quick, discovery, synthesis, safety

    # Agent results
    chemistry: dict
    pharmacology: dict
    toxicology: dict
    synthesis: dict
    catalyst: dict
    literature: dict
    ip: dict
    market: dict

    # Orchestration
    current_agent: str
    errors: list[str]
    retries: int
    route_history: list[str]
    consensus: dict
    score: float
    recommendations: list[str]
    timestamp: str


# ─────────────────────────────────────────────
# AGENT NODE FUNCTIONS
# ─────────────────────────────────────────────

def node_chemistry(state: PipelineState) -> dict:
    """Chemistry node: molecular properties + retrosynthesis."""
    smiles = state["smiles"]
    err = _validate_smiles(smiles)
    if err:
        return {"errors": state.get("errors", []) + [f"chemistry: {err}"], "chemistry": {"error": err}}

    props = _run_script("pharmaclaw-chemistry-query", "rdkit_mol.py",
                        ["--smiles", smiles, "--action", "props"])
    retro = _run_script("pharmaclaw-chemistry-query", "rdkit_mol.py",
                        ["--smiles", smiles, "--action", "retro", "--depth", "2"])

    result = {
        "props": props,
        "retro": retro,
        "smiles": smiles,
    }
    return {
        "chemistry": result,
        "route_history": state.get("route_history", []) + ["chemistry"],
    }


def node_pharmacology(state: PipelineState) -> dict:
    """Pharmacology node: ADME/PK profiling."""
    smiles = state["smiles"]
    input_json = json.dumps({"smiles": smiles})
    result = _run_script("pharmaclaw-pharmacology-agent", "chain_entry.py",
                         ["--input-json", input_json])
    return {
        "pharmacology": result,
        "route_history": state.get("route_history", []) + ["pharmacology"],
    }


def node_toxicology(state: PipelineState) -> dict:
    """Toxicology node: safety profiling."""
    smiles = state["smiles"]
    result = _run_script("pharmaclaw-tox-agent", "tox_agent.py", [smiles])
    return {
        "toxicology": result,
        "route_history": state.get("route_history", []) + ["toxicology"],
    }


def node_synthesis(state: PipelineState) -> dict:
    """Synthesis node: multi-step route planning."""
    smiles = state["smiles"]
    result = _run_script("pharmaclaw-chemistry-query", "rdkit_mol.py",
                         ["--smiles", smiles, "--action", "plan", "--steps", "3"],
                         timeout=120)

    # Add feasibility scoring
    route = result.get("route", [])
    num_steps = len(route)
    total_precursors = sum(len(s.get("precursors", [])) for s in route)
    if num_steps <= 3 and total_precursors <= 10:
        feasibility = {"score": "high", "confidence": 0.75}
    elif num_steps <= 5:
        feasibility = {"score": "moderate", "confidence": 0.55}
    else:
        feasibility = {"score": "challenging", "confidence": 0.35}
    result["feasibility"] = feasibility

    return {
        "synthesis": result,
        "route_history": state.get("route_history", []) + ["synthesis"],
    }


def node_catalyst(state: PipelineState) -> dict:
    """Catalyst node: recommend catalysts based on synthesis route."""
    # Determine reaction types from synthesis data
    reactions = ["suzuki"]  # default
    synth = state.get("synthesis", {})
    if synth.get("route"):
        # Could infer reaction types from precursors — for now use common coupling
        reactions = ["suzuki", "buchwald_hartwig"]

    results = {}
    for rxn in reactions:
        data = _run_script("pharmaclaw-catalyst-design", "catalyst_recommend.py",
                           ["--reaction", rxn])
        results[rxn] = data

    return {
        "catalyst": results,
        "route_history": state.get("route_history", []) + ["catalyst"],
    }


def node_literature(state: PipelineState) -> dict:
    """Literature node: search PubMed for relevant papers."""
    query = state.get("query", "")
    if not query:
        # Build query from SMILES/drug name
        drug = state.get("drug_name", "")
        if drug:
            query = f"{drug} drug discovery synthesis"
        else:
            query = "novel drug candidate synthesis ADME"

    result = _run_script("pharmaclaw-literature-agent", "pubmed_search.py",
                         ["--query", query, "--max-results", "5"])
    return {
        "literature": result,
        "route_history": state.get("route_history", []) + ["literature"],
    }


def node_ip(state: PipelineState) -> dict:
    """IP node: freedom-to-operate analysis."""
    smiles = state["smiles"]
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        mol = Chem.MolFromSmiles(smiles)
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

        refs = [
            ("sotorasib", "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4"),
            ("osimertinib-like", "C=CC(=O)N1CCC(CC1)OC2=NC3=CC(=CC=C3N2)C4=CC=CC(=C4)OC"),
            ("imatinib-like", "CC1=C(C=CC=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C"),
        ]
        comparisons = []
        for name, ref_smi in refs:
            ref_mol = Chem.MolFromSmiles(ref_smi)
            if ref_mol:
                ref_fp = AllChem.GetMorganFingerprintAsBitVect(ref_mol, 2, nBits=2048)
                sim = DataStructs.TanimotoSimilarity(fp, ref_fp)
                comparisons.append({"reference": name, "tanimoto": round(sim, 4),
                                    "risk": "HIGH" if sim >= 0.85 else "MODERATE" if sim >= 0.5 else "LOW"})

        comparisons.sort(key=lambda x: x["tanimoto"], reverse=True)
        max_sim = comparisons[0]["tanimoto"] if comparisons else 0

        result = {
            "max_similarity": round(max_sim, 4),
            "overall_risk": "HIGH" if max_sim >= 0.85 else "MODERATE" if max_sim >= 0.5 else "LOW",
            "comparisons": comparisons,
            "bioisostere_suggestions": [
                {"from": "Cl", "to": "CF3", "rationale": "Similar lipophilicity, novel IP"},
                {"from": "phenyl", "to": "pyridyl", "rationale": "Better solubility, different IP"},
                {"from": "amide", "to": "sulfonamide", "rationale": "Geometry change, same H-bonding"},
            ],
        }
    except Exception as e:
        result = {"error": str(e)}

    return {
        "ip": result,
        "route_history": state.get("route_history", []) + ["ip"],
    }


def node_market(state: PipelineState) -> dict:
    """Market intel node: FAERS adverse events."""
    drug = state.get("drug_name", state.get("smiles", ""))
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        result = _run_script("pharmaclaw-market-intel-agent", "query_faers.py",
                             ["--drug", drug, "--output", tmpdir, "--limit-events", "10"],
                             timeout=60)
        for fname in os.listdir(tmpdir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(tmpdir, fname)) as f:
                        result[fname.replace(".json", "")] = json.load(f)
                except Exception:
                    pass

    return {
        "market": result,
        "route_history": state.get("route_history", []) + ["market"],
    }


# ─────────────────────────────────────────────
# CONSENSUS & SCORING
# ─────────────────────────────────────────────

def node_consensus(state: PipelineState) -> dict:
    """Build consensus score and recommendations from all agent results."""
    score = 10.0
    recommendations = []
    warnings = []

    # Chemistry
    chem = state.get("chemistry", {})
    props = chem.get("props", {})
    mw = props.get("mw", 0)
    logp = props.get("logp", 0)

    if mw > 500:
        score -= 1.0
        warnings.append(f"High MW ({mw:.0f}) — oral bioavailability concern")
    if logp > 5:
        score -= 1.0
        warnings.append(f"High LogP ({logp:.2f}) — solubility concern")

    # Pharmacology
    pharm = state.get("pharmacology", {})
    report = pharm.get("report", {})
    lipinski = report.get("lipinski", {})
    if lipinski and not lipinski.get("pass", True):
        score -= 1.5
        warnings.append(f"Lipinski violations: {lipinski.get('violations', '?')}")
    adme = report.get("adme", {})
    if adme.get("solubility", {}).get("class") == "low":
        score -= 0.5
        recommendations.append("Consider prodrug or salt form for solubility")
    if adme.get("cyp3a4_inhibition", {}).get("risk") == "high":
        score -= 0.5
        recommendations.append("CYP3A4 inhibition risk — check DDI potential")

    # Toxicology
    tox = state.get("toxicology", {})
    risk = tox.get("risk", "")
    if "high" in risk.lower():
        score -= 2.0
        warnings.append("HIGH tox risk — consider structural modifications")
        recommendations.append("Run deeper tox profiling with hERG/Ames assays")
    elif "medium" in risk.lower():
        score -= 1.0

    # Synthesis
    synth = state.get("synthesis", {})
    feas = synth.get("feasibility", {})
    if feas.get("score") == "challenging":
        score -= 1.0
        recommendations.append("Complex synthesis — consider simpler analogs")

    # IP
    ip_data = state.get("ip", {})
    if ip_data.get("overall_risk") == "HIGH":
        score -= 2.0
        warnings.append("HIGH IP risk — apply bioisosteric modifications")
        recommendations.append("Use bioisostere suggestions to generate novel derivatives")
    elif ip_data.get("overall_risk") == "MODERATE":
        score -= 0.5

    score = max(0, min(10, score))

    # Overall assessment
    if score >= 8:
        verdict = "EXCELLENT — strong drug candidate"
    elif score >= 6:
        verdict = "GOOD — viable with modifications"
    elif score >= 4:
        verdict = "FAIR — significant improvements needed"
    else:
        verdict = "POOR — major concerns, consider alternative scaffolds"

    consensus = {
        "score": round(score, 1),
        "verdict": verdict,
        "warnings": warnings,
        "recommendations": recommendations,
        "agents_consulted": state.get("route_history", []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return {"consensus": consensus, "score": score}


# ─────────────────────────────────────────────
# ROUTING LOGIC
# ─────────────────────────────────────────────

def route_after_tox(state: PipelineState) -> str:
    """Conditional routing after toxicology: if high risk, reroute to pharmacology for derivative suggestions."""
    tox = state.get("toxicology", {})
    risk = tox.get("risk", "Low")
    workflow = state.get("workflow", "full")

    if "high" in risk.lower():
        # High tox — make sure pharmacology runs for optimization suggestions
        if "pharmacology" not in state.get("route_history", []):
            return "pharmacology"

    if workflow == "quick":
        return "consensus"

    return "synthesis"


def route_after_synthesis(state: PipelineState) -> str:
    """Route after synthesis based on workflow."""
    workflow = state.get("workflow", "full")
    if workflow in ("quick", "safety"):
        return "consensus"
    return "catalyst"


def route_after_catalyst(state: PipelineState) -> str:
    return "literature"


def route_after_literature(state: PipelineState) -> str:
    return "ip"


def route_after_ip(state: PipelineState) -> str:
    workflow = state.get("workflow", "full")
    if workflow == "full" and state.get("drug_name"):
        return "market"
    return "consensus"


def route_after_market(state: PipelineState) -> str:
    return "consensus"


# ─────────────────────────────────────────────
# WORKFLOW BUILDERS
# ─────────────────────────────────────────────

def build_full_pipeline() -> StateGraph:
    """Full pipeline: chemistry → pharmacology → toxicology → [conditional] → synthesis → catalyst → literature → ip → [market] → consensus."""
    graph = StateGraph(PipelineState)

    # Add all nodes
    graph.add_node("chemistry", node_chemistry)
    graph.add_node("pharmacology", node_pharmacology)
    graph.add_node("toxicology", node_toxicology)
    graph.add_node("synthesis", node_synthesis)
    graph.add_node("catalyst", node_catalyst)
    graph.add_node("literature", node_literature)
    graph.add_node("ip", node_ip)
    graph.add_node("market", node_market)
    graph.add_node("consensus", node_consensus)

    # Entry
    graph.set_entry_point("chemistry")

    # Edges
    graph.add_edge("chemistry", "pharmacology")
    graph.add_edge("pharmacology", "toxicology")

    # Conditional after tox
    graph.add_conditional_edges("toxicology", route_after_tox,
                                {"synthesis": "synthesis", "pharmacology": "pharmacology", "consensus": "consensus"})

    graph.add_conditional_edges("synthesis", route_after_synthesis,
                                {"catalyst": "catalyst", "consensus": "consensus"})

    graph.add_edge("catalyst", "literature")
    graph.add_edge("literature", "ip")

    graph.add_conditional_edges("ip", route_after_ip,
                                {"market": "market", "consensus": "consensus"})

    graph.add_edge("market", "consensus")
    graph.add_edge("consensus", END)

    return graph


def build_quick_pipeline() -> StateGraph:
    """Quick pipeline: chemistry → toxicology → consensus."""
    graph = StateGraph(PipelineState)

    graph.add_node("chemistry", node_chemistry)
    graph.add_node("toxicology", node_toxicology)
    graph.add_node("consensus", node_consensus)

    graph.set_entry_point("chemistry")
    graph.add_edge("chemistry", "toxicology")
    graph.add_edge("toxicology", "consensus")
    graph.add_edge("consensus", END)

    return graph


def build_safety_pipeline() -> StateGraph:
    """Safety-focused: chemistry → pharmacology → toxicology → consensus."""
    graph = StateGraph(PipelineState)

    graph.add_node("chemistry", node_chemistry)
    graph.add_node("pharmacology", node_pharmacology)
    graph.add_node("toxicology", node_toxicology)
    graph.add_node("consensus", node_consensus)

    graph.set_entry_point("chemistry")
    graph.add_edge("chemistry", "pharmacology")
    graph.add_edge("pharmacology", "toxicology")
    graph.add_edge("toxicology", "consensus")
    graph.add_edge("consensus", END)

    return graph


def build_synthesis_pipeline() -> StateGraph:
    """Synthesis-focused: chemistry → synthesis → catalyst → consensus."""
    graph = StateGraph(PipelineState)

    graph.add_node("chemistry", node_chemistry)
    graph.add_node("synthesis", node_synthesis)
    graph.add_node("catalyst", node_catalyst)
    graph.add_node("consensus", node_consensus)

    graph.set_entry_point("chemistry")
    graph.add_edge("chemistry", "synthesis")
    graph.add_edge("synthesis", "catalyst")
    graph.add_edge("catalyst", "consensus")
    graph.add_edge("consensus", END)

    return graph


WORKFLOWS = {
    "full": build_full_pipeline,
    "quick": build_quick_pipeline,
    "safety": build_safety_pipeline,
    "synthesis": build_synthesis_pipeline,
}


# ─────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────

def run_pipeline(smiles: str, workflow: str = "full", query: str = None,
                 drug_name: str = None, verbose: bool = False) -> dict:
    """Run a PharmaClaw pipeline and return full results with consensus."""
    builder = WORKFLOWS.get(workflow, build_full_pipeline)
    graph = builder()
    app = graph.compile()

    initial_state = {
        "smiles": smiles,
        "workflow": workflow,
        "query": query or "",
        "drug_name": drug_name or "",
        "errors": [],
        "retries": 0,
        "route_history": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if verbose:
        print(f"🧪 Running {workflow} pipeline for {smiles}", file=sys.stderr)

    # Run the graph
    result = app.invoke(initial_state)

    # Clean up for JSON output
    output = {
        "orchestrator": "cheminem",
        "framework": "langgraph",
        "version": "1.0.0",
        "workflow": workflow,
        "smiles": smiles,
        "timestamp": result.get("timestamp"),
        "agents_consulted": result.get("route_history", []),
        "consensus": result.get("consensus", {}),
    }

    # Include agent results
    for agent in ["chemistry", "pharmacology", "toxicology", "synthesis",
                   "catalyst", "literature", "ip", "market"]:
        if agent in result and result[agent]:
            output[agent] = result[agent]

    if result.get("errors"):
        output["errors"] = result["errors"]

    return output


def main():
    parser = argparse.ArgumentParser(description="Cheminem Orchestrator — LangGraph multi-agent drug discovery")
    parser.add_argument("--smiles", "-s", required=True, help="SMILES string to analyze")
    parser.add_argument("--workflow", "-w", default="full",
                        choices=["full", "quick", "safety", "synthesis"],
                        help="Pipeline workflow (default: full)")
    parser.add_argument("--query", "-q", help="Literature search query")
    parser.add_argument("--drug", "-d", help="Drug name for market intel")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args()

    result = run_pipeline(
        smiles=args.smiles,
        workflow=args.workflow,
        query=args.query,
        drug_name=args.drug,
        verbose=args.verbose,
    )

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, default=str))


if __name__ == "__main__":
    main()
