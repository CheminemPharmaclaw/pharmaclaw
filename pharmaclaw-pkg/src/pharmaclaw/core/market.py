"""
Market Intel Agent — FDA FAERS adverse events, trends, competitive intelligence.

Usage:
    >>> from pharmaclaw.core.market import query_faers
    >>> result = query_faers("sotorasib")
    >>> result["events"]
"""

import requests


_OPENFDA_BASE = "https://api.fda.gov/drug/event.json"


def query_faers(drug: str, limit: int = 20) -> dict:
    """Query FDA FAERS for adverse events.

    Args:
        drug: Drug name (generic or brand).
        limit: Maximum number of events to return.

    Returns dict with events, top reactions, and yearly counts.
    """
    results = {"agent": "market", "drug": drug}

    # Events search
    try:
        resp = requests.get(_OPENFDA_BASE, params={
            "search": f'patient.drug.medicinalproduct:"{drug}"',
            "limit": min(limit, 100),
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        events = []
        for r in data.get("results", []):
            reactions = [rx.get("reactionmeddrapt", "") for rx in r.get("patient", {}).get("reaction", [])]
            outcomes = r.get("patient", {}).get("reaction", [{}])
            events.append({
                "reactions": reactions[:10],
                "serious": r.get("serious"),
                "receivedate": r.get("receivedate"),
                "country": r.get("occurcountry"),
            })
        results["events"] = events
        results["total_events"] = data.get("meta", {}).get("results", {}).get("total", 0)
    except Exception as e:
        results["events"] = []
        results["events_error"] = str(e)

    # Top reactions (count endpoint)
    try:
        resp = requests.get(_OPENFDA_BASE, params={
            "search": f'patient.drug.medicinalproduct:"{drug}"',
            "count": "patient.reaction.reactionmeddrapt.exact",
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results["top_reactions"] = [
            {"reaction": r["term"], "count": r["count"]}
            for r in data.get("results", [])[:20]
        ]
    except Exception as e:
        results["top_reactions"] = []
        results["reactions_error"] = str(e)

    # Yearly trends
    try:
        resp = requests.get(_OPENFDA_BASE, params={
            "search": f'patient.drug.medicinalproduct:"{drug}"',
            "count": "receivedate",
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Aggregate by year
        yearly = {}
        for r in data.get("results", []):
            year = str(r.get("time", ""))[:4]
            if year:
                yearly[year] = yearly.get(year, 0) + r.get("count", 0)
        results["yearly_trends"] = [{"year": y, "count": c} for y, c in sorted(yearly.items())]
    except Exception as e:
        results["yearly_trends"] = []
        results["trends_error"] = str(e)

    return results
