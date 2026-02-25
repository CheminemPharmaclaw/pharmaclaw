#!/usr/bin/env python3
"""Pharmacology Agent Wrapper - ADME/PK profiling."""

import json
import subprocess
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "pharmaclaw-pharmacology-agent", "scripts")


def profile(smiles: str) -> dict:
    """Run full ADME/PK profile on a SMILES string."""
    script_path = os.path.join(SCRIPTS_DIR, "chain_entry.py")
    input_json = json.dumps({"smiles": smiles})
    cmd = [sys.executable, script_path, "--input-json", input_json]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    output = result.stdout.strip()
    if result.returncode != 0:
        err = result.stderr.strip() or output
        return {"error": err, "agent": "pharmacology", "status": "error"}
    try:
        data = json.loads(output)
        data["agent"] = "pharmacology"
        return data
    except json.JSONDecodeError:
        return {"raw_output": output, "agent": "pharmacology"}
