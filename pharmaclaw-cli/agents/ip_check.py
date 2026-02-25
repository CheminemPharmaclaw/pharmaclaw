#!/usr/bin/env python3
"""IP Expansion Agent Wrapper - FTO analysis, similarity, bioisosteres."""

import json
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "pharmaclaw-ip-expansion-agent", "scripts")


def fto_analysis(smiles: str, compare_smiles: list = None, threshold: float = 0.85) -> dict:
    """Run Freedom-to-Operate analysis using Morgan fingerprint similarity."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, DataStructs

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": f"Invalid SMILES: {smiles}", "agent": "ip"}

        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

        # If no comparison set, use known drug SMILES as reference
        if not compare_smiles:
            compare_smiles = _get_reference_patents()

        results = []
        for ref_smi in compare_smiles:
            ref_mol = Chem.MolFromSmiles(ref_smi)
            if ref_mol is None:
                continue
            ref_fp = AllChem.GetMorganFingerprintAsBitVect(ref_mol, 2, nBits=2048)
            sim = DataStructs.TanimotoSimilarity(fp, ref_fp)
            risk = "HIGH" if sim >= threshold else "MODERATE" if sim >= 0.5 else "LOW"
            results.append({
                "reference_smiles": ref_smi,
                "tanimoto": round(sim, 4),
                "risk": risk
            })

        results.sort(key=lambda x: x["tanimoto"], reverse=True)
        max_sim = results[0]["tanimoto"] if results else 0

        return {
            "agent": "ip",
            "command": "fto",
            "query_smiles": smiles,
            "threshold": threshold,
            "max_similarity": round(max_sim, 4),
            "overall_risk": "HIGH" if max_sim >= threshold else "MODERATE" if max_sim >= 0.5 else "LOW",
            "comparisons": results[:20],
            "recommendation": _fto_recommendation(max_sim, threshold),
        }
    except ImportError as e:
        return {"error": str(e), "agent": "ip", "status": "error"}


def bioisostere_suggestions(smiles: str) -> dict:
    """Suggest bioisosteric replacements for IP differentiation."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem, BRICS

        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": f"Invalid SMILES: {smiles}", "agent": "ip"}

        # BRICS fragments as starting points for modification
        frags = BRICS.BRICSDecompose(mol)

        # Common bioisosteric replacements
        replacements = [
            {"from": "carboxylic acid (-COOH)", "to": "tetrazole", "rationale": "Maintains acidity, improves metabolic stability"},
            {"from": "ester (-COOR)", "to": "oxadiazole", "rationale": "Metabolically stable mimic"},
            {"from": "amide (-CONHR)", "to": "sulfonamide (-SO2NHR)", "rationale": "Different geometry, similar H-bonding"},
            {"from": "phenyl", "to": "pyridyl", "rationale": "Improved solubility, different IP space"},
            {"from": "Cl substituent", "to": "CF3", "rationale": "Similar size/lipophilicity, different IP"},
            {"from": "OH", "to": "NH2", "rationale": "Classical bioisostere, different SAR"},
        ]

        return {
            "agent": "ip",
            "command": "bioisosteres",
            "query_smiles": smiles,
            "fragments": list(frags)[:15],
            "suggested_replacements": replacements,
            "note": "Apply replacements to fragments for novel patentable derivatives"
        }
    except ImportError as e:
        return {"error": str(e), "agent": "ip", "status": "error"}


def _get_reference_patents() -> list:
    """Known drug SMILES for reference comparison."""
    return [
        "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4",  # sotorasib
        "C=CC(=O)N1CCC(CC1)OC2=NC3=CC(=CC=C3N2)C4=CC=CC(=C4)OC",  # osimertinib-like
        "CC(C)(C)C1=CC=C(C=C1)S(=O)(=O)NC2=CC(=CC=C2)C(=O)NC3=CC=CC=C3",  # reference
        "O=C1NC2=CC=CC=C2N1CC3=CC=C(C=C3)C(=O)O",  # reference
        "CC1=C(C=CC=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C",  # imatinib-like
    ]


def _fto_recommendation(max_sim: float, threshold: float) -> str:
    if max_sim >= threshold:
        return f"HIGH RISK: Tanimoto {max_sim:.3f} >= {threshold}. Recommend structural modifications (bioisosteric replacements) before filing."
    elif max_sim >= 0.5:
        return f"MODERATE RISK: Tanimoto {max_sim:.3f}. Consider additional differentiation. Run bioisostere analysis."
    else:
        return f"LOW RISK: Tanimoto {max_sim:.3f}. Novel chemical space. Proceed with patent filing."
