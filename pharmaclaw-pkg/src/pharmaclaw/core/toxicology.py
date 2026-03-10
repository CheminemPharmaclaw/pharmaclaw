"""
Toxicology Agent — Safety profiling, structural alerts, PAINS, risk scoring.

Usage:
    >>> from pharmaclaw.core.toxicology import analyze
    >>> result = analyze("c1ccccc1")  # benzene
    >>> result["risk"]
    'Low'
"""

from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen
from rdkit.Chem.rdMolDescriptors import CalcNumRings, CalcNumAromaticRings


def _validate_smiles(smiles: str) -> Chem.Mol:
    if not smiles or not isinstance(smiles, str):
        raise ValueError("SMILES string is required")
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    Chem.SanitizeMol(mol)
    return mol


def analyze(smiles: str) -> dict:
    """Run toxicology analysis on a SMILES string.

    Returns dict with Lipinski violations, Veber violations, QED,
    PAINS count, risk level, and molecular properties.
    """
    mol = _validate_smiles(smiles)

    # Descriptors
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    rotb = Descriptors.NumRotatableBonds(mol)
    tpsa = Descriptors.TPSA(mol)
    rings = CalcNumRings(mol)
    arom = CalcNumAromaticRings(mol)

    # Lipinski violations
    lipinski_viol = sum([mw > 500, logp > 5, hbd > 5, hba > 10])

    # Veber violations
    veber_viol = sum([tpsa > 140, rotb > 10])

    # QED
    try:
        from rdkit.Chem import QED as QEDModule
        qed = QEDModule.qed(mol)
    except Exception:
        qed = 0.0

    # PAINS (simple substructure check)
    pains_patterns = ["c1ncnc2c1ncn2", "cc1ccc2nsnc2c1"]
    pains_count = 0
    for pat in pains_patterns:
        pat_mol = Chem.MolFromSmarts(pat)
        if pat_mol and mol.HasSubstructMatch(pat_mol):
            pains_count += 1

    # Risk assessment
    if lipinski_viol == 0 and pains_count == 0:
        risk = "Low"
    elif lipinski_viol <= 1 and pains_count == 0:
        risk = "Medium"
    else:
        risk = "High"

    return {
        "agent": "toxicology",
        "smiles": smiles,
        "lipinski_violations": lipinski_viol,
        "veber_violations": veber_viol,
        "qed": round(qed, 3),
        "pains_alerts": pains_count,
        "risk": risk,
        "props": {
            "mw": round(mw, 1),
            "logp": round(logp, 2),
            "tpsa": round(tpsa, 1),
            "hbd": hbd,
            "hba": hba,
            "rotb": rotb,
            "rings": rings,
            "arom_rings": arom,
        },
    }
