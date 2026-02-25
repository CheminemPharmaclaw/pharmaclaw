#!/usr/bin/env python3
"""Toxicology Agent Wrapper - Safety profiling."""

import json
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "pharmaclaw-tox-agent", "scripts")


def analyze(smiles: str) -> dict:
    """Run toxicology analysis on a SMILES string."""
    script_path = os.path.join(SCRIPTS_DIR, "tox_agent.py")
    cmd = [sys.executable, script_path, smiles]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip() or output
        return {"error": err, "agent": "toxicology", "status": "error"}
    try:
        data = json.loads(output)
        data["agent"] = "toxicology"
        return data
    except json.JSONDecodeError:
        return {"raw_output": output, "agent": "toxicology"}
