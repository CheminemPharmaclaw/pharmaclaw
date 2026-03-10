"""
Literature Agent — PubMed + Semantic Scholar search with TLDRs.

Usage:
    >>> from pharmaclaw.core.literature import search
    >>> results = search("KRAS G12C inhibitors 2024")
    >>> results["total_papers"]
    20
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote


# ── PubMed ─────────────────────────────────────────────────

_PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _search_pubmed(query: str, max_results: int = 10, years: int | None = None) -> dict:
    """Search PubMed and return paper metadata."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": min(max_results, 50),
        "retmode": "json",
        "sort": "relevance",
    }
    if years:
        params["datetype"] = "pdat"
        params["reldate"] = years * 365

    try:
        resp = requests.get(_PUBMED_SEARCH, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])

        if not id_list:
            return {"papers": [], "count": 0}

        # Fetch details
        fetch_resp = requests.get(_PUBMED_FETCH, params={
            "db": "pubmed", "id": ",".join(id_list), "retmode": "xml"
        }, timeout=15)
        fetch_resp.raise_for_status()

        papers = []
        root = ET.fromstring(fetch_resp.text)
        for article in root.findall(".//PubmedArticle"):
            title_el = article.find(".//ArticleTitle")
            abstract_el = article.find(".//AbstractText")
            pmid_el = article.find(".//PMID")
            year_el = article.find(".//PubDate/Year")
            journal_el = article.find(".//Journal/Title")

            papers.append({
                "pmid": pmid_el.text if pmid_el is not None else None,
                "title": title_el.text if title_el is not None else "Unknown",
                "abstract": (abstract_el.text or "")[:500] if abstract_el is not None else "",
                "year": year_el.text if year_el is not None else None,
                "journal": journal_el.text if journal_el is not None else None,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid_el.text}/" if pmid_el is not None else None,
            })

        return {"papers": papers, "count": len(papers)}
    except Exception as e:
        return {"papers": [], "count": 0, "error": str(e)}


# ── Semantic Scholar ───────────────────────────────────────

_S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"


def _search_scholar(query: str, max_results: int = 10) -> dict:
    """Search Semantic Scholar and return paper metadata with TLDRs."""
    try:
        resp = requests.get(_S2_API, params={
            "query": query,
            "limit": min(max_results, 50),
            "fields": "title,abstract,year,authors,tldr,url,citationCount,externalIds",
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        papers = []
        for p in data.get("data", []):
            authors = [a.get("name", "") for a in (p.get("authors") or [])[:5]]
            tldr = p.get("tldr", {})
            papers.append({
                "paper_id": p.get("paperId"),
                "title": p.get("title", "Unknown"),
                "abstract": (p.get("abstract") or "")[:500],
                "tldr": tldr.get("text") if tldr else None,
                "year": p.get("year"),
                "authors": authors,
                "citation_count": p.get("citationCount"),
                "url": p.get("url"),
                "doi": (p.get("externalIds") or {}).get("DOI"),
            })

        return {"papers": papers, "count": len(papers)}
    except Exception as e:
        return {"papers": [], "count": 0, "error": str(e)}


# ── Public API ─────────────────────────────────────────────

def search(
    query: str,
    source: str = "both",
    max_results: int = 10,
    years: int | None = None,
) -> dict:
    """Search literature across PubMed and/or Semantic Scholar.

    Args:
        query: Search query string.
        source: 'pubmed', 'scholar', or 'both'.
        max_results: Maximum results per source.
        years: Limit to recent N years (PubMed only).

    Returns dict with papers from each source and total count.
    """
    results = {"agent": "literature", "query": query, "sources": {}}

    if source in ("pubmed", "both"):
        results["sources"]["pubmed"] = _search_pubmed(query, max_results, years)

    if source in ("scholar", "both"):
        results["sources"]["semantic_scholar"] = _search_scholar(query, max_results)

    # Total count
    total = 0
    for src_data in results["sources"].values():
        total += src_data.get("count", 0)
    results["total_papers"] = total

    return results
