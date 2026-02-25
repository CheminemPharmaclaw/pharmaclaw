#!/usr/bin/env python3
"""Catalyst Design Agent Wrapper - Catalyst recommendation + ligand design."""

import json
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "pharmaclaw-catalyst-design", "scripts")


def recommend(reaction: str, substrate: str = None, constraints: str = None, enantioselective: bool = False) -> dict:
    """Recommend catalysts for a given reaction type."""
    script_path = os.path.join(SCRIPTS_DIR, "catalyst_recommend.py")
    cmd = [sys.executable, script_path, "--reaction", reaction]
    if substrate:
        cmd += ["--substrate", substrate]
    if constraints:
        cmd += ["--constraints", constraints]
    if enantioselective:
        cmd.append("--enantioselective")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip() or output
        return {"error": err, "agent": "catalyst", "status": "error"}
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            data["agent"] = "catalyst"
        return data
    except json.JSONDecodeError:
        return {"raw_output": output, "agent": "catalyst"}


def design_ligand(scaffold: str, strategy: str = "all", draw: bool = False) -> dict:
    """Design novel ligand variants from a scaffold."""
    script_path = os.path.join(SCRIPTS_DIR, "ligand_designer.py")
    cmd = [sys.executable, script_path, "--scaffold", scaffold, "--strategy", strategy]
    if draw:
        cmd.append("--draw")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip() or output
        return {"error": err, "agent": "catalyst", "status": "error"}
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            data["agent"] = "catalyst"
        return data
    except json.JSONDecodeError:
        return {"raw_output": output, "agent": "catalyst"}
