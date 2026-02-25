#!/usr/bin/env python3
"""Market Intel Agent Wrapper - FAERS data + competitive intelligence."""

import json
import subprocess
import sys
import os
import tempfile

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "pharmaclaw-market-intel-agent", "scripts")


def query_faers(drug: str, limit: int = 20, include_preds: bool = False) -> dict:
    """Query FDA FAERS for adverse events and trends."""
    script_path = os.path.join(SCRIPTS_DIR, "query_faers.py")
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [sys.executable, script_path, "--drug", drug, "--output", tmpdir, "--limit-events", str(limit)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        output_data = {"agent": "market", "drug": drug}

        # Check for JSON output files
        for fname in os.listdir(tmpdir):
            if fname.endswith(".json"):
                fpath = os.path.join(tmpdir, fname)
                try:
                    with open(fpath) as f:
                        output_data[fname.replace(".json", "")] = json.load(f)
                except Exception:
                    pass

        # Parse stdout for any direct JSON
        stdout = result.stdout.strip()
        if stdout:
            try:
                parsed = json.loads(stdout)
                output_data.update(parsed)
            except json.JSONDecodeError:
                output_data["raw_output"] = stdout

        # Prediction markets (optional Polymarket integration)
        if include_preds:
            output_data["predictions"] = _get_predictions(drug)

        if result.returncode != 0 and "error" not in output_data:
            output_data["stderr"] = result.stderr.strip()

        return output_data


def _get_predictions(drug: str) -> dict:
    """Try Polymarket CLI for prediction market data, fallback to placeholder."""
    try:
        result = subprocess.run(
            ["polymarket-cli", "query", f"{drug} FDA approval odds"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            return {"source": "polymarket", "data": result.stdout.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return {
        "source": "unavailable",
        "note": "Polymarket CLI not installed. Install via: cargo install polymarket-cli",
        "fallback": "Use FAERS trends + literature for market signal estimation"
    }
