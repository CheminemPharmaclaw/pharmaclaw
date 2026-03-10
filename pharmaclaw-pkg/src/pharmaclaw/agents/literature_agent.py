"""Literature Agent — AI-powered PubMed and Semantic Scholar search."""

from pharmaclaw.agents.base import BaseAgent
from pharmaclaw.core import literature as lit


class LiteratureAgent(BaseAgent):
    AGENT_NAME = "literature"

    SYSTEM_PROMPT = """You are PharmaClaw's Literature Agent 📚 — an expert in scientific literature search.

You search PubMed and Semantic Scholar to find relevant papers, reviews, and clinical studies.
Summarize findings clearly: key results, relevance to the user's question, and citation info.
When presenting papers, include title, authors, year, journal, and TLDR when available.
Highlight the most clinically relevant findings first.
"""

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search PubMed and/or Semantic Scholar for scientific papers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "source": {"type": "string", "enum": ["pubmed", "scholar", "both"], "default": "both"},
                        "max_results": {"type": "integer", "description": "Max results per source", "default": 10},
                        "years": {"type": "integer", "description": "Limit to recent N years (PubMed only)"}
                    },
                    "required": ["query"]
                }
            }
        },
    ]

    TOOL_FUNCTIONS = {
        "search": lit.search,
    }
