#!/usr/bin/env python3
"""PharmaClaw CLI - Input Validation Utilities."""

import json
import sys


def validate_smiles(smiles: str) -> str:
    """Validate SMILES string using RDKit. Returns canonical SMILES or raises."""
    from rdkit import Chem
    if not smiles or not smiles.strip():
        raise click.BadParameter("SMILES string cannot be empty")
    mol = Chem.MolFromSmiles(smiles.strip())
    if mol is None:
        raise ValueError(f"Invalid SMILES: '{smiles}'")
    return Chem.MolToSmiles(mol)


def validate_smiles_click(ctx, param, value):
    """Click callback for SMILES validation."""
    if value is None:
        return None
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(value.strip())
        if mol is None:
            raise ValueError()
        return value.strip()
    except Exception:
        import click
        raise click.BadParameter(f"Invalid SMILES: '{value}'")
