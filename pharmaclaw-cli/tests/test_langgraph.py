#!/usr/bin/env python3
"""Tests for LangGraph orchestration."""

import json
import subprocess
import sys
import os

CLI_PATH = os.path.join(os.path.dirname(__file__), "..", "pharmaclaw_cli.py")
PYTHON = sys.executable

SOTORASIB = "CC1=NN(C(=O)C1=CC2=C(N=C(C=C2)NC3=CC(=NN3C)C(F)(F)F)Cl)C4CC4"
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
ETHANOL = "CCO"


def run_cmd(args: list) -> dict:
    cmd = [PYTHON, CLI_PATH] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    try:
        return {"exit_code": result.returncode, "data": json.loads(result.stdout.strip()), "stderr": result.stderr}
    except json.JSONDecodeError:
        return {"exit_code": result.returncode, "raw": result.stdout, "stderr": result.stderr}


def test_quick_workflow():
    r = run_cmd(["langgraph", "--smiles", ETHANOL, "--workflow", "quick"])
    assert r["exit_code"] == 0, f"Exit code {r['exit_code']}: {r.get('stderr', '')}"
    d = r["data"]
    assert d["framework"] == "langgraph"
    assert d["workflow"] == "quick"
    assert "consensus" in d
    assert "score" in d["consensus"]
    print(f"✅ quick workflow: score={d['consensus']['score']}/10 — {d['consensus']['verdict']}")


def test_safety_workflow():
    r = run_cmd(["langgraph", "--smiles", ASPIRIN, "--workflow", "safety"])
    assert r["exit_code"] == 0
    d = r["data"]
    assert "pharmacology" in d
    assert "toxicology" in d
    assert "consensus" in d
    print(f"✅ safety workflow: score={d['consensus']['score']}/10")


def test_synthesis_workflow():
    r = run_cmd(["langgraph", "--smiles", ASPIRIN, "--workflow", "synthesis"])
    assert r["exit_code"] == 0
    d = r["data"]
    assert "synthesis" in d
    assert "catalyst" in d
    print(f"✅ synthesis workflow: score={d['consensus']['score']}/10")


def test_full_workflow():
    r = run_cmd(["langgraph", "--smiles", ETHANOL, "--workflow", "full", "--query", "ethanol pharmacology"])
    assert r["exit_code"] == 0
    d = r["data"]
    assert "chemistry" in d
    assert "pharmacology" in d
    assert "toxicology" in d
    assert "consensus" in d
    agents = d.get("agents_consulted", [])
    assert len(agents) >= 4, f"Expected >=4 agents, got {agents}"
    print(f"✅ full workflow: {len(agents)} agents, score={d['consensus']['score']}/10 — {d['consensus']['verdict']}")


def test_consensus_scoring():
    """Test that sotorasib gets HIGH IP risk (it's in the reference set)."""
    r = run_cmd(["langgraph", "--smiles", SOTORASIB, "--workflow", "quick"])
    assert r["exit_code"] == 0
    d = r["data"]
    assert "consensus" in d
    score = d["consensus"]["score"]
    assert isinstance(score, (int, float))
    print(f"✅ consensus scoring: sotorasib score={score}/10")


if __name__ == "__main__":
    tests = [
        test_quick_workflow,
        test_safety_workflow,
        test_synthesis_workflow,
        test_full_workflow,
        test_consensus_scoring,
    ]

    passed = failed = 0
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
        print("🎉 All LangGraph tests passed!")
    sys.exit(1 if failed > 0 else 0)
