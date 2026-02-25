#!/usr/bin/env python3
"""PharmaClaw CLI Tests."""

import json
import subprocess
import sys
import os

CLI_PATH = os.path.join(os.path.dirname(__file__), "..", "pharmaclaw_cli.py")
PYTHON = sys.executable

# Sotorasib SMILES (KRAS G12C inhibitor)
SOTORASIB = "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4"
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
ETHANOL = "CCO"


def run_cmd(args: list, stdin_data: str = None) -> dict:
    """Run a CLI command and return parsed JSON."""
    cmd = [PYTHON, CLI_PATH] + args
    result = subprocess.run(cmd, capture_output=True, text=True, input=stdin_data, timeout=120)
    try:
        return {"exit_code": result.returncode, "data": json.loads(result.stdout.strip()), "stderr": result.stderr}
    except json.JSONDecodeError:
        return {"exit_code": result.returncode, "raw": result.stdout, "stderr": result.stderr}


def test_version():
    r = run_cmd(["--version"])
    assert r["exit_code"] == 0
    assert r["data"]["version"] == "1.0.0"
    print("✅ version")


def test_chemistry_props():
    r = run_cmd(["chemistry", "--smiles", SOTORASIB, "--mode", "props"])
    assert r["exit_code"] == 0
    d = r["data"]
    assert "mw" in d, f"Missing mw in {d}"
    mw = d["mw"]
    assert 400 < mw < 600, f"MW {mw} out of range for sotorasib"
    print(f"✅ chemistry props: MW={mw:.1f}")


def test_chemistry_retro():
    r = run_cmd(["chemistry", "--smiles", ASPIRIN, "--mode", "retro", "--depth", "1"])
    assert r["exit_code"] == 0
    d = r["data"]
    assert "precursors" in d or "num_precursors" in d, f"No retro data: {d}"
    print(f"✅ chemistry retro: {d.get('num_precursors', '?')} precursors")


def test_toxicology():
    r = run_cmd(["toxicology", "--smiles", SOTORASIB])
    assert r["exit_code"] == 0
    d = r["data"]
    assert "risk" in d, f"Missing risk in {d}"
    print(f"✅ toxicology: risk={d['risk']}")


def test_pharmacology():
    r = run_cmd(["pharmacology", "--smiles", ASPIRIN])
    assert r["exit_code"] == 0
    d = r["data"]
    # Should have lipinski or descriptors
    has_data = "lipinski" in d or "descriptors" in d or "mw" in d
    assert has_data or "error" not in d, f"Pharmacology failed: {d}"
    print(f"✅ pharmacology: keys={list(d.keys())[:5]}")


def test_ip_fto():
    r = run_cmd(["ip", "--smiles", ETHANOL])
    assert r["exit_code"] == 0
    d = r["data"]
    assert "overall_risk" in d, f"Missing overall_risk: {d}"
    print(f"✅ ip: risk={d['overall_risk']}, max_sim={d.get('max_similarity')}")


def test_compare():
    r = run_cmd(["compare", "--smiles", f"{ETHANOL},{ASPIRIN}"])
    assert r["exit_code"] == 0
    d = r["data"]
    assert d["count"] == 2
    print(f"✅ compare: {d['count']} compounds")


def test_invalid_smiles():
    r = run_cmd(["chemistry", "--smiles", "INVALID_NOT_SMILES", "--mode", "props"])
    # Should error gracefully
    assert r["exit_code"] != 0 or "error" in str(r.get("data", "")) or "error" in str(r.get("stderr", ""))
    print("✅ invalid SMILES handled")


def test_piping():
    """Test JSON piping: chemistry → toxicology."""
    # First get chemistry output
    r1 = run_cmd(["chemistry", "--smiles", ETHANOL, "--mode", "props"])
    assert r1["exit_code"] == 0
    # Pipe it to toxicology (stdin)
    chem_json = json.dumps({**r1["data"], "smiles": ETHANOL})
    r2 = run_cmd(["toxicology"], stdin_data=chem_json)
    assert r2["exit_code"] == 0
    print(f"✅ piping: chemistry → toxicology")


if __name__ == "__main__":
    tests = [
        test_version,
        test_chemistry_props,
        test_chemistry_retro,
        test_toxicology,
        test_pharmacology,
        test_ip_fto,
        test_compare,
        test_invalid_smiles,
        test_piping,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed == 0:
        print("🎉 All tests passed!")
    sys.exit(1 if failed > 0 else 0)
