"""PubChem API utilities — compound lookup, property queries."""

import requests

_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def name_to_smiles(name: str) -> str:
    """Resolve a compound name to canonical SMILES via PubChem."""
    url = f"{_BASE}/compound/name/{requests.utils.quote(name)}/property/CanonicalSMILES/JSON"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    props = data.get("PropertyTable", {}).get("Properties", [])
    if not props:
        raise ValueError(f"No PubChem results for '{name}'")
    return props[0]["CanonicalSMILES"]


def get_compound_info(identifier: str, id_type: str = "name") -> dict:
    """Get compound info (CID, name, formula, MW, SMILES) from PubChem.

    Args:
        identifier: Compound name, SMILES, or CID.
        id_type: 'name', 'smiles', or 'cid'.
    """
    url = f"{_BASE}/compound/{id_type}/{requests.utils.quote(str(identifier))}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,IUPACName,InChI/JSON"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    props = data.get("PropertyTable", {}).get("Properties", [])
    if not props:
        raise ValueError(f"No PubChem results for '{identifier}'")
    p = props[0]
    return {
        "cid": p.get("CID"),
        "iupac_name": p.get("IUPACName"),
        "formula": p.get("MolecularFormula"),
        "mw": p.get("MolecularWeight"),
        "smiles": p.get("CanonicalSMILES"),
        "inchi": p.get("InChI"),
    }


def get_synonyms(identifier: str, id_type: str = "name", limit: int = 10) -> list[str]:
    """Get compound synonyms from PubChem."""
    url = f"{_BASE}/compound/{id_type}/{requests.utils.quote(str(identifier))}/synonyms/JSON"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    info_list = data.get("InformationList", {}).get("Information", [])
    if not info_list:
        return []
    return info_list[0].get("Synonym", [])[:limit]
