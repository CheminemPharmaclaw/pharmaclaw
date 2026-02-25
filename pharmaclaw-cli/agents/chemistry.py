#!/usr/bin/env python3
"""Chemistry Agent Wrapper - PubChem + RDKit props, retrosynthesis, reactions."""

import json
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "pharmaclaw-chemistry-query", "scripts")


def run_script(script_name: str, args: list) -> dict:
    """Run a chemistry script and return parsed JSON output."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    cmd = [sys.executable, script_path] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip() or output
        return {"error": err, "agent": "chemistry", "status": "error"}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"raw_output": output, "agent": "chemistry"}


def get_props(smiles: str) -> dict:
    data = run_script("rdkit_mol.py", ["--smiles", smiles, "--action", "props"])
    return {"agent": "chemistry", "command": "props", "smiles": smiles, **data}


def get_retro(smiles: str, depth: int = 1) -> dict:
    data = run_script("rdkit_mol.py", ["--smiles", smiles, "--action", "retro", "--depth", str(depth)])
    return {"agent": "chemistry", "command": "retro", "smiles": smiles, **data}


def get_plan(smiles: str, steps: int = 3) -> dict:
    data = run_script("rdkit_mol.py", ["--smiles", smiles, "--action", "plan", "--steps", str(steps)])
    return {"agent": "chemistry", "command": "plan", **data}


def get_fingerprint(smiles: str, radius: int = 2) -> dict:
    data = run_script("rdkit_mol.py", ["--smiles", smiles, "--action", "fingerprint", "--radius", str(radius)])
    return {"agent": "chemistry", "command": "fingerprint", "smiles": smiles, **data}


def get_similarity(query_smiles: str, target_smiles: str) -> dict:
    data = run_script("rdkit_mol.py", ["--query_smiles", query_smiles, "--target_smiles", target_smiles, "--action", "similarity"])
    return {"agent": "chemistry", "command": "similarity", **data}


def get_draw(smiles: str, output: str = None, fmt: str = "svg") -> dict:
    args = ["--smiles", smiles, "--action", "draw", "--format", fmt]
    if output:
        args += ["--output", output]
    data = run_script("rdkit_mol.py", args)
    return {"agent": "chemistry", "command": "draw", **data}


def query_pubchem(compound: str, query_type: str = "info", fmt: str = "json") -> dict:
    args = ["--compound", compound, "--type", query_type, "--format", fmt]
    data = run_script("query_pubchem.py", args)
    return {"agent": "chemistry", "command": "pubchem", "compound": compound, **data}


def run_reaction(template: str, reactants: list = None, product: str = None, reaction_type: str = "forward") -> dict:
    args = ["--template", template, "--type", reaction_type]
    if reactants:
        args += ["--reactants"] + reactants
    if product:
        args += ["--product", product]
    data = run_script("rdkit_reaction.py", args)
    return {"agent": "chemistry", "command": "reaction", **data}
