#!/usr/bin/env python3
"""PharmaClaw Agent Tools — LangChain tool wrappers for all 8 agents.

Each tool wraps the existing agent scripts via subprocess, returning structured JSON.
Tools are designed for use in LangGraph state graphs.
"""

import json
import subprocess
import sys
import os
import re
from typing import Optional
from langchain_core.tools import tool

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills")
PYTHON = sys.executable


def _run_script(skill: str, script: str, args: list, timeout: int = 60) -> dict:
    """Run a skill script and return parsed JSON."""
    script_path = os.path.join(SKILLS_DIR, skill, "scripts", script)
    cmd = [PYTHON, script_path] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = result.stdout.strip()
        if output:
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"raw_output": output}
        if result.returncode != 0:
            return {"error": result.stderr.strip() or "Script failed with no output"}
        return {"error": "No output from script"}
    except subprocess.TimeoutExpired:
        return {"error": f"Script timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


def _validate_smiles(smiles: str) -> str | None:
    """Validate SMILES, return error message or None if valid."""
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return f"Invalid SMILES: '{smiles}'"
        return None
    except Exception as e:
        return f"SMILES validation error: {e}"


# ─────────────────────────────────────────────
# CHEMISTRY TOOL
# ─────────────────────────────────────────────
@tool
def chemistry_props(smiles: str) -> dict:
    """Compute molecular properties (MW, LogP, TPSA, HBD, HBA, rotatable bonds, aromatic rings) from a SMILES string using RDKit."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    return _run_script("pharmaclaw-chemistry-query", "rdkit_mol.py",
                       ["--smiles", smiles, "--action", "props"])


@tool
def chemistry_retro(smiles: str, depth: int = 2) -> dict:
    """Run BRICS retrosynthesis on a SMILES string. Returns precursor fragments at the given depth."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    return _run_script("pharmaclaw-chemistry-query", "rdkit_mol.py",
                       ["--smiles", smiles, "--action", "retro", "--depth", str(depth)])


@tool
def chemistry_plan(smiles: str, steps: int = 3) -> dict:
    """Plan a multi-step synthesis route using BRICS retrosynthesis. Returns step-by-step precursors and conditions."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    return _run_script("pharmaclaw-chemistry-query", "rdkit_mol.py",
                       ["--smiles", smiles, "--action", "plan", "--steps", str(steps)])


@tool
def chemistry_similarity(query_smiles: str, target_smiles_csv: str) -> dict:
    """Compute Tanimoto similarity between a query SMILES and comma-separated target SMILES using Morgan fingerprints."""
    return _run_script("pharmaclaw-chemistry-query", "rdkit_mol.py",
                       ["--query_smiles", query_smiles, "--target_smiles", target_smiles_csv, "--action", "similarity"])


@tool
def pubchem_lookup(compound: str, query_type: str = "info") -> dict:
    """Look up a compound on PubChem. Types: info (properties), structure (SMILES/InChI), synthesis (references), similar (analogs)."""
    return _run_script("pharmaclaw-chemistry-query", "query_pubchem.py",
                       ["--compound", compound, "--type", query_type])


# ─────────────────────────────────────────────
# CHEMINFORMATICS TOOLS
# ─────────────────────────────────────────────
@tool
def cheminformatics_profile(smiles: str, actions: str = "conformers,pharmacophore,recap,stereoisomers,formats") -> dict:
    """Run full cheminformatics profile: 3D conformers (ETKDG+MMFF), pharmacophore features, RECAP fragmentation, stereoisomer enumeration, format conversion. Returns comprehensive structural analysis."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    action_list = [a.strip() for a in actions.split(",")]
    input_json = json.dumps({"smiles": smiles, "actions": action_list})
    return _run_script("pharmaclaw-cheminformatics", "chain_entry.py",
                       ["--input-json", input_json], timeout=90)


@tool
def conformer_generate(smiles: str, num_confs: int = 20, optimize: str = "mmff") -> dict:
    """Generate 3D conformer ensemble using ETKDG with MMFF/UFF optimization. Returns conformer energies, RMSD matrix, and statistics."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    return _run_script("pharmaclaw-cheminformatics", "conformer_gen.py",
                       ["--smiles", smiles, "--num_confs", str(num_confs), "--optimize", optimize, "--action", "generate"])


@tool
def pharmacophore_features(smiles: str) -> dict:
    """Extract pharmacophore features (HBD, HBA, hydrophobic, aromatic, ionizable) from a molecule. Returns feature counts, positions, and pharmacophore fingerprint."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    return _run_script("pharmaclaw-cheminformatics", "pharmacophore.py",
                       ["--smiles", smiles, "--action", "features"])


@tool
def recap_fragment(smiles: str) -> dict:
    """Fragment molecule at synthetically accessible bonds using RECAP rules. Returns fragment tree, leaf nodes for combinatorial library design."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    return _run_script("pharmaclaw-cheminformatics", "recap_fragment.py",
                       ["--smiles", smiles, "--action", "leaves"])


@tool
def stereoisomer_enumerate(smiles: str, max_isomers: int = 32) -> dict:
    """Enumerate all stereoisomers (R/S, E/Z) for a molecule. Identifies chiral centers and double bond geometries."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    return _run_script("pharmaclaw-cheminformatics", "stereoisomers.py",
                       ["--smiles", smiles, "--action", "enumerate", "--max_isomers", str(max_isomers)])


# ─────────────────────────────────────────────
# PHARMACOLOGY TOOL
# ─────────────────────────────────────────────
@tool
def pharmacology_profile(smiles: str) -> dict:
    """Run full ADME/PK profile: Lipinski Ro5, Veber rules, QED, SA Score, BBB permeability, solubility, CYP3A4 inhibition, P-gp substrate, plasma protein binding, PAINS alerts."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    input_json = json.dumps({"smiles": smiles})
    return _run_script("pharmaclaw-pharmacology-agent", "chain_entry.py",
                       ["--input-json", input_json])


# ─────────────────────────────────────────────
# TOXICOLOGY TOOL
# ─────────────────────────────────────────────
@tool
def toxicology_analyze(smiles: str) -> dict:
    """Analyze toxicology/safety profile: Lipinski violations, Veber violations, QED, PAINS alerts, risk level (Low/Medium/High), and detailed molecular properties."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    return _run_script("pharmaclaw-tox-agent", "tox_agent.py", [smiles])


# ─────────────────────────────────────────────
# SYNTHESIS TOOL
# ─────────────────────────────────────────────
@tool
def synthesis_plan(smiles: str, steps: int = 3) -> dict:
    """Plan multi-step synthesis route with feasibility scoring. Uses BRICS retrosynthesis with step-by-step precursor analysis."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    data = _run_script("pharmaclaw-chemistry-query", "rdkit_mol.py",
                       ["--smiles", smiles, "--action", "plan", "--steps", str(steps)],
                       timeout=120)
    # Add feasibility scoring
    route = data.get("route", [])
    num_steps = len(route)
    total_precursors = sum(len(s.get("precursors", [])) for s in route)
    if num_steps <= 3 and total_precursors <= 10:
        feasibility = {"score": "high", "confidence": 0.75}
    elif num_steps <= 5:
        feasibility = {"score": "moderate", "confidence": 0.55}
    else:
        feasibility = {"score": "challenging", "confidence": 0.35}
    data["feasibility"] = feasibility
    return data


# ─────────────────────────────────────────────
# CATALYST DESIGN TOOL
# ─────────────────────────────────────────────
@tool
def catalyst_recommend(reaction: str, substrate: Optional[str] = None, enantioselective: bool = False) -> dict:
    """Recommend organometallic catalysts for a reaction type (suzuki, heck, buchwald_hartwig, metathesis, hydrogenation, click, etc). Optionally filter by substrate SMILES."""
    args = ["--reaction", reaction]
    if substrate:
        args += ["--substrate", substrate]
    if enantioselective:
        args.append("--enantioselective")
    return _run_script("pharmaclaw-catalyst-design", "catalyst_recommend.py", args)


@tool
def ligand_design(scaffold: str, strategy: str = "all") -> dict:
    """Design novel ligand variants from a scaffold (PPh3, NHC_IMes, PCy3, etc). Strategies: steric, electronic, bioisosteric, all."""
    return _run_script("pharmaclaw-catalyst-design", "ligand_designer.py",
                       ["--scaffold", scaffold, "--strategy", strategy])


# ─────────────────────────────────────────────
# LITERATURE TOOL
# ─────────────────────────────────────────────
@tool
def literature_search(query: str, source: str = "pubmed", max_results: int = 5) -> dict:
    """Search scientific literature. Sources: pubmed (biomedical), scholar (Semantic Scholar for CS/ML/AI). Returns papers with titles, abstracts, DOIs, citations."""
    if source == "scholar":
        return _run_script("pharmaclaw-literature-agent", "semantic_scholar.py",
                           ["--query", query, "--max-results", str(max_results)])
    else:
        return _run_script("pharmaclaw-literature-agent", "pubmed_search.py",
                           ["--query", query, "--max-results", str(max_results)])


# ─────────────────────────────────────────────
# IP CHECK TOOL
# ─────────────────────────────────────────────
@tool
def ip_fto_analysis(smiles: str, threshold: float = 0.85) -> dict:
    """Run Freedom-to-Operate analysis: Morgan fingerprint Tanimoto similarity against known drug patents. Returns risk level and bioisostere suggestions."""
    err = _validate_smiles(smiles)
    if err:
        return {"error": err}
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        mol = Chem.MolFromSmiles(smiles)
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

        # Reference patents
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
                risk = "HIGH" if sim >= threshold else "MODERATE" if sim >= 0.5 else "LOW"
                comparisons.append({"reference": name, "tanimoto": round(sim, 4), "risk": risk})

        comparisons.sort(key=lambda x: x["tanimoto"], reverse=True)
        max_sim = comparisons[0]["tanimoto"] if comparisons else 0

        # Bioisostere suggestions
        bioisosteres = [
            {"from": "Cl", "to": "CF3", "rationale": "Similar size/lipophilicity, different IP"},
            {"from": "phenyl", "to": "pyridyl", "rationale": "Improved solubility, different IP space"},
            {"from": "amide", "to": "sulfonamide", "rationale": "Different geometry, similar H-bonding"},
            {"from": "CF3", "to": "OCF3", "rationale": "Modulates electronics, novel IP space"},
        ]

        return {
            "query_smiles": smiles,
            "max_similarity": round(max_sim, 4),
            "overall_risk": "HIGH" if max_sim >= threshold else "MODERATE" if max_sim >= 0.5 else "LOW",
            "comparisons": comparisons,
            "bioisostere_suggestions": bioisosteres,
        }
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# MARKET INTEL TOOL
# ─────────────────────────────────────────────
@tool
def market_intel(drug: str, limit: int = 10) -> dict:
    """Query FDA FAERS for adverse events and market trends for a drug (name or SMILES). Returns event frequencies, yearly trends, and top reactions."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        data = _run_script("pharmaclaw-market-intel-agent", "query_faers.py",
                           ["--drug", drug, "--output", tmpdir, "--limit-events", str(limit)],
                           timeout=60)
        # Check for output files
        for fname in os.listdir(tmpdir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(tmpdir, fname)) as f:
                        data[fname.replace(".json", "")] = json.load(f)
                except Exception:
                    pass
        return data


# Collect all tools for easy import
ALL_TOOLS = [
    chemistry_props,
    chemistry_retro,
    chemistry_plan,
    chemistry_similarity,
    pubchem_lookup,
    cheminformatics_profile,
    conformer_generate,
    pharmacophore_features,
    recap_fragment,
    stereoisomer_enumerate,
    pharmacology_profile,
    toxicology_analyze,
    synthesis_plan,
    catalyst_recommend,
    ligand_design,
    literature_search,
    ip_fto_analysis,
    market_intel,
]
