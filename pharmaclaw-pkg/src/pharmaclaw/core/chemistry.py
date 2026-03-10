"""
Chemistry Agent — Molecular properties, retrosynthesis, fingerprints, similarity, PubChem queries.

Usage:
    >>> from pharmaclaw.core.chemistry import get_props, get_retro, get_fingerprint
    >>> props = get_props("CCO")
    >>> retro = get_retro("CC(=O)Oc1ccccc1C(=O)O", depth=2)
"""

import json
import re
from typing import Optional

from rdkit import Chem, DataStructs
from rdkit.Chem import Descriptors, Draw, AllChem, BRICS
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem import rdChemReactions
from rdkit.Chem.Scaffolds import MurckoScaffold

# Optional advanced modules (full RDKit / conda-forge only)
try:
    from rdkit.Chem import rdMolStandardize
    _HAS_STANDARDIZE = True
except ImportError:
    _HAS_STANDARDIZE = False

try:
    from rdkit.Chem import rdFMCS
    _HAS_FMCS = True
except ImportError:
    _HAS_FMCS = False

try:
    from rdkit.Chem import rdMMPA
    _HAS_MMPA = True
except ImportError:
    _HAS_MMPA = False


# ── Helpers ────────────────────────────────────────────────

def _validate_smiles(smiles: str) -> Chem.Mol:
    """Parse and validate a SMILES string, returning an RDKit Mol."""
    if not smiles or not isinstance(smiles, str):
        raise ValueError("SMILES string is required")
    smiles = smiles.strip()
    if len(smiles) > 2000:
        raise ValueError("SMILES exceeds 2000 character limit")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    return mol


def _resolve_target(target: str) -> str:
    """Resolve a compound name or SMILES to a canonical SMILES string."""
    target = target.strip()
    mol = Chem.MolFromSmiles(target)
    if mol is not None:
        return Chem.MolToSmiles(mol, isomericSmiles=True)
    # Try PubChem lookup
    try:
        from pharmaclaw.core._pubchem import name_to_smiles
        return name_to_smiles(target)
    except Exception as e:
        raise ValueError(f"Could not resolve '{target}' to SMILES: {e}")


def _brics_retro(mol, depth: int) -> list[str]:
    """Recursive BRICS retrosynthesis. Returns list of fragment SMILES."""
    if depth <= 0:
        return [Chem.MolToSmiles(mol, isomericSmiles=True)]
    try:
        frags = BRICS.BRICSDecompose(mol)
        if not frags or len(frags) <= 1:
            return [Chem.MolToSmiles(mol, isomericSmiles=True)]
        precursors = []
        for frag_smi in frags:
            clean_smi = re.sub(r'\[\d+\*\]', '[H]', frag_smi)
            frag_mol = Chem.MolFromSmiles(clean_smi)
            if frag_mol is not None:
                precursors += _brics_retro(frag_mol, depth - 1)
            else:
                precursors.append(frag_smi)
        return list(set(precursors))
    except Exception:
        return [Chem.MolToSmiles(mol, isomericSmiles=True)]


# ── Public API ─────────────────────────────────────────────

def get_props(smiles: str) -> dict:
    """Compute basic molecular properties from SMILES.

    Returns dict with: mw, logp, tpsa, hbd, hba, rotb, arom_rings, canonical_smiles.
    """
    mol = _validate_smiles(smiles)
    canonical = Chem.MolToSmiles(mol, isomericSmiles=True)
    return {
        "agent": "chemistry",
        "command": "props",
        "smiles": canonical,
        "mw": round(Descriptors.ExactMolWt(mol), 2),
        "logp": round(Descriptors.MolLogP(mol), 4),
        "tpsa": round(Descriptors.TPSA(mol), 2),
        "hbd": Descriptors.NumHDonors(mol),
        "hba": Descriptors.NumHAcceptors(mol),
        "rotb": Descriptors.NumRotatableBonds(mol),
        "arom_rings": Descriptors.NumAromaticRings(mol),
    }


def get_fingerprint(smiles: str, radius: int = 2, n_bits: int = 2048) -> dict:
    """Compute Morgan fingerprint for a molecule."""
    mol = _validate_smiles(smiles)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return {
        "agent": "chemistry",
        "command": "fingerprint",
        "smiles": smiles,
        "bitstring": fp.ToBitString(),
        "num_bits": fp.GetNumBits(),
        "bits_set": sorted(list(fp.GetOnBits())),
    }


def get_similarity(query_smiles: str, target_smiles: str | list[str], radius: int = 2) -> dict:
    """Compute Tanimoto similarity between query and one or more targets.

    Args:
        target_smiles: Single SMILES string (comma-separated OK) or list of SMILES.
    """
    qmol = _validate_smiles(query_smiles)
    if isinstance(target_smiles, str):
        target_list = [s.strip() for s in target_smiles.split(",") if s.strip()]
    else:
        target_list = target_smiles

    qfp = AllChem.GetMorganFingerprintAsBitVect(qmol, radius, nBits=2048)
    results = []
    for t_smi in target_list:
        t_mol = _validate_smiles(t_smi)
        t_fp = AllChem.GetMorganFingerprintAsBitVect(t_mol, radius, nBits=2048)
        sim = DataStructs.TanimotoSimilarity(qfp, t_fp)
        results.append({"target": t_smi, "tanimoto": round(sim, 4)})
    results.sort(key=lambda x: x["tanimoto"], reverse=True)
    return {
        "agent": "chemistry",
        "command": "similarity",
        "query_smiles": query_smiles,
        "results": results,
        "max_similarity": results[0]["tanimoto"] if results else 0,
    }


def get_retro(smiles: str, depth: int = 1) -> dict:
    """Run BRICS retrosynthesis on a molecule.

    Args:
        smiles: Target molecule SMILES (or compound name).
        depth: Recursion depth for disconnection (1-3 recommended).
    """
    target_smiles = _resolve_target(smiles)
    mol = _validate_smiles(target_smiles)
    precursors = _brics_retro(mol, depth)
    return {
        "agent": "chemistry",
        "command": "retro",
        "target": target_smiles,
        "depth": depth,
        "precursors": sorted(precursors),
        "num_precursors": len(precursors),
    }


def get_plan(smiles: str, steps: int = 3) -> dict:
    """Generate a multi-step synthesis plan via iterative BRICS disconnection.

    Args:
        smiles: Target molecule SMILES (or compound name).
        steps: Number of retrosynthetic steps (1-5).
    """
    target_smiles = _resolve_target(smiles)
    mol = _validate_smiles(target_smiles)
    current_products = [target_smiles]
    route = []
    for step_num in range(1, steps + 1):
        precursors_step = []
        for prod_smi in current_products:
            prod_mol = _validate_smiles(prod_smi)
            step_precs = _brics_retro(prod_mol, 1)
            precursors_step.extend(step_precs)
        precursors_step = list(set(precursors_step))
        route.append({
            "step": step_num,
            "precursors": precursors_step[:10],
            "condition": "BRICS template (ester/amide/etc disconnects)",
            "yield_estimate": "N/A (BRICS)",
            "product": current_products[0],
        })
        current_products = precursors_step[:5]
    return {
        "agent": "chemistry",
        "command": "plan",
        "target": target_smiles,
        "steps": steps,
        "templates_used": "BRICS",
        "route": route,
    }


def get_xyz(smiles: str) -> dict:
    """Generate 3D coordinates (XYZ block) for a molecule."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)
    xyz = Chem.MolToXYZBlock(mol)
    return {
        "agent": "chemistry",
        "command": "xyz",
        "smiles": smiles,
        "xyz": xyz.strip(),
        "num_atoms": mol.GetNumAtoms(),
    }


def draw_molecule(smiles: str, output: Optional[str] = None, fmt: str = "svg") -> dict:
    """Render a 2D depiction of a molecule.

    Args:
        fmt: 'svg' or 'png'.
        output: Optional file path to save the image.
    """
    mol = _validate_smiles(smiles)
    if fmt == "svg":
        drawer = rdMolDraw2D.MolDraw2DSVG(300, 300)
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        svg = drawer.GetDrawingText()
        if output:
            with open(output, "w") as f:
                f.write(svg)
        return {"agent": "chemistry", "command": "draw", "svg": svg, "format": "svg", "success": True}
    else:
        img = Draw.MolToImage(mol, size=(300, 300))
        if output:
            img.save(output)
        return {"agent": "chemistry", "command": "draw", "format": "png", "output": output, "success": True}


def run_reaction(smarts: str, reactant_smiles: list[str]) -> dict:
    """Run a reaction using a SMARTS template.

    Args:
        smarts: Reaction SMARTS string.
        reactant_smiles: List of reactant SMILES strings.
    """
    rxn = rdChemReactions.ReactionFromSmarts(smarts)
    if rxn is None:
        raise ValueError("Invalid SMARTS reaction template")
    reactant_mols = [_validate_smiles(s) for s in reactant_smiles]
    products = rxn.RunReactants(reactant_mols)
    product_smiles = []
    for prod_tuple in products:
        for mol in prod_tuple:
            if mol is not None:
                try:
                    Chem.SanitizeMol(mol)
                    if mol.GetNumAtoms() > 0:
                        product_smiles.append(Chem.MolToSmiles(mol, isomericSmiles=True))
                except Exception:
                    pass
    return {
        "agent": "chemistry",
        "command": "reaction",
        "products": product_smiles,
        "num_products": len(product_smiles),
    }


def standardize(smiles: str) -> dict:
    """Standardize a molecule and enumerate tautomers.

    Requires full RDKit (conda-forge). Falls back to canonical SMILES if unavailable.
    """
    mol = _validate_smiles(smiles)
    canonical = Chem.MolToSmiles(mol, isomericSmiles=True)

    if not _HAS_STANDARDIZE:
        return {
            "agent": "chemistry",
            "command": "standardize",
            "input_smiles": smiles,
            "standardized": canonical,
            "tautomers": [canonical],
            "num_tautomers": 1,
            "note": "rdMolStandardize not available. Install full RDKit (conda-forge) for normalization/tautomers.",
        }

    normalizer = rdMolStandardize.Normalizer()
    norm_mol = normalizer.normalize(mol)
    uncharger = rdMolStandardize.Uncharger()
    uncharged = uncharger.uncharge(norm_mol)
    chooser = rdMolStandardize.LargestFragmentChooser()
    parent = chooser.choose(uncharged)
    canonical = Chem.MolToSmiles(parent, isomericSmiles=True)
    enumerator = rdMolStandardize.TautomerEnumerator()
    tauts = list(enumerator.Enumerate(parent))
    taut_smiles = sorted(set(Chem.MolToSmiles(t, isomericSmiles=True) for t in tauts))
    return {
        "agent": "chemistry",
        "command": "standardize",
        "input_smiles": smiles,
        "standardized": canonical,
        "tautomers": taut_smiles[:20],
        "num_tautomers": len(taut_smiles),
    }


def scaffold_analysis(smiles: str | list[str]) -> dict:
    """Compute Murcko scaffold(s) for one or more molecules."""
    if isinstance(smiles, str):
        smiles_list = [s.strip() for s in smiles.split(",") if s.strip()]
    else:
        smiles_list = smiles
    results = []
    for smi in smiles_list:
        mol = _validate_smiles(smi)
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        generic = MurckoScaffold.MakeScaffoldGeneric(scaffold)
        results.append({
            "smiles": smi,
            "murcko_scaffold": Chem.MolToSmiles(scaffold),
            "generic_scaffold": Chem.MolToSmiles(generic),
        })
    return {
        "agent": "chemistry",
        "command": "scaffold",
        "results": results,
        "num_unique_scaffolds": len(set(r["murcko_scaffold"] for r in results)),
    }


def mcs(smiles_list: list[str]) -> dict:
    """Find Maximum Common Substructure across a set of molecules.

    Requires full RDKit (conda-forge) for rdFMCS.
    """
    if not _HAS_FMCS:
        raise ImportError("MCS requires rdFMCS. Install full RDKit via conda: conda install -c conda-forge rdkit")
    mols = [_validate_smiles(s) for s in smiles_list]
    result = rdFMCS.FindMCS(mols, timeout=30)
    return {
        "agent": "chemistry",
        "command": "mcs",
        "smarts": result.smartsString,
        "num_atoms": result.numAtoms,
        "num_bonds": result.numBonds,
        "num_molecules": len(mols),
    }
