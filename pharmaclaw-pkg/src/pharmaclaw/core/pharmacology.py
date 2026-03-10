"""
Pharmacology Agent — ADME/PK profiling via RDKit descriptors and rule-based predictions.

Usage:
    >>> from pharmaclaw.core.pharmacology import profile
    >>> result = profile("CC(=O)Oc1ccccc1C(=O)O")  # aspirin
    >>> result["report"]["lipinski"]["pass"]
    True
"""

import os
import sys
from datetime import datetime, timezone

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors, FilterCatalog
from rdkit.Chem import QED as QEDModule

# SA Score (optional — may not be in all RDKit installs)
try:
    from rdkit.Chem import RDConfig
    sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
    import sascorer
    _HAS_SASCORER = True
except Exception:
    _HAS_SASCORER = False

# PAINS filter catalog
try:
    _pains_params = FilterCatalog.FilterCatalogParams()
    _pains_params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
    _PAINS_CATALOG = FilterCatalog.FilterCatalog(_pains_params)
    _HAS_PAINS = True
except Exception:
    _HAS_PAINS = False


def _validate_smiles(smiles: str) -> Chem.Mol:
    if not smiles or not isinstance(smiles, str):
        raise ValueError("SMILES string is required")
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    return mol


def compute_descriptors(mol: Chem.Mol) -> dict:
    """Compute core molecular descriptors."""
    return {
        "mw": round(Descriptors.ExactMolWt(mol), 2),
        "logp": round(Descriptors.MolLogP(mol), 4),
        "tpsa": round(Descriptors.TPSA(mol), 2),
        "hbd": Descriptors.NumHDonors(mol),
        "hba": Descriptors.NumHAcceptors(mol),
        "rotb": Descriptors.NumRotatableBonds(mol),
        "arom_rings": Descriptors.NumAromaticRings(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "mr": round(Descriptors.MolMR(mol), 2),
    }


def lipinski(desc: dict) -> dict:
    """Lipinski Rule of Five."""
    violations = 0
    details = {}
    for label, passed, val in [
        ("MW < 500", desc["mw"] < 500, desc["mw"]),
        ("logP < 5", desc["logp"] < 5, desc["logp"]),
        ("HBD < 5", desc["hbd"] < 5, desc["hbd"]),
        ("HBA < 10", desc["hba"] < 10, desc["hba"]),
    ]:
        details[label] = {"value": val, "pass": passed}
        if not passed:
            violations += 1
    return {"pass": violations <= 1, "violations": violations, "details": details}


def veber(desc: dict) -> dict:
    """Veber rules for oral bioavailability."""
    tpsa_ok = desc["tpsa"] <= 140
    rotb_ok = desc["rotb"] <= 10
    return {
        "pass": tpsa_ok and rotb_ok,
        "tpsa": {"value": desc["tpsa"], "threshold": 140, "pass": tpsa_ok},
        "rotatable_bonds": {"value": desc["rotb"], "threshold": 10, "pass": rotb_ok},
    }


def compute_qed(mol: Chem.Mol) -> float | None:
    """Quantitative Estimate of Drug-likeness."""
    try:
        return round(QEDModule.qed(mol), 4)
    except Exception:
        return None


def compute_sa_score(mol: Chem.Mol) -> float | None:
    """Synthetic Accessibility Score (1=easy, 10=hard)."""
    if not _HAS_SASCORER:
        return None
    try:
        return round(sascorer.calculateScore(mol), 2)
    except Exception:
        return None


def predict_adme(desc: dict) -> dict:
    """Rule-based ADME predictions (BBB, solubility, GI, CYP3A4, P-gp, PPB)."""
    adme = {}

    # BBB permeability
    if desc["tpsa"] < 60 and 1 <= desc["logp"] <= 3:
        adme["bbb"] = {"prediction": "high", "confidence": "medium",
                       "rationale": f"TPSA={desc['tpsa']}<60, logP={desc['logp']} in 1-3"}
    elif desc["tpsa"] < 90:
        adme["bbb"] = {"prediction": "moderate", "confidence": "medium",
                       "rationale": f"TPSA={desc['tpsa']}<90"}
    else:
        adme["bbb"] = {"prediction": "low", "confidence": "medium",
                       "rationale": f"TPSA={desc['tpsa']}>=90"}

    # Aqueous solubility (ESOL-like)
    log_s = round(0.16 - 0.63 * desc["logp"] - 0.0062 * desc["mw"]
                  + 0.066 * desc["rotb"] - 0.74 * desc["arom_rings"], 2)
    sol_class = "high" if log_s > -2 else "moderate" if log_s > -4 else "low"
    adme["solubility"] = {"logS_estimate": log_s, "class": sol_class,
                          "rationale": "ESOL-approximation from descriptors"}

    # GI absorption (Egan egg)
    gi_pass = desc["logp"] < 5.6 and desc["tpsa"] < 131.6
    adme["gi_absorption"] = {"prediction": "high" if gi_pass else "low",
                             "rationale": "Egan egg model (logP/TPSA)"}

    # CYP3A4 inhibition risk
    cyp_risk = desc["logp"] > 3 and desc["mw"] > 300
    adme["cyp3a4_inhibition"] = {
        "risk": "high" if cyp_risk else "low",
        "rationale": f"logP={desc['logp']}>3 and MW={desc['mw']}>300" if cyp_risk else "Below thresholds",
    }

    # P-glycoprotein substrate
    pgp_sub = desc["mw"] > 400 and desc["hbd"] > 2
    adme["pgp_substrate"] = {
        "prediction": "likely" if pgp_sub else "unlikely",
        "rationale": f"MW={desc['mw']}>400 and HBD={desc['hbd']}>2" if pgp_sub else "Below thresholds",
    }

    # Plasma protein binding
    ppb_high = desc["logp"] > 3
    adme["plasma_protein_binding"] = {
        "prediction": "high (>90%)" if ppb_high else "moderate-low",
        "rationale": f"logP={desc['logp']}>3" if ppb_high else f"logP={desc['logp']}<=3",
    }

    return adme


def check_pains(mol: Chem.Mol) -> dict:
    """Check for PAINS (Pan-Assay Interference Compounds) alerts."""
    if not _HAS_PAINS:
        return {"checked": False, "reason": "PAINS catalog not available"}
    entry = _PAINS_CATALOG.GetFirstMatch(mol)
    if entry:
        return {"alert": True, "pattern": entry.GetDescription()}
    return {"alert": False}


def _assess_risks(desc, lip, adme, pains) -> list[str]:
    """Compile risk factors."""
    risks = []
    if not lip["pass"]:
        risks.append(f"Lipinski violations: {lip['violations']}")
    if desc["mw"] > 600:
        risks.append(f"High MW ({desc['mw']}) — oral absorption concerns")
    if desc["logp"] > 5:
        risks.append(f"High logP ({desc['logp']}) — solubility/metabolism concerns")
    if desc["tpsa"] > 140:
        risks.append(f"High TPSA ({desc['tpsa']}) — permeability concerns")
    if adme.get("solubility", {}).get("class") == "low":
        risks.append("Low predicted aqueous solubility")
    if adme.get("cyp3a4_inhibition", {}).get("risk") == "high":
        risks.append("CYP3A4 inhibition risk — potential DDI")
    if adme.get("pgp_substrate", {}).get("prediction") == "likely":
        risks.append("Likely P-gp substrate — may affect oral absorption")
    if isinstance(pains, dict) and pains.get("alert"):
        risks.append(f"PAINS alert: {pains.get('pattern', 'unknown')}")
    return risks


# ── Public API ─────────────────────────────────────────────

def profile(smiles: str) -> dict:
    """Run full ADME/PK profile on a SMILES string.

    Returns a complete pharmacology report with descriptors, Lipinski/Veber rules,
    QED, SA Score, ADME predictions, PAINS alerts, and risk assessment.
    """
    mol = _validate_smiles(smiles)
    canonical = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)

    desc = compute_descriptors(mol)
    lip = lipinski(desc)
    veb = veber(desc)
    qed_val = compute_qed(mol)
    sa = compute_sa_score(mol)
    adme = predict_adme(desc)
    pains = check_pains(mol)
    risks = _assess_risks(desc, lip, adme, pains)

    return {
        "agent": "pharmacology",
        "version": "1.1.0",
        "smiles": canonical,
        "status": "success",
        "report": {
            "descriptors": desc,
            "lipinski": lip,
            "veber": veb,
            "qed": qed_val,
            "sa_score": sa,
            "adme": adme,
            "pains": pains,
        },
        "risks": risks,
        "recommend_next": ["toxicology", "ip-expansion"],
        "confidence": 0.85,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
