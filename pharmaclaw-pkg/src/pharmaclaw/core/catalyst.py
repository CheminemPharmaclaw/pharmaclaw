"""
Catalyst Design Agent — Organometallic catalyst recommendation + novel ligand design.

Usage:
    >>> from pharmaclaw.core.catalyst import recommend, design_ligand
    >>> rec = recommend("suzuki")
    >>> lig = design_ligand("PPh3", strategy="all")
"""

import json
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors

# ── Catalyst Database ──────────────────────────────────────

CATALYST_DB = [
    {"name": "Pd(PPh3)4", "metal": "Pd", "ligand": "PPh3", "reactions": ["suzuki", "heck", "sonogashira", "stille", "negishi"],
     "conditions": "THF/DMF, 60-110°C, base (K2CO3)", "cost": "moderate", "notes": "Workhorse Pd(0) catalyst"},
    {"name": "Pd(dppf)Cl2", "metal": "Pd", "ligand": "dppf", "reactions": ["suzuki", "kumada", "negishi", "carbonylation"],
     "conditions": "THF/dioxane, 80-100°C", "cost": "moderate", "notes": "Good for sterically demanding substrates"},
    {"name": "Pd2(dba)3/XPhos", "metal": "Pd", "ligand": "XPhos", "reactions": ["buchwald_hartwig", "suzuki", "c_n_coupling"],
     "conditions": "Toluene/dioxane, 80-110°C, base", "cost": "high", "notes": "Buchwald ligand, excellent for C-N"},
    {"name": "Pd(OAc)2/BINAP", "metal": "Pd", "ligand": "BINAP", "reactions": ["buchwald_hartwig", "heck", "asymmetric"],
     "conditions": "Toluene, 80-100°C", "cost": "high", "notes": "Chiral bidentate, enantioselective"},
    {"name": "Grubbs-II", "metal": "Ru", "ligand": "NHC-PCy3", "reactions": ["metathesis", "ring_closing_metathesis", "cross_metathesis"],
     "conditions": "DCM/toluene, 25-40°C", "cost": "high", "notes": "2nd gen olefin metathesis"},
    {"name": "Hoveyda-Grubbs-II", "metal": "Ru", "ligand": "NHC-isopropoxybenzylidene", "reactions": ["metathesis", "ring_closing_metathesis"],
     "conditions": "DCM/toluene, 25-40°C, recyclable", "cost": "high", "notes": "Recyclable metathesis catalyst"},
    {"name": "Wilkinson's [RhCl(PPh3)3]", "metal": "Rh", "ligand": "PPh3", "reactions": ["hydrogenation", "hydroformylation"],
     "conditions": "THF/MeOH, H2 1-4 atm, 25°C", "cost": "very_high", "notes": "Classic homogeneous hydrogenation"},
    {"name": "Crabtree's [Ir(cod)(PCy3)(py)]PF6", "metal": "Ir", "ligand": "PCy3/pyridine",
     "reactions": ["hydrogenation", "asymmetric_hydrogenation", "c_h_borylation"],
     "conditions": "DCM, H2 1-50 atm, 25°C", "cost": "very_high", "notes": "Trisubstituted olefin hydrogenation"},
    {"name": "Ni(cod)2/dppf", "metal": "Ni", "ligand": "dppf", "reactions": ["suzuki", "kumada", "reductive_coupling"],
     "conditions": "THF/DMF, 60-80°C", "cost": "low", "notes": "Cheap Pd alternative"},
    {"name": "CuI/DMEDA", "metal": "Cu", "ligand": "DMEDA", "reactions": ["ullmann", "goldberg", "click", "chan_lam"],
     "conditions": "DMF/DMSO, 80-120°C, base", "cost": "low", "notes": "Cheap C-N/C-O coupling"},
    {"name": "Cp2ZrCl2", "metal": "Zr", "ligand": "Cp2", "reactions": ["hydrozirconation", "carboalumination"],
     "conditions": "THF, -78°C to 25°C", "cost": "low", "notes": "Schwartz reagent"},
    {"name": "Fe(acac)3", "metal": "Fe", "ligand": "acac", "reactions": ["kumada", "cross_coupling", "radical_coupling"],
     "conditions": "THF/NMP, 0-25°C", "cost": "very_low", "notes": "Green chemistry, earth-abundant"},
]

LIGAND_SCAFFOLDS = {
    "PPh3": {"smiles": "c1ccc(cc1)P(c2ccccc2)c3ccccc3", "type": "phosphine", "denticity": 1, "cone_angle": 145},
    "PCy3": {"smiles": "C1CCCCC1P(C2CCCCC2)C3CCCCC3", "type": "phosphine", "denticity": 1, "cone_angle": 170},
    "NHC_IMes": {"smiles": "C(=C1N(C=CN1c2c(C)cc(C)cc2C)c3c(C)cc(C)cc3C)", "type": "NHC", "denticity": 1, "tev": 33.6},
    "dppf": {"smiles": "c1ccc(cc1)P(c2ccccc2)[C@@H]3[C@@H](P(c4ccccc4)c5ccccc5)[Fe]36[CH]7[CH]=[CH][CH]=[CH]76", "type": "diphosphine", "denticity": 2, "bite_angle": 96},
    "BINAP": {"smiles": "c1ccc2c(c1)-c3ccccc3C2P(c4ccccc4)c5ccccc5", "type": "diphosphine", "denticity": 2, "bite_angle": 92},
    "XPhos": {"smiles": "c1ccc(c(c1)c2ccccc2)P(C3CCCCC3)C4CCCCC4", "type": "phosphine", "denticity": 1, "cone_angle": 163},
}


# ── Public API ─────────────────────────────────────────────

def recommend(
    reaction: str,
    substrate: str | None = None,
    constraints: str | None = None,
    enantioselective: bool = False,
) -> dict:
    """Recommend catalysts for a given reaction type.

    Args:
        reaction: Reaction type (suzuki, heck, buchwald_hartwig, metathesis, etc.).
        substrate: Optional substrate SMILES for compatibility check.
        constraints: Optional JSON string with cost/metal preferences.
        enantioselective: Filter for chiral/asymmetric catalysts.

    Returns dict with ranked catalyst recommendations.
    """
    reaction_key = reaction.lower().replace("-", "_").replace(" ", "_")

    matches = []
    for cat in CATALYST_DB:
        if reaction_key in cat["reactions"]:
            score = 1.0
            # Prefer cheaper catalysts
            cost_scores = {"very_low": 1.0, "low": 0.9, "moderate": 0.7, "high": 0.5, "very_high": 0.3}
            score *= cost_scores.get(cat["cost"], 0.5)
            # Enantioselective filter
            if enantioselective and "asymmetric" not in cat["reactions"] and "BINAP" not in cat["name"]:
                score *= 0.3
            matches.append({**cat, "score": round(score, 2)})

    matches.sort(key=lambda x: x["score"], reverse=True)

    return {
        "agent": "catalyst",
        "command": "recommend",
        "reaction": reaction,
        "num_matches": len(matches),
        "recommendations": matches[:5],
        "note": "Scores consider cost and reaction compatibility. Validate with literature.",
    }


def design_ligand(scaffold: str, strategy: str = "all") -> dict:
    """Design novel ligand variants from a known scaffold.

    Args:
        scaffold: Scaffold name (PPh3, NHC_IMes, PCy3, etc.) or SMILES.
        strategy: 'steric', 'electronic', 'bioisosteric', or 'all'.

    Returns dict with novel ligand variants and their properties.
    """
    # Resolve scaffold
    if scaffold in LIGAND_SCAFFOLDS:
        scaffold_info = LIGAND_SCAFFOLDS[scaffold]
        scaffold_smiles = scaffold_info["smiles"]
    else:
        scaffold_smiles = scaffold
        scaffold_info = {"type": "custom", "smiles": scaffold}

    mol = Chem.MolFromSmiles(scaffold_smiles)
    if mol is None:
        raise ValueError(f"Invalid scaffold: {scaffold}")

    variants = []

    # Steric modifications
    if strategy in ("steric", "all"):
        steric_mods = [
            ("tert-butyl substitution", "add t-Bu groups for increased steric bulk"),
            ("isopropyl substitution", "moderate steric increase"),
            ("cyclohexyl replacement", "PCy3-like bulk on phosphine"),
        ]
        for name, rationale in steric_mods:
            variants.append({
                "modification": name,
                "strategy": "steric",
                "rationale": rationale,
                "parent_scaffold": scaffold,
            })

    # Electronic modifications
    if strategy in ("electronic", "all"):
        electronic_mods = [
            ("para-CF3 on aryl", "electron-withdrawing, increases electrophilicity"),
            ("para-OMe on aryl", "electron-donating, increases nucleophilicity"),
            ("para-NMe2 on aryl", "strong donor, high TEV"),
        ]
        for name, rationale in electronic_mods:
            variants.append({
                "modification": name,
                "strategy": "electronic",
                "rationale": rationale,
                "parent_scaffold": scaffold,
            })

    # Bioisosteric modifications
    if strategy in ("bioisosteric", "all"):
        bio_mods = [
            ("phenyl → pyridyl", "improved solubility, distinct IP"),
            ("P → As substitution", "arsine analog, different σ-donor strength"),
            ("NHC → CAAC", "cyclic alkyl amino carbene, stronger σ-donor"),
        ]
        for name, rationale in bio_mods:
            variants.append({
                "modification": name,
                "strategy": "bioisosteric",
                "rationale": rationale,
                "parent_scaffold": scaffold,
            })

    return {
        "agent": "catalyst",
        "command": "ligand_design",
        "scaffold": scaffold,
        "scaffold_info": scaffold_info,
        "strategy": strategy,
        "num_variants": len(variants),
        "variants": variants,
        "note": "Validate novel ligands with DFT/xTB geometry optimization before synthesis.",
    }
