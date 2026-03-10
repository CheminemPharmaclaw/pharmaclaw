"""
IP Check Agent — Freedom-to-Operate analysis, similarity search, bioisostere suggestions.

Usage:
    >>> from pharmaclaw.core.ip_check import fto_analysis, bioisostere_suggestions
    >>> fto = fto_analysis("CCO")
    >>> fto["overall_risk"]
    'LOW'
"""

from rdkit import Chem
from rdkit.Chem import AllChem, DataStructs, BRICS

# Known drug SMILES for reference comparison
_REFERENCE_PATENTS = [
    "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4",  # sotorasib
    "C=CC(=O)N1CCC(CC1)OC2=NC3=CC(=CC=C3N2)C4=CC=CC(=C4)OC",  # osimertinib-like
    "CC(C)(C)C1=CC=C(C=C1)S(=O)(=O)NC2=CC(=CC=C2)C(=O)NC3=CC=CC=C3",
    "O=C1NC2=CC=CC=C2N1CC3=CC=C(C=C3)C(=O)O",
    "CC1=C(C=CC=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C",  # imatinib-like
]


def _validate_smiles(smiles: str) -> Chem.Mol:
    if not smiles or not isinstance(smiles, str):
        raise ValueError("SMILES string is required")
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    return mol


def fto_analysis(
    smiles: str,
    compare_smiles: list[str] | None = None,
    threshold: float = 0.85,
) -> dict:
    """Run Freedom-to-Operate analysis using Morgan fingerprint similarity.

    Args:
        smiles: Query molecule SMILES.
        compare_smiles: Reference SMILES to compare against (defaults to known drugs).
        threshold: Tanimoto threshold for HIGH risk classification.

    Returns dict with overall risk, comparisons, and recommendation.
    """
    mol = _validate_smiles(smiles)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)

    refs = compare_smiles or _REFERENCE_PATENTS
    results = []
    for ref_smi in refs:
        ref_mol = Chem.MolFromSmiles(ref_smi)
        if ref_mol is None:
            continue
        ref_fp = AllChem.GetMorganFingerprintAsBitVect(ref_mol, 2, nBits=2048)
        sim = DataStructs.TanimotoSimilarity(fp, ref_fp)
        risk = "HIGH" if sim >= threshold else "MODERATE" if sim >= 0.5 else "LOW"
        results.append({
            "reference_smiles": ref_smi,
            "tanimoto": round(sim, 4),
            "risk": risk,
        })

    results.sort(key=lambda x: x["tanimoto"], reverse=True)
    max_sim = results[0]["tanimoto"] if results else 0

    if max_sim >= threshold:
        recommendation = f"HIGH RISK: Tanimoto {max_sim:.3f} >= {threshold}. Recommend structural modifications before filing."
    elif max_sim >= 0.5:
        recommendation = f"MODERATE RISK: Tanimoto {max_sim:.3f}. Consider additional differentiation."
    else:
        recommendation = f"LOW RISK: Tanimoto {max_sim:.3f}. Novel chemical space. Proceed with patent filing."

    return {
        "agent": "ip",
        "command": "fto",
        "query_smiles": smiles,
        "threshold": threshold,
        "max_similarity": round(max_sim, 4),
        "overall_risk": "HIGH" if max_sim >= threshold else "MODERATE" if max_sim >= 0.5 else "LOW",
        "comparisons": results[:20],
        "recommendation": recommendation,
    }


def bioisostere_suggestions(smiles: str) -> dict:
    """Suggest bioisosteric replacements for IP differentiation.

    Returns common bioisosteric replacement strategies and BRICS fragments.
    """
    mol = _validate_smiles(smiles)
    frags = BRICS.BRICSDecompose(mol)

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
        "fragments": sorted(list(frags))[:15],
        "suggested_replacements": replacements,
        "note": "Apply replacements to fragments for novel patentable derivatives",
    }
