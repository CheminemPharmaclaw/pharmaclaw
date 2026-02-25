#!/usr/bin/env python3
"""Literature Mining Agent Wrapper - PubMed + Semantic Scholar."""

import json
import subprocess
import sys
import os

LIT_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "..", "skills", "pharmaclaw-literature-agent", "scripts")


def search(query: str, source: str = "both", max_results: int = 10, years: int = None) -> dict:
    """Search literature across PubMed and/or Semantic Scholar."""
    results = {"agent": "literature", "query": query, "sources": {}}

    if source in ("pubmed", "both"):
        results["sources"]["pubmed"] = _search_pubmed(query, max_results, years)

    if source in ("scholar", "both"):
        results["sources"]["semantic_scholar"] = _search_scholar(query, max_results)

    # Merge and deduplicate by title similarity
    all_papers = []
    for src, data in results["sources"].items():
        for paper in data.get("papers", []):
            paper["source"] = src
            all_papers.append(paper)
    results["total_papers"] = len(all_papers)
    return results


def _search_pubmed(query: str, max_results: int = 10, years: int = None) -> dict:
    script_path = os.path.join(LIT_SCRIPTS, "pubmed_search.py")
    cmd = [sys.executable, script_path, "--query", query, "--max-results", str(max_results)]
    if years:
        cmd += ["--years", str(years)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return {"error": result.stderr.strip(), "status": "error"}
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"raw_output": result.stdout.strip()}


def _search_scholar(query: str, max_results: int = 10) -> dict:
    script_path = os.path.join(LIT_SCRIPTS, "semantic_scholar.py")
    cmd = [sys.executable, script_path, "--query", query, "--max-results", str(max_results)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return {"error": result.stderr.strip(), "status": "error"}
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"raw_output": result.stdout.strip()}
