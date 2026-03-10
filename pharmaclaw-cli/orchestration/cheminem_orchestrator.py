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
from llm_consensus import llm_consensus as _llm_consensus

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
    cheminformatics: dict
    pharmacology: dict
    toxicology: dict
    synthesis: dict
    catalyst: dict
    literature: dict
    ip: dict
    market: dict

    # === CONTEXT-AWARE SHARED MEMORY (P0 upgrade) ===
    # Accumulated findings from all agents — each agent reads AND writes
    findings: list[dict]       # [{"agent": str, "type": str, "detail": str, "severity": "info"|"warning"|"critical"}]
    molecule_profile: dict     # Accumulated molecular identity: name, class, target, mechanism, key_features
    open_questions: list[str]  # Questions raised by agents for downstream agents to address

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
# CONTEXT EXTRACTION HELPERS
# ─────────────────────────────────────────────

def extract_chemistry_findings(result: dict) -> tuple[list[dict], dict, list[str]]:
    """Extract key findings, molecule profile, and open questions from chemistry results."""
    findings = []
    profile = {}
    questions = []

    props = result.get("props", {})
    retro = result.get("retro", {})

    # If chemistry script errored, try to pull from pharmacology results
    if props.get("error") or props.get("mw", 0) == 0:
        # Chemistry script failed — don't generate misleading findings from zero values
        return (
            [{"agent": "chemistry", "type": "error", "detail": "Chemistry props script failed — using pharmacology for descriptors", "severity": "warning"}],
            {},
            ["Fix rdkit_mol.py import error (rdMolStandardize)"]
        )

    mw = props.get("mw", 0)
    logp = props.get("logp", 0)
    tpsa = props.get("tpsa", 0)
    rings = props.get("num_rings", 0)
    hba = props.get("hba", 0)
    hbd = props.get("hbd", 0)
    rotb = props.get("rotatable_bonds", 0)

    # Core identity
    profile["mw"] = mw
    profile["logp"] = logp
    profile["tpsa"] = tpsa
    profile["num_rings"] = rings
    profile["hba"] = hba
    profile["hbd"] = hbd

    # Flag notable properties
    if mw > 500:
        findings.append({"agent": "chemistry", "type": "property", "detail": f"High MW ({mw:.0f}) — may limit oral bioavailability", "severity": "warning"})
        questions.append("Are there analogs with lower MW that maintain activity?")
    if logp > 5:
        findings.append({"agent": "chemistry", "type": "property", "detail": f"High LogP ({logp:.2f}) — solubility and metabolism concern", "severity": "warning"})
        questions.append("What salt forms or prodrug strategies could improve solubility?")
    if tpsa > 140:
        findings.append({"agent": "chemistry", "type": "property", "detail": f"High TPSA ({tpsa:.0f}) — may limit membrane permeability", "severity": "warning"})
    if tpsa < 20:
        findings.append({"agent": "chemistry", "type": "property", "detail": f"Very low TPSA ({tpsa:.0f}) — poor aqueous solubility likely", "severity": "warning"})

    findings.append({"agent": "chemistry", "type": "identity", "detail": f"MW={mw:.1f}, LogP={logp:.2f}, TPSA={tpsa:.1f}, Rings={rings}, HBD={hbd}, HBA={hba}", "severity": "info"})

    # Retrosynthesis findings
    precursors = retro.get("precursors", [])
    n_precursors = len(precursors) if isinstance(precursors, list) else 0
    if n_precursors > 0:
        findings.append({"agent": "chemistry", "type": "synthesis", "detail": f"BRICS retrosynthesis yielded {n_precursors} precursor fragments", "severity": "info"})
        profile["precursor_count"] = n_precursors
        profile["precursor_smiles"] = precursors[:5] if isinstance(precursors, list) else []

    # Identify functional groups / scaffold features for downstream agents
    smiles = result.get("smiles", "")
    key_features = []
    if "F" in smiles or "Cl" in smiles or "Br" in smiles:
        key_features.append("halogenated")
    if "N" in smiles:
        key_features.append("nitrogen-containing")
    if "S" in smiles:
        key_features.append("sulfur-containing")
    if "c1" in smiles.lower() or "C1=C" in smiles:
        key_features.append("aromatic")
    if "C(=O)N" in smiles:
        key_features.append("amide-bond")
    if "C=C" in smiles and "C(=O)" in smiles:
        key_features.append("michael-acceptor")
    profile["key_features"] = key_features

    return findings, profile, questions


def extract_cheminformatics_findings(result: dict) -> tuple[list[dict], dict, list[str]]:
    """Extract findings, profile additions, and questions from cheminformatics results."""
    findings = []
    profile_additions = {}
    questions = []

    report = result.get("report", {})

    # Conformer info
    conf = report.get("conformers", {})
    if conf and "error" not in conf:
        num_confs = conf.get("num_conformers", conf.get("num_generated", 0))
        min_energy = conf.get("min_energy", conf.get("best_energy"))
        findings.append({
            "agent": "cheminformatics", "type": "3d_structure",
            "detail": f"Generated {num_confs} 3D conformers" + (f", lowest energy: {min_energy:.1f} kcal/mol" if min_energy else ""),
            "severity": "info"
        })
        profile_additions["has_3d_conformers"] = True
        profile_additions["num_conformers"] = num_confs

    # Pharmacophore features
    pharm = report.get("pharmacophore", {})
    if pharm and "error" not in pharm:
        summary = pharm.get("summary", {})
        features = []
        for feat_type in ["HBD", "HBA", "Hydrophobe", "Aromatic", "PosIonizable", "NegIonizable"]:
            count = summary.get(feat_type, 0)
            if count > 0:
                features.append(f"{feat_type}:{count}")
        if features:
            findings.append({
                "agent": "cheminformatics", "type": "pharmacophore",
                "detail": f"Pharmacophore features: {', '.join(features)}",
                "severity": "info"
            })
            profile_additions["pharmacophore_features"] = summary

        # Flag if no HBD/HBA
        if summary.get("HBD", 0) == 0 and summary.get("HBA", 0) == 0:
            findings.append({
                "agent": "cheminformatics", "type": "pharmacophore",
                "detail": "No hydrogen bond donors or acceptors — unusual for drug candidates",
                "severity": "warning"
            })

    # RECAP fragments
    recap = report.get("recap", {})
    if recap and "error" not in recap:
        num_frags = recap.get("num_fragments", 0)
        leaves = recap.get("leaves", recap.get("fragments", []))
        num_leaves = len(leaves) if isinstance(leaves, list) else 0
        findings.append({
            "agent": "cheminformatics", "type": "fragmentation",
            "detail": f"RECAP fragmentation: {num_frags} cleavable bonds, {num_leaves} leaf fragments for library design",
            "severity": "info"
        })
        profile_additions["recap_fragments"] = num_leaves
        if isinstance(leaves, list) and leaves:
            profile_additions["recap_leaves"] = leaves[:8]  # Top fragments for synthesis/IP

        if num_frags == 0:
            findings.append({
                "agent": "cheminformatics", "type": "fragmentation",
                "detail": "No RECAP-cleavable bonds — molecule is a simple building block or has unusual connectivity",
                "severity": "warning"
            })
            questions.append("Is this compound available commercially as a building block?")

    # Stereoisomers
    stereo = report.get("stereoisomers", {})
    if stereo and "error" not in stereo:
        enum = stereo.get("enumeration", {})
        num_iso = enum.get("num_generated", 0)
        num_centers = enum.get("num_stereocenters", stereo.get("chiral_centers", 0))
        profile_additions["num_stereocenters"] = num_centers
        profile_additions["num_stereoisomers"] = num_iso

        if num_iso > 1:
            findings.append({
                "agent": "cheminformatics", "type": "stereochemistry",
                "detail": f"{num_centers} stereocenters → {num_iso} stereoisomers (each requires separate characterization per FDA)",
                "severity": "warning" if num_iso > 4 else "info"
            })
            questions.append(f"Which of the {num_iso} stereoisomers has the best target binding? Consider enantioselective synthesis.")
            # Stereoisomers are patentable — flag for IP
            profile_additions["stereoisomers_for_ip"] = True
        else:
            findings.append({
                "agent": "cheminformatics", "type": "stereochemistry",
                "detail": f"{num_centers} stereocenters, single stereoisomer (or achiral)",
                "severity": "info"
            })

    # Warnings from the agent itself
    for w in result.get("warnings", []):
        findings.append({"agent": "cheminformatics", "type": "warning", "detail": w, "severity": "warning"})
    for r in result.get("risks", []):
        findings.append({"agent": "cheminformatics", "type": "risk", "detail": r, "severity": "warning"})

    return findings, profile_additions, questions


def extract_pharmacology_findings(result: dict) -> tuple[list[dict], list[str], dict]:
    """Extract key findings, questions, and descriptor backup from pharmacology results.
    Returns (findings, questions, descriptor_backup) — descriptor_backup fills molecule_profile if chemistry failed."""
    findings = []
    questions = []
    descriptor_backup = {}

    report = result.get("report", result)  # Handle both nested and flat

    # Extract descriptors as backup for molecule_profile
    desc = report.get("descriptors", {})
    if desc:
        descriptor_backup = {
            "mw": desc.get("mw", 0),
            "logp": desc.get("logp", 0),
            "tpsa": desc.get("tpsa", 0),
            "hbd": desc.get("hbd", 0),
            "hba": desc.get("hba", 0),
        }

    # Lipinski
    lipinski = report.get("lipinski", {})
    if lipinski:
        passes = lipinski.get("pass", True)
        violations = lipinski.get("violations", 0)
        if not passes:
            findings.append({"agent": "pharmacology", "type": "druglikeness", "detail": f"Lipinski Ro5: FAILS ({violations} violations)", "severity": "warning"})
        else:
            findings.append({"agent": "pharmacology", "type": "druglikeness", "detail": "Lipinski Ro5: passes", "severity": "info"})

    # ADME predictions
    adme = report.get("adme", {})
    if adme:
        sol = adme.get("solubility", {})
        if sol.get("class") == "low" or sol.get("risk") == "high":
            findings.append({"agent": "pharmacology", "type": "adme", "detail": "Low aqueous solubility predicted", "severity": "warning"})
            questions.append("Search literature for formulation strategies for poorly soluble compounds in this scaffold class")

        bbb = adme.get("bbb_permeability", {})
        if bbb.get("permeable") or bbb.get("class") == "permeable":
            findings.append({"agent": "pharmacology", "type": "adme", "detail": "BBB permeable — CNS exposure likely", "severity": "info"})

        cyp = adme.get("cyp3a4_inhibition", {})
        if cyp.get("risk") == "high" or cyp.get("inhibitor"):
            findings.append({"agent": "pharmacology", "type": "adme", "detail": "CYP3A4 inhibition risk — DDI potential", "severity": "warning"})
            questions.append("What structural modifications reduce CYP3A4 inhibition in this scaffold class?")

        pgp = adme.get("pgp_substrate", {})
        if pgp.get("substrate") or pgp.get("risk") == "high":
            findings.append({"agent": "pharmacology", "type": "adme", "detail": "P-gp substrate — may limit oral absorption and CNS penetration", "severity": "warning"})

    # QED
    qed = report.get("qed", report.get("QED"))
    if qed is not None:
        if isinstance(qed, (int, float)):
            if qed < 0.3:
                findings.append({"agent": "pharmacology", "type": "druglikeness", "detail": f"Low QED ({qed:.3f}) — poor overall drug-likeness", "severity": "warning"})
            else:
                findings.append({"agent": "pharmacology", "type": "druglikeness", "detail": f"QED: {qed:.3f}", "severity": "info"})

    # PAINS
    pains = report.get("pains", report.get("pains_alerts", []))
    if pains and len(pains) > 0:
        findings.append({"agent": "pharmacology", "type": "safety", "detail": f"PAINS alerts detected: {pains}", "severity": "critical"})
        questions.append("Are these PAINS alerts known false positives for this compound class?")

    return findings, questions, descriptor_backup


def extract_toxicology_findings(result: dict) -> tuple[list[dict], list[str]]:
    """Extract key findings and questions from toxicology results."""
    findings = []
    questions = []

    risk = result.get("risk", result.get("overall_risk", ""))
    alerts = result.get("structural_alerts", result.get("alerts", []))

    if "high" in str(risk).lower():
        findings.append({"agent": "toxicology", "type": "safety", "detail": f"Overall tox risk: HIGH", "severity": "critical"})
        questions.append("What structural modifications could reduce toxicity while maintaining activity?")
        questions.append("Search for literature on toxicity mitigation for this compound class")
    elif "medium" in str(risk).lower():
        findings.append({"agent": "toxicology", "type": "safety", "detail": f"Overall tox risk: MEDIUM", "severity": "warning"})
    else:
        findings.append({"agent": "toxicology", "type": "safety", "detail": f"Overall tox risk: LOW", "severity": "info"})

    if alerts:
        alert_str = ", ".join(alerts[:5]) if isinstance(alerts, list) else str(alerts)
        findings.append({"agent": "toxicology", "type": "alerts", "detail": f"Structural alerts: {alert_str}", "severity": "warning"})

    return findings, questions


def extract_synthesis_findings(result: dict) -> tuple[list[dict], dict, list[str]]:
    """Extract key findings, route info, and questions from synthesis results."""
    findings = []
    route_info = {}
    questions = []

    route = result.get("route", [])
    feasibility = result.get("feasibility", {})

    num_steps = len(route) if isinstance(route, list) else 0
    feas_score = feasibility.get("score", "unknown")

    findings.append({"agent": "synthesis", "type": "route", "detail": f"{num_steps}-step synthesis route, feasibility: {feas_score}", "severity": "info"})

    # Extract reaction types from route for catalyst agent
    reaction_types = []
    bond_disconnections = []
    for step in (route if isinstance(route, list) else []):
        if isinstance(step, dict):
            rxn = step.get("reaction_type", step.get("type", ""))
            if rxn:
                reaction_types.append(rxn)
            precs = step.get("precursors", [])
            if precs:
                bond_disconnections.extend(precs[:3])

    route_info["num_steps"] = num_steps
    route_info["reaction_types"] = reaction_types if reaction_types else ["coupling"]  # fallback
    route_info["bond_disconnections"] = bond_disconnections[:6]
    route_info["feasibility"] = feas_score

    if feas_score == "challenging":
        questions.append("Are there simpler synthetic routes via alternative disconnections?")
        questions.append("Search literature for improved synthesis of this scaffold class")

    return findings, route_info, questions


def build_context_summary(state: PipelineState) -> str:
    """Build a concise text summary of all findings so far, for agents that benefit from context."""
    findings = state.get("findings", [])
    profile = state.get("molecule_profile", {})

    lines = []
    if profile:
        features = profile.get("key_features", [])
        lines.append(f"Molecule: MW={profile.get('mw', '?')}, LogP={profile.get('logp', '?')}, features={features}")

    warnings = [f for f in findings if f.get("severity") in ("warning", "critical")]
    if warnings:
        lines.append("Key concerns:")
        for w in warnings[:8]:
            lines.append(f"  - [{w['agent']}] {w['detail']}")

    questions = state.get("open_questions", [])
    if questions:
        lines.append("Open questions: " + "; ".join(questions[:5]))

    return "\n".join(lines)


# ─────────────────────────────────────────────
# AGENT NODE FUNCTIONS
# ─────────────────────────────────────────────

def node_chemistry(state: PipelineState) -> dict:
    """Chemistry node: molecular properties + retrosynthesis. Seeds the shared context."""
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

    # P0: Extract findings and seed the shared context
    new_findings, mol_profile, new_questions = extract_chemistry_findings(result)
    mol_profile["smiles"] = smiles
    if state.get("drug_name"):
        mol_profile["name"] = state["drug_name"]

    return {
        "chemistry": result,
        "route_history": state.get("route_history", []) + ["chemistry"],
        "findings": state.get("findings", []) + new_findings,
        "molecule_profile": {**state.get("molecule_profile", {}), **mol_profile},
        "open_questions": state.get("open_questions", []) + new_questions,
    }


def node_cheminformatics(state: PipelineState) -> dict:
    """Cheminformatics node: 3D conformers, pharmacophores, RECAP, stereoisomers.
    Enriches molecule_profile with structural features for all downstream agents."""
    smiles = state["smiles"]
    profile = state.get("molecule_profile", {})

    # Determine which actions to run based on context
    # For pipeline: run all by default; could be selective based on workflow
    actions = ["conformers", "pharmacophore", "recap", "stereoisomers", "formats"]

    input_data = {
        "smiles": smiles,
        "context": "pipeline",
        "actions": actions,
        "molecule_profile": profile,
    }
    input_json = json.dumps(input_data)
    result = _run_script("pharmaclaw-cheminformatics", "chain_entry.py",
                         ["--input-json", input_json], timeout=90)

    # P0: Extract findings and enrich molecule_profile
    new_findings, profile_additions, new_questions = extract_cheminformatics_findings(result)
    updated_profile = {**profile, **profile_additions}

    return {
        "cheminformatics": result,
        "route_history": state.get("route_history", []) + ["cheminformatics"],
        "findings": state.get("findings", []) + new_findings,
        "molecule_profile": updated_profile,
        "open_questions": state.get("open_questions", []) + new_questions,
    }


def node_pharmacology(state: PipelineState) -> dict:
    """Pharmacology node: ADME/PK profiling. Context-aware: receives molecule profile."""
    smiles = state["smiles"]
    # P0: Pass molecule profile context to pharmacology
    input_data = {
        "smiles": smiles,
        "context": "pipeline",
        "molecule_profile": state.get("molecule_profile", {}),
    }
    input_json = json.dumps(input_data)
    result = _run_script("pharmaclaw-pharmacology-agent", "chain_entry.py",
                         ["--input-json", input_json])

    # P0: Extract findings + descriptor backup for molecule_profile
    new_findings, new_questions, desc_backup = extract_pharmacology_findings(result)

    # If chemistry failed, pharmacology fills the molecule_profile
    current_profile = state.get("molecule_profile", {})
    if desc_backup and not current_profile.get("mw"):
        current_profile.update(desc_backup)

    return {
        "pharmacology": result,
        "route_history": state.get("route_history", []) + ["pharmacology"],
        "findings": state.get("findings", []) + new_findings,
        "molecule_profile": current_profile,
        "open_questions": state.get("open_questions", []) + new_questions,
    }


def node_toxicology(state: PipelineState) -> dict:
    """Toxicology node: safety profiling. Feeds findings back to shared context."""
    smiles = state["smiles"]
    result = _run_script("pharmaclaw-tox-agent", "tox_agent.py", [smiles])

    # P0: Extract findings
    new_findings, new_questions = extract_toxicology_findings(result)

    return {
        "toxicology": result,
        "route_history": state.get("route_history", []) + ["toxicology"],
        "findings": state.get("findings", []) + new_findings,
        "open_questions": state.get("open_questions", []) + new_questions,
    }


def node_synthesis(state: PipelineState) -> dict:
    """Synthesis node: multi-step route planning. Feeds route info to catalyst agent."""
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

    # P0: Extract synthesis findings + route info for catalyst agent
    new_findings, route_info, new_questions = extract_synthesis_findings(result)

    # Store route_info in molecule_profile so catalyst can read it
    updated_profile = {**state.get("molecule_profile", {}), "synthesis_route": route_info}

    return {
        "synthesis": result,
        "route_history": state.get("route_history", []) + ["synthesis"],
        "findings": state.get("findings", []) + new_findings,
        "molecule_profile": updated_profile,
        "open_questions": state.get("open_questions", []) + new_questions,
    }


def node_catalyst(state: PipelineState) -> dict:
    """Catalyst node: recommend catalysts based on ACTUAL synthesis route from shared context."""
    profile = state.get("molecule_profile", {})
    route_info = profile.get("synthesis_route", {})

    # P0: Read reaction types from synthesis route instead of hardcoding
    reactions = route_info.get("reaction_types", [])
    key_features = profile.get("key_features", [])

    # Infer additional reaction types from molecular features if route didn't specify
    if not reactions or reactions == ["coupling"]:
        reactions = []
        if "halogenated" in key_features and "aromatic" in key_features:
            reactions.append("suzuki")     # Ar-X → Ar-Ar coupling
        if "nitrogen-containing" in key_features and "halogenated" in key_features:
            reactions.append("buchwald_hartwig")  # C-N bond formation
        if "amide-bond" in key_features:
            reactions.append("amide_coupling")
        if "michael-acceptor" in key_features:
            reactions.append("michael_addition")
        if not reactions:
            reactions = ["suzuki", "buchwald_hartwig"]  # safe defaults

    # Get substrate SMILES for more targeted recommendations
    substrate = state.get("smiles", "")

    results = {"inferred_reactions": reactions, "source": "context-aware"}
    for rxn in reactions:
        args = ["--reaction", rxn]
        if substrate:
            args.extend(["--substrate", substrate])
        data = _run_script("pharmaclaw-catalyst-design", "catalyst_recommend.py", args)
        results[rxn] = data

    # P0: Add finding
    findings = state.get("findings", [])
    findings.append({
        "agent": "catalyst",
        "type": "recommendation",
        "detail": f"Catalysts recommended for {len(reactions)} reaction types: {', '.join(reactions)} (inferred from synthesis route)",
        "severity": "info"
    })

    return {
        "catalyst": results,
        "route_history": state.get("route_history", []) + ["catalyst"],
        "findings": findings,
    }


def node_literature(state: PipelineState) -> dict:
    """Literature node: CONTEXT-AWARE search. Uses findings + open questions to build targeted queries."""
    profile = state.get("molecule_profile", {})
    findings = state.get("findings", [])
    open_questions = state.get("open_questions", [])

    # P0: Build a smart, context-aware query from accumulated findings
    drug = state.get("drug_name", "") or profile.get("name", "")
    user_query = state.get("query", "")

    # Strategy: Run up to 2 targeted searches based on what the pipeline found
    queries = []

    # Query 1: Primary compound/drug query
    if user_query:
        queries.append(user_query)
    elif drug:
        queries.append(f"{drug} drug discovery synthesis ADME")
    else:
        # Build from features
        features = profile.get("key_features", [])
        if features:
            queries.append(f"{''.join(features[:2])} drug candidate ADME toxicity")

    # Query 2: Address the most important open question / warning
    # This is the key P0 upgrade — literature searches for answers to actual concerns
    critical_findings = [f for f in findings if f.get("severity") == "critical"]
    warning_findings = [f for f in findings if f.get("severity") == "warning"]

    if critical_findings:
        concern = critical_findings[0]["detail"]
        if drug:
            queries.append(f"{drug} {concern}")
        else:
            queries.append(concern)
    elif warning_findings and len(warning_findings) > 0:
        # Pick the most actionable warning
        for w in warning_findings:
            if "CYP3A4" in w["detail"]:
                queries.append(f"CYP3A4 inhibition drug design mitigation strategies")
                break
            elif "solubility" in w["detail"].lower():
                queries.append(f"improving aqueous solubility drug candidates formulation")
                break
            elif "tox" in w["detail"].lower() or "risk" in w["detail"].lower():
                queries.append(f"reducing toxicity drug design structural modifications")
                break

    # Also check open questions for targeted searches
    if open_questions and len(queries) < 2:
        # Use the first open question as a search
        q = open_questions[0]
        # Clean it up for search
        q = q.replace("Search literature for ", "").replace("Search for ", "")
        if len(q) > 20:
            queries.append(q)

    # Deduplicate and limit
    seen = set()
    unique_queries = []
    for q in queries:
        q_key = q.lower().strip()
        if q_key not in seen and q_key:
            seen.add(q_key)
            unique_queries.append(q)
    queries = unique_queries[:2]

    # Run searches
    all_results = []
    for q in queries:
        r = _run_script("pharmaclaw-literature-agent", "pubmed_search.py",
                        ["--query", q, "--max-results", "3"])
        papers = r.get("papers", r.get("results", []))
        if isinstance(papers, list):
            for p in papers:
                p["search_query"] = q  # Tag which query found this paper
            all_results.extend(papers)

    result = {
        "queries_used": queries,
        "context_driven": True,
        "papers_found": len(all_results),
        "papers": all_results,
        "open_questions_addressed": open_questions[:3],
    }

    # P0: Add finding
    new_findings = state.get("findings", [])
    new_findings.append({
        "agent": "literature",
        "type": "search",
        "detail": f"Found {len(all_results)} papers across {len(queries)} context-driven queries: {queries}",
        "severity": "info"
    })

    return {
        "literature": result,
        "route_history": state.get("route_history", []) + ["literature"],
        "findings": new_findings,
    }


def node_ip(state: PipelineState) -> dict:
    """IP node: CONTEXT-AWARE freedom-to-operate analysis. Uses findings to tailor bioisostere suggestions."""
    smiles = state["smiles"]
    profile = state.get("molecule_profile", {})
    findings = state.get("findings", [])

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

        # P0: Context-aware bioisostere suggestions
        # Tailor suggestions based on what OTHER agents flagged
        bioisosteres = []
        key_features = profile.get("key_features", [])
        warning_details = [f["detail"] for f in findings if f.get("severity") in ("warning", "critical")]

        # Always include standard suggestions
        bioisosteres.append({"from": "Cl", "to": "CF3", "rationale": "Similar lipophilicity, novel IP space"})
        bioisosteres.append({"from": "phenyl", "to": "pyridyl", "rationale": "Improved solubility, different IP space"})

        # Add targeted suggestions based on pipeline findings
        if any("solubility" in w.lower() for w in warning_details):
            bioisosteres.append({"from": "phenyl", "to": "pyrimidyl", "rationale": "Addresses low solubility (flagged by pharmacology) + novel IP"})
            bioisosteres.append({"from": "tBu", "to": "cyclopropyl", "rationale": "Reduces LogP to improve solubility + smaller analog"})

        if any("CYP3A4" in w for w in warning_details):
            bioisosteres.append({"from": "N-methyl", "to": "N-cyclopropyl", "rationale": "May reduce CYP3A4 inhibition (flagged by pharmacology) + novel IP"})
            bioisosteres.append({"from": "methoxy", "to": "difluoromethoxy", "rationale": "Metabolic stability vs CYP3A4 + novel IP"})

        if any("tox" in w.lower() and "high" in w.lower() for w in warning_details):
            bioisosteres.append({"from": "aniline", "to": "aminopyridine", "rationale": "Reduces tox liability (flagged by toxicology) + novel IP"})

        if any("michael-acceptor" in f for f in key_features):
            bioisosteres.append({"from": "acrylamide", "to": "vinyl sulfonamide", "rationale": "Alternative warhead, different IP, potentially lower reactivity"})

        # Deduplicate
        seen = set()
        unique_bio = []
        for b in bioisosteres:
            key = (b["from"], b["to"])
            if key not in seen:
                seen.add(key)
                unique_bio.append(b)

        result = {
            "max_similarity": round(max_sim, 4),
            "overall_risk": "HIGH" if max_sim >= 0.85 else "MODERATE" if max_sim >= 0.5 else "LOW",
            "comparisons": comparisons,
            "bioisostere_suggestions": unique_bio,
            "context_driven": True,
            "concerns_addressed": [w for w in warning_details[:5]],
        }
    except Exception as e:
        result = {"error": str(e)}

    # P0: Add findings
    new_findings = state.get("findings", [])
    overall_risk = result.get("overall_risk", "UNKNOWN")
    new_findings.append({
        "agent": "ip",
        "type": "fto",
        "detail": f"FTO risk: {overall_risk} (max Tanimoto: {result.get('max_similarity', '?')}), {len(result.get('bioisostere_suggestions', []))} context-aware bioisostere suggestions",
        "severity": "critical" if overall_risk == "HIGH" else "warning" if overall_risk == "MODERATE" else "info"
    })

    return {
        "ip": result,
        "route_history": state.get("route_history", []) + ["ip"],
        "findings": new_findings,
    }


def node_market(state: PipelineState) -> dict:
    """Market intel node: FAERS adverse events. Context-aware: adds safety signal findings."""
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

    # P0: Extract FAERS findings for consensus
    new_findings = state.get("findings", [])
    total_reports = result.get("total_reports", result.get("total", 0))
    top_reactions = result.get("top_reactions", [])

    if total_reports:
        new_findings.append({
            "agent": "market",
            "type": "safety_signal",
            "detail": f"FAERS: {total_reports} total adverse event reports for {drug}",
            "severity": "info" if total_reports < 1000 else "warning"
        })
    if top_reactions and isinstance(top_reactions, list):
        top_3 = [r.get("reaction", r.get("term", "?")) for r in top_reactions[:3]]
        new_findings.append({
            "agent": "market",
            "type": "safety_signal",
            "detail": f"Top FAERS signals: {', '.join(top_3)}",
            "severity": "warning"
        })

    return {
        "market": result,
        "route_history": state.get("route_history", []) + ["market"],
        "findings": new_findings,
    }


# ─────────────────────────────────────────────
# CONSENSUS & SCORING
# ─────────────────────────────────────────────

def _rule_based_consensus(state: PipelineState) -> dict:
    """Rule-based fallback consensus when LLM is unavailable."""
    findings = state.get("findings", [])
    profile = state.get("molecule_profile", {})
    open_questions = state.get("open_questions", [])

    score = 10.0
    recommendations = []
    warnings = []

    # P0: Score based on accumulated findings from ALL agents
    for f in findings:
        sev = f.get("severity", "info")
        detail = f.get("detail", "")
        agent = f.get("agent", "unknown")

        if sev == "critical":
            score -= 2.0
            warnings.append(f"[{agent}] {detail}")
        elif sev == "warning":
            score -= 0.5
            warnings.append(f"[{agent}] {detail}")
        # info findings don't affect score

    # Additional rule-based checks (keep for backward compat, but findings do most work)
    chem = state.get("chemistry", {})
    props = chem.get("props", {})
    mw = props.get("mw", 0)
    logp = props.get("logp", 0)

    # Only penalize if NOT already penalized by findings
    mw_warned = any("MW" in f.get("detail", "") for f in findings if f.get("severity") != "info")
    logp_warned = any("LogP" in f.get("detail", "") for f in findings if f.get("severity") != "info")

    if mw > 500 and not mw_warned:
        score -= 1.0
        warnings.append(f"High MW ({mw:.0f}) — oral bioavailability concern")
    if logp > 5 and not logp_warned:
        score -= 1.0
        warnings.append(f"High LogP ({logp:.2f}) — solubility concern")

    # P0: Generate recommendations from open questions
    for q in open_questions[:5]:
        if q not in recommendations:
            recommendations.append(q)

    # Add targeted recommendations based on IP results
    ip_data = state.get("ip", {})
    bioisosteres = ip_data.get("bioisostere_suggestions", [])
    if bioisosteres and ip_data.get("overall_risk") in ("HIGH", "MODERATE"):
        top_bio = bioisosteres[:3]
        for b in top_bio:
            recommendations.append(f"Bioisostere: replace {b['from']} → {b['to']} ({b['rationale']})")

    # Add literature-based recommendations
    lit = state.get("literature", {})
    if lit.get("context_driven"):
        queries = lit.get("queries_used", [])
        papers = lit.get("papers", [])
        if papers:
            recommendations.append(f"Literature search found {len(papers)} relevant papers via context-driven queries: {queries}")

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

    # Deduplicate warnings and recommendations
    warnings = list(dict.fromkeys(warnings))
    recommendations = list(dict.fromkeys(recommendations))

    consensus = {
        "score": round(score, 1),
        "verdict": verdict,
        "warnings": warnings[:15],
        "recommendations": recommendations[:10],
        "agents_consulted": state.get("route_history", []),
        "total_findings": len(findings),
        "critical_count": sum(1 for f in findings if f.get("severity") == "critical"),
        "warning_count": sum(1 for f in findings if f.get("severity") == "warning"),
        "context_summary": build_context_summary(state),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return {"consensus": consensus, "score": score}


def node_consensus(state: PipelineState) -> dict:
    """P1: Try LLM-powered consensus first, fall back to rule-based.
    
    LLM consensus gives nuanced, contextual scoring by reasoning over all
    agent findings like a senior medicinal chemist. Rule-based is the
    reliable fallback when no LLM is configured or the call fails.
    """
    verbose = state.get("workflow", "") != "quick"
    skip_llm = os.environ.get("PHARMACLAW_SKIP_LLM", "") == "1"

    # Try LLM consensus (unless explicitly skipped)
    llm_result = None
    if not skip_llm:
        llm_result = _llm_consensus(state, verbose=verbose)

    if llm_result is not None:
        # LLM succeeded — use its consensus but add context_summary for compatibility
        llm_result["context_summary"] = build_context_summary(state)
        return {"consensus": llm_result, "score": llm_result.get("score", 5.0)}

    # Fall back to rule-based
    if verbose:
        import sys
        print("[Consensus] Using rule-based scoring (no LLM configured)", file=sys.stderr)
    return _rule_based_consensus(state)


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
    """Full pipeline: chemistry → cheminformatics → pharmacology → toxicology → [conditional] → synthesis → catalyst → literature → ip → [market] → consensus."""
    graph = StateGraph(PipelineState)

    # Add all nodes (9 agents + consensus)
    graph.add_node("chemistry", node_chemistry)
    graph.add_node("cheminformatics", node_cheminformatics)
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

    # Edges: chemistry → cheminformatics → pharmacology → toxicology
    graph.add_edge("chemistry", "cheminformatics")
    graph.add_edge("cheminformatics", "pharmacology")
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
    """Safety-focused: chemistry → cheminformatics → pharmacology → toxicology → consensus."""
    graph = StateGraph(PipelineState)

    graph.add_node("chemistry", node_chemistry)
    graph.add_node("cheminformatics", node_cheminformatics)
    graph.add_node("pharmacology", node_pharmacology)
    graph.add_node("toxicology", node_toxicology)
    graph.add_node("consensus", node_consensus)

    graph.set_entry_point("chemistry")
    graph.add_edge("chemistry", "cheminformatics")
    graph.add_edge("cheminformatics", "pharmacology")
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
        "version": "2.0.0",  # P0: Context-aware upgrade
        "workflow": workflow,
        "smiles": smiles,
        "timestamp": result.get("timestamp"),
        "agents_consulted": result.get("route_history", []),
        "consensus": result.get("consensus", {}),
    }

    # P0: Include shared context in output
    if result.get("findings"):
        output["findings"] = result["findings"]
    if result.get("molecule_profile"):
        output["molecule_profile"] = result["molecule_profile"]
    if result.get("open_questions"):
        output["open_questions"] = result["open_questions"]

    # Include agent results
    for agent in ["chemistry", "cheminformatics", "pharmacology", "toxicology", "synthesis",
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
    parser.add_argument("--consensus", choices=["auto", "llm", "rules"],
                        default="auto",
                        help="Consensus method: auto (try LLM, fallback rules), llm (require LLM), rules (skip LLM)")
    parser.add_argument("--llm-model", help="Override LLM model for consensus (e.g., anthropic/claude-sonnet-4-20250514, openai/gpt-4o)")
    args = parser.parse_args()

    # Set consensus preferences via env
    if args.consensus == "rules":
        os.environ["PHARMACLAW_LLM_MODEL"] = ""  # Force rule-based
        os.environ["PHARMACLAW_SKIP_LLM"] = "1"
    if args.llm_model:
        os.environ["PHARMACLAW_LLM_MODEL"] = args.llm_model

    result = run_pipeline(
        smiles=args.smiles,
        workflow=args.workflow,
        query=args.query,
        drug_name=args.drug,
        verbose=args.verbose,
    )

    # If --consensus=llm and it fell back to rules, error out
    if args.consensus == "llm" and result.get("consensus", {}).get("consensus_method") != "llm":
        print(json.dumps({"error": "LLM consensus required but failed. Check API key and model configuration."}))
        sys.exit(1)

    indent = 2 if args.pretty else None
    print(json.dumps(result, indent=indent, default=str))


if __name__ == "__main__":
    main()
