"""
Cheminformatics Agent — 3D conformers, pharmacophore mapping, format conversion,
RECAP fragmentation, stereoisomer enumeration.

Usage:
    >>> from pharmaclaw.core.cheminformatics import generate_conformers, recap_fragment
    >>> conf = generate_conformers("CCO", num_confs=5)
    >>> frags = recap_fragment("CC(=O)Oc1ccccc1C(=O)O")
"""

import re
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Draw
from rdkit.Chem import rdMolDescriptors
from rdkit.Chem import BRICS


def _validate_smiles(smiles: str) -> Chem.Mol:
    if not smiles or not isinstance(smiles, str):
        raise ValueError("SMILES string is required")
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    return mol


def generate_conformers(
    smiles: str,
    num_confs: int = 10,
    optimize: bool = True,
    random_seed: int = 42,
) -> dict:
    """Generate 3D conformer ensemble via ETKDG + MMFF/UFF optimization.

    Args:
        smiles: Input SMILES.
        num_confs: Number of conformers to generate.
        optimize: Whether to run force-field optimization.

    Returns dict with conformer energies and XYZ blocks.
    """
    mol = _validate_smiles(smiles)
    mol = Chem.AddHs(mol)

    params = AllChem.ETKDGv3()
    params.randomSeed = random_seed
    params.numThreads = 0
    cids = AllChem.EmbedMultipleConfs(mol, numConfs=num_confs, params=params)

    conformers = []
    for cid in cids:
        energy = None
        if optimize:
            try:
                res = AllChem.MMFFOptimizeMolecule(mol, confId=cid)
                ff = AllChem.MMFFGetMoleculeForceField(mol, AllChem.MMFFGetMoleculeProperties(mol), confId=cid)
                if ff:
                    energy = round(ff.CalcEnergy(), 2)
            except Exception:
                try:
                    AllChem.UFFOptimizeMolecule(mol, confId=cid)
                    ff = AllChem.UFFGetMoleculeForceField(mol, confId=cid)
                    if ff:
                        energy = round(ff.CalcEnergy(), 2)
                except Exception:
                    pass

        xyz = Chem.MolToXYZBlock(mol, confId=cid)
        conformers.append({
            "conf_id": cid,
            "energy_kcal": energy,
            "xyz": xyz.strip(),
        })

    # Sort by energy
    conformers.sort(key=lambda c: c["energy_kcal"] if c["energy_kcal"] is not None else float("inf"))

    return {
        "agent": "cheminformatics",
        "command": "conformers",
        "smiles": smiles,
        "num_generated": len(conformers),
        "conformers": conformers,
    }


def recap_fragment(smiles: str) -> dict:
    """RECAP retrosynthetic fragmentation for library design.

    Decomposes a molecule at synthetically relevant bonds (amide, ester,
    sulfonamide, etc.) to identify building blocks.
    """
    mol = _validate_smiles(smiles)
    tree = Chem.BRICS.BRICSDecompose(mol)
    fragments = sorted(list(tree))

    # Clean BRICS dummy atoms for readability
    clean_frags = []
    for frag in fragments:
        clean = re.sub(r'\[\d+\*\]', '[H]', frag)
        clean_mol = Chem.MolFromSmiles(clean)
        if clean_mol:
            clean_frags.append(Chem.MolToSmiles(clean_mol))

    return {
        "agent": "cheminformatics",
        "command": "recap",
        "smiles": smiles,
        "raw_fragments": fragments[:20],
        "clean_fragments": sorted(set(clean_frags))[:20],
        "num_fragments": len(fragments),
    }


def enumerate_stereoisomers(smiles: str, max_isomers: int = 32) -> dict:
    """Enumerate stereo isomers (R/S, E/Z) of a molecule.

    Args:
        smiles: Input SMILES.
        max_isomers: Maximum number of stereoisomers to generate.
    """
    from rdkit.Chem import EnumerateStereoisomers as ES

    mol = _validate_smiles(smiles)
    opts = ES.StereoEnumerationOptions(maxIsomers=max_isomers, unique=True)
    isomers = list(ES.EnumerateStereoisomers(mol, options=opts))
    isomer_smiles = sorted(set(Chem.MolToSmiles(iso, isomericSmiles=True) for iso in isomers))

    # Count stereocenters
    chiral_centers = Chem.FindMolChiralCenters(mol, includeUnassigned=True)

    return {
        "agent": "cheminformatics",
        "command": "stereoisomers",
        "smiles": smiles,
        "num_chiral_centers": len(chiral_centers),
        "chiral_centers": [{"atom_idx": c[0], "label": c[1]} for c in chiral_centers],
        "num_isomers": len(isomer_smiles),
        "isomers": isomer_smiles[:max_isomers],
    }


def convert_format(smiles: str, target_format: str = "inchi") -> dict:
    """Convert SMILES to other molecular formats.

    Args:
        target_format: 'inchi', 'inchikey', 'mol', 'sdf', 'xyz', or 'canonical'.
    """
    mol = _validate_smiles(smiles)
    canonical = Chem.MolToSmiles(mol, isomericSmiles=True)
    result = {
        "agent": "cheminformatics",
        "command": "convert",
        "input_smiles": smiles,
        "canonical_smiles": canonical,
    }

    if target_format == "inchi":
        result["inchi"] = Chem.MolToInchi(mol)
    elif target_format == "inchikey":
        inchi = Chem.MolToInchi(mol)
        result["inchi"] = inchi
        result["inchikey"] = Chem.InchiToInchiKey(inchi) if inchi else None
    elif target_format == "mol":
        result["mol_block"] = Chem.MolToMolBlock(mol)
    elif target_format == "sdf":
        mol3d = Chem.AddHs(mol)
        AllChem.EmbedMolecule(mol3d, randomSeed=42)
        AllChem.MMFFOptimizeMolecule(mol3d)
        result["sdf_block"] = Chem.MolToMolBlock(mol3d)
    elif target_format == "xyz":
        mol3d = Chem.AddHs(mol)
        AllChem.EmbedMolecule(mol3d, randomSeed=42)
        AllChem.MMFFOptimizeMolecule(mol3d)
        result["xyz_block"] = Chem.MolToXYZBlock(mol3d)
    elif target_format == "canonical":
        pass  # already have canonical_smiles
    else:
        raise ValueError(f"Unknown format: {target_format}. Use inchi/inchikey/mol/sdf/xyz/canonical.")

    return result
