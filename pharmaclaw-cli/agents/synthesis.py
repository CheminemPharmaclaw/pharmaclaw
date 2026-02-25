#!/usr/bin/env python3
"""Synthesis Agent Wrapper - Multi-step retrosynthesis and route planning."""

import json
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "pharmaclaw-chemistry-query", "scripts")


def plan_synthesis(smiles: str, target: str = None, depth: int = 2, steps: int = 3) -> dict:
    """Plan multi-step synthesis route for a molecule."""
    script_path = os.path.join(SCRIPTS_DIR, "rdkit_mol.py")
    target_arg = target or smiles
    cmd = [sys.executable, script_path, "--action", "plan", "--target", target_arg, "--steps", str(steps), "--depth", str(depth)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip() or output
        return {"error": err, "agent": "synthesis", "status": "error"}
    try:
        data = json.loads(output)
        data["agent"] = "synthesis"
        # Enrich with feasibility scoring
        data["feasibility"] = _score_feasibility(data)
        return data
    except json.JSONDecodeError:
        return {"raw_output": output, "agent": "synthesis"}


def retrosynthesis(smiles: str, depth: int = 2) -> dict:
    """Run BRICS retrosynthesis."""
    script_path = os.path.join(SCRIPTS_DIR, "rdkit_mol.py")
    cmd = [sys.executable, script_path, "--smiles", smiles, "--action", "retro", "--depth", str(depth)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip() or output
        return {"error": err, "agent": "synthesis", "status": "error"}
    try:
        data = json.loads(output)
        data["agent"] = "synthesis"
        return data
    except json.JSONDecodeError:
        return {"raw_output": output, "agent": "synthesis"}


def _score_feasibility(plan_data: dict) -> dict:
    """Score synthesis feasibility based on route complexity."""
    route = plan_data.get("route", [])
    num_steps = len(route)
    total_precursors = sum(len(s.get("precursors", [])) for s in route)

    if num_steps <= 3 and total_precursors <= 10:
        score = "high"
        confidence = 0.75
    elif num_steps <= 5:
        score = "moderate"
        confidence = 0.55
    else:
        score = "challenging"
        confidence = 0.35

    return {
        "score": score,
        "confidence": confidence,
        "steps": num_steps,
        "total_precursors": total_precursors,
        "note": "BRICS-based disconnection; real yields require experimental validation"
    }
